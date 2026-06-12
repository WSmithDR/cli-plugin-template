#!/usr/bin/env python3
"""Stop hook: detecta feedbacks de plugins sin aplicar (cross-plugin) y sugiere
procesarlos con plugin-hotpatch (P2). Lee solo el store de cli-plugin-template.

Emite JSON con `systemMessage` (misma convención que el Stop hook de ankify) si hay
pendientes; nada si no.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))


def main() -> int:
    transcript_path = sys.argv[1] if len(sys.argv) > 1 else ""
    # transcript_path se pasa por consistencia con otros hooks; acá no se usa todavía.
    _ = transcript_path

    try:
        from gateway import feedback_list
        pending = feedback_list(pending_only=True)
    except Exception:
        return 0

    if not pending:
        return 0

    count = len(pending)
    items = "; ".join(pending[:3])
    suffix = "..." if count > 3 else ""
    msg = (f"PENDING PLUGIN FEEDBACK: {count} feedback(s) sin aplicar: "
           f"[{items}{suffix}]. Call Skill(\"cli-plugin-template:plugin-hotpatch\") "
           f"using the Skill tool to review and patch.")

    print(json.dumps({"systemMessage": msg}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
