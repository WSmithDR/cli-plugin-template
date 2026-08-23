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
mkdir -p "$REPO_ROOT/features/nuevo-feature"
expect_block '{"tool_name":"Write","tool_input":{"file_path":"'$REPO_ROOT'/features/nuevo-feature/files/x.md","content":"hola"}}' "feature sin meta.yml → block"
printf '{"version":"1.0.0","name":"nuevo-feature"}' > "$REPO_ROOT/features/nuevo-feature/meta.yml"
expect_allow '{"tool_name":"Write","tool_input":{"file_path":"'$REPO_ROOT'/features/nuevo-feature/files/x.md","content":"hola"}}' "feature con meta.yml → allow"
rm -rf "$REPO_ROOT/features/nuevo-feature"
expect_allow '{"tool_name":"Write","tool_input":{"file_path":"'$REPO_ROOT'/README.md","content":"x"}}' "archivo fuera del catálogo → allow"

BLOCK_MD='---\ndescription: x\n---\n# T\n```bash\nlinea1\nlinea2\nlinea3\n```\n'
ALLOW_MD='---\ndescription: x\n---\n# T\n```bash\nlinea1\n```\n'
expect_block '{"tool_name":"Edit","tool_input":{"file_path":"'$REPO_ROOT'/skills/plugin-dev/SKILL.md","content":"'"$BLOCK_MD"'"}}' "SKILL.md con bloque >2 líneas → block"
expect_allow '{"tool_name":"Edit","tool_input":{"file_path":"'$REPO_ROOT'/skills/plugin-dev/SKILL.md","content":"'"$ALLOW_MD"'"}}' "SKILL.md con bloque ≤2 líneas → allow"

echo ""
echo "Resultado: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
