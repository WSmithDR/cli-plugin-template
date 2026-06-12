#!/bin/bash
# Tests de la captura de feedback de bin/cpt. Data dir aislado.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CPT="$SCRIPT_DIR/cpt"
PASS=0; FAIL=0
_pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
_fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

DATA=$(mktemp -d)
export CLI_PLUGIN_TEMPLATE_DATA_DIR="$DATA"
trap 'rm -rf "$DATA"' EXIT

echo ""
echo "=== cpt feedback ==="

# save via heredoc → archivo en <plugin>/feedbacks/feedback_<slug>.md
python3 "$CPT" feedback save ankify "namespace-issue" - >/dev/null <<'EOF'
---
name: feedback-namespace-issue
plugin: ankify
applied: false
---
algo falló
EOF
f="$DATA/ankify/feedbacks/feedback_namespace-issue.md"
[ -f "$f" ] && _pass "save heredoc → archivo en <plugin>/feedbacks/" || _fail "save: no existe $f"

# list --pending lo incluye (applied:false)
out=$(python3 "$CPT" feedback list --pending)
echo "$out" | grep -qx "ankify/namespace-issue" && _pass "list --pending incluye applied:false" \
    || _fail "pending: '$out'"

# un feedback applied:true NO aparece en --pending pero sí en list normal
python3 "$CPT" feedback save ankify "ya-aplicado" - >/dev/null <<'EOF'
---
applied: true
---
listo
EOF
pend=$(python3 "$CPT" feedback list --pending --plugin ankify)
allf=$(python3 "$CPT" feedback list --plugin ankify)
echo "$pend" | grep -q "ya-aplicado" && _fail "applied:true no debería estar en --pending" \
    || { echo "$allf" | grep -q "ya-aplicado" && _pass "applied:true: fuera de --pending, dentro de list" \
         || _fail "applied:true ausente de list normal: '$allf'"; }

# cross-plugin: otro plugin → prefijo <plugin>/ correcto
python3 "$CPT" feedback save cli-plugin-template "self-friction" - >/dev/null <<'EOF'
---
applied: false
---
dogfood
EOF
out=$(python3 "$CPT" feedback list --pending)
echo "$out" | grep -qx "cli-plugin-template/self-friction" \
    && _pass "cross-plugin → '<plugin>/<slug>'" || _fail "cross-plugin: '$out'"

echo ""
echo "Resultado: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ] && exit 0 || exit 1
