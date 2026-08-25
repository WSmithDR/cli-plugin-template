#!/usr/bin/env python3
"""PostToolUse (Edit|Write|MultiEdit): tras cada edición en un plugin registrado,
evalúa si el diff captura una convención nueva o contradice un aprendizaje vigente.
Si hay señal, propone guardarlo. Cooldown: una vez por archivo por sesión.

Contrato universal: JSON por stdin -> hookSpecificOutput por stdout; exit 0 siempre.
Solo Claude Code: OpenCode no tiene PostToolUse (verificado 2026-08-25).
"""
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

_CPT = "python3 <tu-cli>"  # ← adaptar


def _data_dir() -> Path:
    override = os.environ.get("MY_PLUGIN_DATA_DIR")  # ← adaptar
    return Path(override) if override else Path.home() / ".local/share/my-plugin"


def _plugin_of(file_path: str) -> str:
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


def _already_said(file_path: str, session_id: str) -> bool:
    marker = _data_dir() / "detect-learning.json"
    try:
        seen = json.loads(marker.read_text())
    except Exception:
        seen = {}
    key = f"{session_id or 'sin-sesion'}|{file_path}"
    if key in seen:
        return True
    seen = dict(list(seen.items())[-49:])
    seen[key] = True
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps(seen))
    except Exception:
        pass
    return False


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _extract_keywords(body: str) -> list:
    """Keywords del body (ignora frontmatter y headings)."""
    keywords, in_fm, past_fm = [], False, False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped == "---":
            if not past_fm:
                in_fm = not in_fm
                continue
            break
        if in_fm or stripped.startswith(("#",)):
            continue
        if stripped.startswith("- "):
            stripped = stripped[2:]
        keywords.extend(w[:8] for w in re.findall(r"\b\w{4,}\b", stripped)[:5])
    return list(dict.fromkeys(keywords))[:10]


def _learnings_for(plugin: str) -> list:
    try:
        from learning_store import learning_list, learning_load
        result = []
        for ref in learning_list(plugin=plugin):
            parts = ref.split("/", 1)
            if len(parts) == 2:
                scope, slug = parts
                result.append({"slug": slug, "body": learning_load(scope, slug)})
        return result
    except Exception:
        return []


def _diff_contradicts(diff_text: str, learnings: list):
    """Slug del primer aprendizaje que el diff parece contradecir, o None.
    ponytail: heurística 2+ keywords — se afina con uso real."""
    norm_diff = _normalize(diff_text)
    for entry in learnings:
        kw = _extract_keywords(entry["body"])
        if kw and sum(1 for k in kw if k in norm_diff) >= 2:
            return entry["slug"]
    return None


def _diff_shows_convention(diff_text: str) -> bool:
    """Heurística barata. ← REEMPLAZAR por los patrones de convención de TU plugin."""
    added = [l[1:] for l in diff_text.splitlines()
             if l.startswith("+") and not l.startswith("+++")]
    patterns = [r"sys\.path\.insert", r"json\.load\(sys\.stdin\)", r"try:\s*$",
                r"except \w+Error:", r"^# ?ponytail:"]
    hits = sum(1 for p in patterns if any(re.search(p, l) for l in added))
    return len(added) >= 2 and hits >= 2


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    path = (data.get("tool_input") or {}).get("file_path") or ""
    diff = (data.get("tool_output") or {}).get("diff", "") or ""
    if not path or not diff:
        return
    plugin = _plugin_of(path)
    if not plugin or _already_said(path, str(data.get("session_id") or "")):
        return
    learnings = _learnings_for(plugin)
    if not learnings:
        return
    slug = _diff_contradicts(diff, learnings)
    action = "update" if slug else ("propose" if _diff_shows_convention(diff) else None)
    if not action:
        return
    if action == "update":
        msg = (f"El diff parece contradecir el aprendizaje `{slug}` de {plugin}. "
               f"Corregí el código Y el aprendizaje juntos:\n"
               f"    {_CPT} learning save {slug} \"<nueva descripcion>\" --plugin {plugin}")
    else:
        msg = (f"El diff en {plugin} parece capturar una convención nueva. "
               f"Si es intencional, guardalo:\n"
               f"    {_CPT} learning save <slug> \"<descripcion>\" "
               f"--plugin {plugin} --category convencion")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": msg,
    }}))


if __name__ == "__main__":
    main()
