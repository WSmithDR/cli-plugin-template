#!/usr/bin/env python3
"""PreToolUse (Edit|Write|MultiEdit): si el archivo a tocar vive en un plugin
registrado, recuerda los aprendizajes vigentes ANTES de editar. El momento importa:
al abrir sesión el aprendizaje no aplica a nada; al editar sí hay una decisión.

Habla UNA vez por sesión y por plugin. Nunca bloquea: exit 0 siempre.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))


def _data_dir() -> Path:
    override = os.environ.get("MY_PLUGIN_DATA_DIR")  # ← adaptar
    return Path(override) if override else Path.home() / ".local/share/my-plugin"


def _plugin_of(file_path: str) -> str:
    """Plugin registrado que contiene el archivo. Gana el local_path más largo."""
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


def _already_said(plugin: str, session_id: str) -> bool:
    marker = _data_dir() / "learning-nudge.json"
    try:
        seen = json.loads(marker.read_text())
    except Exception:
        seen = {}
    key = f"{session_id or 'sin-sesion'}|{plugin}"
    if key in seen:
        return True
    seen = dict(list(seen.items())[-49:])  # ponytail: cap fijo, sin ciclo de vida de sesión
    seen[key] = True
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps(seen))
    except Exception:
        pass
    return False


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
    try:
        from learning_store import learning_list
        refs = learning_list(plugin=plugin)
    except Exception:
        refs = []
    if not refs or _already_said(plugin, str(data.get("session_id") or "")):
        return
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": (
            f"Estás editando {plugin}. Hay {len(refs)} aprendizaje(s) vigente(s) "
            f"({', '.join(refs[:5])}{', …' if len(refs) > 5 else ''}). Leelos antes de "
            f"decidir el enfoque:\n    python3 <tu-cli> learning list --plugin {plugin} --full\n"
            "Si lo que descubrís los contradice, corregí el aprendizaje además del código."),
    }}))


if __name__ == "__main__":
    main()
