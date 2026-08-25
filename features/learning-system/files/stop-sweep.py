#!/usr/bin/env python3
"""Stop hook — pieza 4 del loop: barre learnings modificados HOY y pide verificarlos.
Si los tocaste en esta sesión, conviene confirmar que siguen siendo correctos.

Integrar como función en tu Stop hook existente (ej. detect-pending-feedback.py);
devuelve "" cuando no hay nada que reportar. Dedupe no hace falta: el barrido es
idempotente por fecha y el costo de repetirlo al cierre es cero.
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

_CPT = "python3 <tu-cli>"  # ← adaptar


def _pending_learnings_message() -> str:
    from learning_store import learnings_dir, GLOBAL_SCOPE
    today = date.today().isoformat()
    found = []
    # .parent.parent: learnings_dir(GLOBAL_SCOPE) es <datadir>/_global/learnings;
    # hay que subir DOS niveles para alcanzar todos los scopes.
    for scope_dir in learnings_dir(GLOBAL_SCOPE).parent.parent.glob("*/learnings"):
        if not scope_dir.is_dir():
            continue
        for path in scope_dir.glob("learning_*.md"):
            body = path.read_text(encoding="utf-8", errors="replace")
            for line in body.splitlines():
                if line.startswith("last_updated:") and line.split(":", 1)[1].strip() == today:
                    found.append(f"{scope_dir.parent.name}/{path.stem[len('learning_'):]}")
                    break
    if not found:
        return ""
    items = ", ".join(found[:5])
    suffix = f" +{len(found)-5}" if len(found) > 5 else ""
    return (f"LEARNINGS MODIFIED TODAY ({len(found)}): [{items}{suffix}]. "
            f"Verify they are still correct or delete obsolete ones: "
            f"{_CPT} learning list --plugin <name> --full")


if __name__ == "__main__":
    try:
        json.load(sys.stdin)  # input del hook; no se usa más que validarlo
    except Exception:
        pass
    msg = _pending_learnings_message()
    if msg:
        print(json.dumps({"systemMessage": msg}))
