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
echo "=== test-failure-nudge.py (PostToolUseFailure) ==="
run_nudge() { printf '%s' "$1" | python3 "$NUDGE" 2>/dev/null; }

out=$(run_nudge '{"tool_name":"Bash","tool_input":{"command":"bash bin/test-catalog-hooks.sh"},"error":"Exit code 1\nFAILED (tests=3, failures=2)\nAssertionError: esperaba allow"}')
if echo "$out" | grep -q "cpt feedback save"; then echo "  PASS: suite fallida (Exit code 1) → sugiere feedback"; pass=$((pass+1)); else echo "  FAIL: suite fallida Exit code 1 sin sugerencia"; fail=$((fail+1)); fi

out=$(run_nudge '{"tool_name":"Bash","tool_input":{"command":"bash bin/test-catalog-hooks.sh"},"error":"Exit code 0"}')
if [ -z "$out" ]; then echo "  PASS: error Exit code 0 → silencio"; pass=$((pass+1)); else echo "  FAIL: Exit code 0 no debe hablar"; fail=$((fail+1)); fi

out=$(run_nudge '{"tool_name":"Bash","tool_input":{"command":"ls -la"},"error":"Exit code 1"}')
if [ -z "$out" ]; then echo "  PASS: comando ajeno → silencio"; pass=$((pass+1)); else echo "  FAIL: ls no es suite"; fail=$((fail+1)); fi

out=$(run_nudge '{"tool_name":"Bash","tool_input":{"command":"bash bin/test-catalog-hooks.sh"},"error":"python3: can'\''t open file: no such file"}')
if [ -z "$out" ]; then echo "  PASS: error sin línea de exit code → silencio"; pass=$((pass+1)); else echo "  FAIL: error sin Exit code N no debe hablar"; fail=$((fail+1)); fi

INTENT="$REPO_ROOT/bin/hooks/intent-nudge.py"
echo ""
echo "=== intent-nudge.py (UserPromptSubmit) ==="
mkdir -p /tmp/proj-ankify
printf '[{"name":"ankify","local_path":"/tmp/proj-ankify","skill_namespaces":["ankify"]}]' > "$DATA/registry.json"

out=$(cd /tmp/proj-ankify && printf '%s' '{"prompt":"integrá versionado al plugin"}' | python3 "$INTENT")
if echo "$out" | grep -q "plugin-dev"; then echo "  PASS: intención en plugin registrado → sugiere router"; pass=$((pass+1)); else echo "  FAIL: intención sin sugerencia"; fail=$((fail+1)); fi

out=$(cd "$REPO_ROOT" && printf '%s' '{"prompt":"integrá versionado al plugin"}' | python3 "$INTENT")
if [ -z "$out" ]; then echo "  PASS: repo propio (sentinel) → silencio"; pass=$((pass+1)); else echo "  FAIL: en el catálogo sobra el nudge"; fail=$((fail+1)); fi

out=$(cd /tmp/proj-ankify && printf '%s' '{"prompt":"qué hora es"}' | python3 "$INTENT")
if [ -z "$out" ]; then echo "  PASS: prompt sin intención → silencio"; pass=$((pass+1)); else echo "  FAIL: falso positivo"; fail=$((fail+1)); fi

out=$(cd /tmp && printf '%s' '{"prompt":"integrá versionado al plugin"}' | python3 "$INTENT")
if [ -z "$out" ]; then echo "  PASS: intención en dir no registrado → silencio"; pass=$((pass+1)); else echo "  FAIL: nudge fuera de un plugin registrado"; fail=$((fail+1)); fi

WIP="$REPO_ROOT/bin/hooks/wip-snapshot.py"
echo ""
echo "=== wip-snapshot.py (PreCompact) ==="
out=$(cd "$REPO_ROOT" && printf '{}' | python3 "$WIP")
snap=$(ls -t "$DATA"/wip/*.txt 2>/dev/null | head -1)
if [ -n "$snap" ] && grep -A1 "^## Branch" "$snap" | sed -n 2p | grep -q "main"; then echo "  PASS: snapshot creado con branch"; pass=$((pass+1)); else echo "  FAIL: sin snapshot utilizable"; fail=$((fail+1)); fi

out=$(printf 'basura no-JSON' | python3 "$WIP" 2>/dev/null); rc=$?
if [ "$rc" -eq 0 ]; then echo "  PASS: payload basura → exit 0 igual"; pass=$((pass+1)); else echo "  FAIL: hook debe salir siempre 0"; fail=$((fail+1)); fi

echo ""
echo "Resultado: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
