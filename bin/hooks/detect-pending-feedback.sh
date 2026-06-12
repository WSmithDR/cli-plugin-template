#!/usr/bin/env bash
# Stop hook: delega la detección de feedbacks pendientes a detect-pending-feedback.py.
# Lee solo el store de cli-plugin-template; coexiste con hooks Stop de otros plugins.

set -uo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
INPUT=$(cat)

TRANSCRIPT_PATH=$(echo "$INPUT" | python3 -c "
import json,sys
try:
    print(json.load(sys.stdin).get('transcript_path',''))
except Exception:
    print('')
" 2>/dev/null)

python3 "$PLUGIN_ROOT/bin/hooks/detect-pending-feedback.py" "$TRANSCRIPT_PATH"
