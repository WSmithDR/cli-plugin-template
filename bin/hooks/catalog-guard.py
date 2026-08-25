#!/usr/bin/env python3
"""PreToolUse guard: hace cumplir el contrato del catálogo EN EL MOMENTO del edit,
no recién en el pre-commit. Lee {tool_name, tool_input{file_path, content?|new_string?|edits[]?}} por stdin.
exit 2 + stderr = bloquear (convención Claude Code); exit 0 = allow silencioso.
Reglas v1:
  1. features/<name>/ sin meta.yml (y el archivo no ES meta.yml) → block.
     Solo dentro del repo del catálogo (sentinel .catalog-root en algún ancestro):
     `features/` es un nombre de carpeta común (p. ej. src/features/ de una app
     Next.js) y bloquear ahí sería un falso positivo en repos ajenos.
  2. skills/*/SKILL.md con fenced block de script >2 líneas → block (regla de
     bin/audit-skill-structure.py, aplicada antes de escribir). Aplica a cualquier
     plugin, no solo al catálogo.
"""
import json
import re
import sys
from pathlib import Path

FENCE = re.compile(r"```(\w+)[^\n]*\n(.*?)```", re.DOTALL)
SCRIPT_LANGS = {"bash", "sh", "python", "python3", "node", "ts", "typescript", "js", "javascript"}
FEATURES_RE = re.compile(r"(^|/)features/([^/]+)/")
SENTINEL = ".catalog-root"


def en_el_catalogo(feat_dir: Path) -> bool:
    """True si el feature vive dentro del repo del catálogo, que se identifica con
    el sentinel .catalog-root en su raíz (mismo criterio que session-start.sh,
    intent-nudge.py y .opencode/lib/paths.ts). Sin sentinel en ningún ancestro, el
    `features/<x>/` es de otro proyecto y la regla 1 no corresponde."""
    for anc in (feat_dir, *feat_dir.parents):
        if (anc / SENTINEL).exists():
            return True
    return False


def violations(file_path: str, content: str) -> list[str]:
    out: list[str] = []
    m = FEATURES_RE.search(file_path.replace("\\", "/"))
    if m and Path(file_path).name != "meta.yml":
        feat_dir = next((p for p in Path(file_path).parents if p.name == m.group(2)), None)
        if feat_dir and en_el_catalogo(feat_dir) and not (feat_dir / "meta.yml").exists():
            out.append(f"features/{m.group(2)}/ no tiene meta.yml — crealo junto al resto del feature")
    base = Path(file_path).name
    if base == "SKILL.md" and "/skills/" in file_path.replace("\\", "/"):
        for lang, body in FENCE.findall(content or ""):
            if lang.lower() in SCRIPT_LANGS and len([l for l in body.split("\n") if l.strip()]) > 2:
                out.append(
                    f"SKILL.md embebe un bloque ```{lang} de más de 2 líneas — va a scripts/ "
                    "(regla de modularización; audit-skill-structure.py lo bloquearía igual)"
                )
                break
    return out


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    tool_input = data.get("tool_input") or {}
    path = tool_input.get("file_path") or ""
    if not path:
        sys.exit(0)
    payloads = [tool_input.get("content") or tool_input.get("new_string") or ""]
    payloads += [e.get("new_string") or "" for e in tool_input.get("edits") or []]
    found = [v for p in payloads for v in violations(path, p)]
    if not found:
        sys.exit(0)
    print("CATALOG-GUARD: " + "; ".join(found), file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
