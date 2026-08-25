#!/usr/bin/env python3
"""PreToolUse (Edit|Write|MultiEdit): si el archivo que se va a tocar vive en un plugin
registrado, recuerda consultar los aprendizajes vigentes ANTES de editar.

El momento importa: al abrir sesión el aprendizaje todavía no aplica a nada y se
olvida; al editar es cuando hay una decisión concreta que tomar. Por eso el nudge es
PreToolUse y no SessionStart.

Habla UNA vez por sesión y por plugin — un recordatorio en cada Edit sería ruido, y el
ruido se ignora. Nunca bloquea: exit 0 siempre, aunque el store esté roto.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))


def _data_dir() -> Path:
    override = os.environ.get("CLI_PLUGIN_TEMPLATE_DATA_DIR")
    return Path(override) if override else Path.home() / ".local/share/cli-plugin-template"


def _plugin_of(file_path: str) -> str:
    """Nombre del plugin registrado que contiene el archivo, o "" si ninguno.
    Gana el local_path más largo: un plugin anidado en otro no queda tapado."""
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


def _learnings(plugin: str) -> list:
    try:
        from gateway import learning_list
        return learning_list(plugin=plugin)
    except Exception:
        return []


def _already_said(plugin: str, session_id: str) -> bool:
    """Marca por (sesión, plugin). Sin session_id el hook habla una sola vez y listo:
    mejor un nudge de menos que uno por cada Edit."""
    marker = _data_dir() / "learning-nudge.json"
    try:
        seen = json.loads(marker.read_text())
    except Exception:
        seen = {}
    key = f"{session_id or 'sin-sesion'}|{plugin}"
    if key in seen:
        return True
    # ponytail: se queda con las últimas 50 marcas — no hay ciclo de vida de sesión
    # que las limpie, y el archivo no debería crecer para siempre.
    seen = dict(list(seen.items())[-49:])
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
    # El propio catálogo NO se excluye: también es un plugin que se desarrolla, y sus
    # convenciones son justamente las que el taller quiere aplicar (a diferencia del
    # nudge de auditoría, que sí se calla acá con .catalog-root).
    if not path:
        return
    plugin = _plugin_of(path)
    if not plugin:
        return
    refs = _learnings(plugin)
    if not refs:
        return
    if _already_said(plugin, str(data.get("session_id") or "")):
        return
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": (
            f"Estás editando {plugin}. Hay {len(refs)} aprendizaje(s) vigente(s) sobre "
            f"cómo se desarrollan estos plugins ({', '.join(refs[:5])}"
            f"{', …' if len(refs) > 5 else ''}). Leelos antes de decidir el enfoque:\n"
            f"    python3 \"$CLAUDE_PLUGIN_ROOT/bin/cpt\" learning list --plugin {plugin} --full\n"
            "Si lo que descubrís los contradice, corregí el aprendizaje además del código "
            "(cpt learning save <slug> - lo pisa por tema)."),
    }}))


if __name__ == "__main__":
    main()
