#!/usr/bin/env bash
set -euo pipefail
python3 - "$CLAUDE_PLUGIN_ROOT" <<'PY'
import json, sys, pathlib
root = pathlib.Path(sys.argv[1] or ".")
hj = root / "hooks" / "hooks.json"
try:
    hooks = json.loads(hj.read_text()).get("hooks", {})
    ss = hooks.get("SessionStart")
    print("✓ SessionStart registrado en hooks.json" if ss
          else "✗ SessionStart no está en hooks.json")
except Exception as e:
    print(f"✗ no pude leer hooks.json ({e})")
PY
[ -f "${CLAUDE_PLUGIN_ROOT}/bin/hooks/session-start.sh" ] \
  && echo "✓ session-start.sh presente" || echo "✗ falta bin/hooks/session-start.sh"
