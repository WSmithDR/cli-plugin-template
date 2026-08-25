#!/usr/bin/env python3
"""PostToolUse (Edit|Write|MultiEdit): despues de cada edicion en un plugin registrado,
evalua si el diff captura una convencion nueva o contradice un aprendizaje vigente.
Si hay senal, propone guardarlo con ``cpt learning save``. Una vez por archivo por sesion.

Contrato universal: JSON por stdin -> hookSpecificOutput por stdout; exit 0 siempre.
Solo Claude Code: OpenCode no tiene PostToolUse (verificado 2026-08-25).
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

_CPT = str(Path(__file__).resolve().parents[1] / "cpt")


def _data_dir() -> Path:
    override = os.environ.get("CLI_PLUGIN_TEMPLATE_DATA_DIR")
    return Path(override) if override else Path.home() / ".local/share/cli-plugin-template"


def _plugin_of(file_path: str) -> str:
    """Nombre del plugin registrado que contiene el archivo, o '' si ninguno."""
    try:
        registry = json.loads((_data_dir() / "registry.json").read_text())
    except Exception:
        return ""
    target = os.path.abspath(file_path)
    best = ("", 0)
    for entry in registry:
        lp = (entry.get("local_path") or "").rstrip("/")
        if lp and (target == lp or target.startswith(lp + "/")) and len(lp) > best[1]:
            best = (entry.get("name") or "", len(lp))
    return best[0]


def _learnings_for(plugin: str) -> list:
    try:
        from gateway import learning_list, learning_load
        slugs = learning_list(plugin=plugin)
        result = []
        for ref in slugs:
            parts = ref.split("/", 1)
            if len(parts) == 2:
                scope, slug = parts
                body = learning_load(scope, slug)
                result.append({"ref": ref, "slug": slug, "body": body})
        return result
    except Exception:
        return []


def _already_said(file_path: str, session_id: str) -> bool:
    """Cooldown: una vez por archivo por sesion."""
    marker = _data_dir() / "detect-learning.json"
    try:
        seen = json.loads(marker.read_text())
    except Exception:
        seen = {}
    key = f"{session_id or 'sin-sesion'}|{file_path}"
    if key in seen:
        return True
    # ponytail: se queda con las ultimas 50 marcas
    seen = dict(list(seen.items())[-49:])
    seen[key] = True
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps(seen))
    except Exception:
        pass
    return False


def _normalize(text: str) -> str:
    import unicodedata
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _extract_keywords(body: str) -> list:
    """Extrae keywords del body del aprendizaje (ignora frontmatter YAML)."""
    keywords = []
    in_frontmatter = False
    past_frontmatter = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped == "---":
            if not past_frontmatter:
                in_frontmatter = not in_frontmatter
                continue
            else:
                break
        if in_frontmatter:
            continue
        if stripped.startswith(("## ", "# ")):
            continue
        if stripped.startswith("- "):
            stripped = stripped[2:]
        words = re.findall(r"\b\w{4,}\b", stripped)
        keywords.extend(w[:8] for w in words[:5])
    return list(dict.fromkeys(keywords))[:10]


def _diff_contradicts(diff_text: str, learnings: list):
    """Devuelve el slug del primer aprendizaje que el diff parece contradecir, o None."""
    norm_diff = _normalize(diff_text)
    for entry in learnings:
        kw = _extract_keywords(entry["body"])
        if not kw:
            continue
        hits = sum(1 for k in kw if k in norm_diff)
        if hits >= 2:
            return entry["slug"]
    return None


def _diff_shows_convention(diff_text: str) -> bool:
    """Heuristica barata: el diff agrega un patron que parece convencion."""
    added = [l[1:] for l in diff_text.splitlines()
             if l.startswith("+") and not l.startswith("+++")]
    if len(added) < 2:
        return False
    patterns = [
        r"sys\.path\.insert",
        r"json\.load\(sys\.stdin\)",
        r"def _\w+\(.*\) ->",
        r"try:\s*$",
        r"except \w+Error:",
        r"^# ?ponytail:",
    ]
    hits = sum(1 for p in patterns if any(re.search(p, l) for l in added))
    return hits >= 2


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    path = (data.get("tool_input") or {}).get("file_path") or ""
    if not path:
        return
    plugin = _plugin_of(path)
    if not plugin:
        return
    session_id = str(data.get("session_id") or "")
    if _already_said(path, session_id):
        return
    diff = (data.get("tool_output") or {}).get("diff", "") or ""
    if not diff:
        return
    learnings = _learnings_for(plugin)
    if not learnings:
        return
    slug = _diff_contradicts(diff, learnings)
    action = "update" if slug else ("propose" if _diff_shows_convention(diff) else None)
    if not action:
        return
    if action == "update":
        msg = (f"El diff parece contradecir el aprendizaje ``{slug}`` de {plugin}. "
               f"Corregi el codigo Y el aprendizaje juntos:\n"
               f"    python3 \"{_CPT}\" learning save {slug} \"<nueva descripcion>\" --plugin {plugin}")
    else:
        msg = (f"El diff en {plugin} parece capturar una convencion nueva. "
               f"Si es intencional, guardalo:\n"
               f"    python3 \"{_CPT}\" learning save <slug> \"<descripcion>\" "
               f"--plugin {plugin} --category convencion")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": msg,
    }}))


if __name__ == "__main__":
    main()
