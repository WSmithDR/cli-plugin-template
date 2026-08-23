#!/bin/bash
# Tests de los hooks nuevos del meta-plugin. Data dir aislado.
set -uo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA=$(mktemp -d)
trap 'rm -rf "$DATA"' EXIT
export CLI_PLUGIN_TEMPLATE_DATA_DIR="$DATA"
pass=0 fail=0

run_guard() { printf '%s' "$1" | python3 "$REPO_ROOT/bin/hooks/catalog-guard.py" >/dev/null 2>&1; }
expect_block() {
  if ! run_guard "$1"; then echo "  PASS: $2"; pass=$((pass+1)); else echo "  FAIL: $2 (esperaba bloqueo)"; fail=$((fail+1)); fi
}
expect_allow() {
  if run_guard "$1"; then echo "  PASS: $2"; pass=$((pass+1)); else echo "  FAIL: $2 (esperaba allow)"; fail=$((fail+1)); fi
}

echo ""
echo "=== catalog-guard.py (PreToolUse) ==="
expect_block '{"tool_name":"Write","tool_input":{"file_path":"'$DATA'/features/nuevo-feature/files/x.md","content":"hola"}}' "feature sin meta.yml → block"
mkdir -p "$DATA/features/nuevo-feature"
printf '{"version":"1.0.0","name":"nuevo-feature"}' > "$DATA/features/nuevo-feature/meta.yml"
expect_allow '{"tool_name":"Write","tool_input":{"file_path":"'$DATA'/features/nuevo-feature/files/x.md","content":"hola"}}' "feature con meta.yml → allow"
expect_allow '{"tool_name":"Write","tool_input":{"file_path":"'$REPO_ROOT'/README.md","content":"x"}}' "archivo fuera del catálogo → allow"

BLOCK_MD='---\ndescription: x\n---\n# T\n```bash\nlinea1\nlinea2\nlinea3\n```\n'
ALLOW_MD='---\ndescription: x\n---\n# T\n```bash\nlinea1\n```\n'
SKILL_PATH="$REPO_ROOT/skills/plugin-dev/SKILL.md"
expect_block '{"tool_name":"Edit","tool_input":{"file_path":"'$SKILL_PATH'","content":"'"$BLOCK_MD"'"}}' "SKILL.md con bloque >2 líneas en content → block"
expect_allow '{"tool_name":"Edit","tool_input":{"file_path":"'$SKILL_PATH'","content":"'"$ALLOW_MD"'"}}' "SKILL.md con bloque ≤2 líneas → allow"
expect_block '{"tool_name":"Edit","tool_input":{"file_path":"'$SKILL_PATH'","new_string":"```bash\nl1\nl2\nl3\n```"}}' "SKILL.md con bloque >2 líneas en new_string → block"

NUDGE="$REPO_ROOT/bin/hooks/test-failure-nudge.py"
echo ""
echo "=== test-failure-nudge.py (PostToolUse) ==="
run_nudge() { printf '%s' "$1" | python3 "$NUDGE" 2>/dev/null; }

out=$(run_nudge '{"tool_input":{"command":"bash bin/test-catalog-hooks.sh"},"tool_response":{"success":false}}')
if echo "$out" | grep -q "cpt feedback save"; then echo "  PASS: suite fallida → sugiere feedback"; pass=$((pass+1)); else echo "  FAIL: suite fallida sin sugerencia"; fail=$((fail+1)); fi

out=$(run_nudge '{"tool_input":{"command":"bash bin/test-catalog-hooks.sh"},"tool_response":{"success":true}}')
if [ -z "$out" ]; then echo "  PASS: suite ok → silencio"; pass=$((pass+1)); else echo "  FAIL: suite ok no debe hablar"; fail=$((fail+1)); fi

out=$(run_nudge '{"tool_input":{"command":"ls -la"},"tool_response":{"success":false}}')
if [ -z "$out" ]; then echo "  PASS: comando ajeno → silencio"; pass=$((pass+1)); else echo "  FAIL: ls no es suite"; fail=$((fail+1)); fi

echo ""
echo "Resultado: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
