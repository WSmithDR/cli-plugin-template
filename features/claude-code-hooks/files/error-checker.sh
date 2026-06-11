#!/bin/bash
# PostToolUse(Bash): cuando un comando falla, evalúa si merece una acción del plugin.

set -euo pipefail

TOOL_INFO=$(cat)

IS_ERROR=$(echo "$TOOL_INFO" | python3 -c '
import json, sys
d = json.load(sys.stdin)
tr = d.get("tool_response", {})
is_err = False
if isinstance(tr, dict):
    is_err = tr.get("is_error", False) or tr.get("exit_code", 0) not in (0, None)
print("true" if is_err else "false")
' 2>/dev/null || echo "false")

[ "$IS_ERROR" != "true" ] && exit 0

# Solo actuar en proyectos del plugin
[ ! -d ".midata" ] && exit 0

CMD=$(echo "$TOOL_INFO" | python3 -c '
import json, sys
print(json.load(sys.stdin).get("tool_input", {}).get("command", "")[:250])
' 2>/dev/null || echo "")

# Ignorar comandos triviales que devuelven non-zero por diseño
echo "$CMD" | grep -qE "^\s*(grep|ls|find|test |\[ )" && exit 0
echo "$CMD" | grep -qE "2>/dev/null|>/dev/null|\|\| true" && exit 0

echo "ERROR-CHECKER: el comando falló.
  Comando: $CMD

Evaluá si vale la pena registrar esto (acción del plugin) o ignorarlo." >&2
exit 2
