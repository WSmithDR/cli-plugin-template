#!/usr/bin/env python3
"""PreToolUse guard: hace cumplir el contrato del catálogo EN EL MOMENTO del edit,
no recién en el pre-commit. Lee {tool_name, tool_input{file_path, content?}} por stdin.
exit 2 + stderr = bloquear (convención Claude Code); exit 0 = allow silencioso.
Reglas v1:
  1. features/<name>/ sin meta.yml (y el archivo no ES meta.yml) → block.
  2. skills/*/SKILL.md con fenced block de script >2 líneas → block (regla de
     bin/audit-skill-structure.py, aplicada antes de escribir).
"""
import json
import re
import sys
from pathlib import Path

FENCE = re.compile(r"```(\w+)[^\n]*\n(.*?)```", re.DOTALL)
SCRIPT_LANGS = {"bash", "sh", "python", "python3", "node", "ts", "typescript", "js", "javascript"}
FEATURES_RE = re.compile(r"(^|/)features/([^/]+)/")


def violations(file_path: str, content: str) -> list[str]:
    out: list[str] = []
    m = FEATURES_RE.search(file_path.replace("\\", "/"))
    if m and Path(file_path).name != "meta.yml":
        feat_dir = next((p for p in Path(file_path).parents if p.name == m.group(2)), None)
        if feat_dir and not (feat_dir / "meta.yml").exists():
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
    found = violations(path, tool_input.get("content") or "")
    if not found:
        sys.exit(0)
    print("CATALOG-GUARD: " + "; ".join(found), file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
