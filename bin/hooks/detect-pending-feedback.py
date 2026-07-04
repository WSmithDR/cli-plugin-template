#!/usr/bin/env python3
"""Stop hook (entrypoint directo, sin wrapper .sh): (1) detecta feedbacks de plugins sin
aplicar y sugiere plugin-hotpatch; (2) escanea el tramo NUEVO del transcript buscando
fricción con plugins registrados y sugiere delegar la cosecha al subagente
feedback-harvester, fuera del hilo principal.

Lee el input del hook (JSON con transcript_path) por stdin. Emite JSON con
`systemMessage` (misma convención que el Stop hook de ankify) si hay algo que
reportar; nada si no.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

# ponytail: heurística por keywords — el análisis real lo hace el subagente feedback-harvester.
FRICTION_KEYWORDS = (
    "no me gusta", "prefiero", "está mal", "esta mal", "estuvo mal",
    "no funciona", "no sirve", "incompleto", "no lo cubre", "no lo contempla",
)


def _new_chunk(transcript_path: str) -> str:
    """Devuelve solo lo agregado al transcript desde el último Stop (idempotencia por offset)."""
    from gateway import harvest_offset_get, harvest_offset_set
    p = Path(transcript_path)
    if not p.is_file():
        return ""
    text = p.read_text(encoding="utf-8", errors="replace")
    start = harvest_offset_get(str(p))
    chunk = text[start:] if start <= len(text) else text
    try:
        harvest_offset_set(str(p), len(text))
    except Exception:
        pass
    return chunk


def _user_text(chunk: str) -> str:
    out = []
    for line in chunk.splitlines():
        try:
            entry = json.loads(line)
        except Exception:
            continue
        if entry.get("type") != "user":
            continue
        content = (entry.get("message") or {}).get("content", "")
        if isinstance(content, list):
            content = " ".join(b.get("text", "") for b in content if isinstance(b, dict))
        out.append(str(content))
    return " ".join(out).lower()


def _friction_message(transcript_path: str) -> str:
    if not transcript_path:
        return ""
    try:
        from gateway import registry_list
        plugins = [r.get("name", "") for r in registry_list() if r.get("name")]
    except Exception:
        return ""
    if not plugins:
        return ""
    chunk = _new_chunk(transcript_path)
    if not chunk:
        return ""
    lower = chunk.lower()
    mentioned = [n for n in plugins if n.lower() in lower]
    if not mentioned or not any(k in _user_text(chunk) for k in FRICTION_KEYWORDS):
        return ""
    return (f"POSSIBLE PLUGIN FRICTION this session (plugins: {', '.join(mentioned)}). "
            f"Dispatch the harvest OUTSIDE the main thread: call the Agent tool with "
            f"subagent_type \"cli-plugin-template:feedback-harvester\" and "
            f"run_in_background, passing the transcript path {transcript_path}. It saves "
            f"feedbacks via cpt and replies with a one-line summary.")


def main() -> int:
    try:
        transcript_path = str(json.load(sys.stdin).get("transcript_path", ""))
    except Exception:
        transcript_path = ""
    msgs = []

    try:
        from gateway import feedback_list
        pending = feedback_list(pending_only=True)
    except Exception:
        pending = []

    if pending:
        count = len(pending)
        items = "; ".join(pending[:3])
        suffix = "..." if count > 3 else ""
        msgs.append(f"PENDING PLUGIN FEEDBACK: {count} feedback(s) sin aplicar: "
                    f"[{items}{suffix}]. Call Skill(\"cli-plugin-template:plugin-hotpatch\") "
                    f"using the Skill tool to review and patch.")

    friction = _friction_message(transcript_path)
    if friction:
        msgs.append(friction)

    if msgs:
        print(json.dumps({"systemMessage": " | ".join(msgs)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
