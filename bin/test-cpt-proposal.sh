#!/bin/bash
# Tests del gate de propuestas y feedback apply (P2). Data dir aislado.
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
echo "=== cpt proposal + feedback apply ==="

# proposal save → archivo en <plugin>/proposals/<slug>.md con status pending
python3 "$CPT" proposal save ankify gap-x - >/dev/null <<'EOF'
---
status: pending
patch_target: "skills/x/SKILL.md"
---
ANTES: foo
DESPUÉS: bar
EOF
f="$DATA/ankify/proposals/gap-x.md"
[ -f "$f" ] && _pass "proposal save → <plugin>/proposals/<slug>.md" || _fail "proposal save: no existe $f"

# list --status pending lo incluye
out=$(python3 "$CPT" proposal list --status pending)
echo "$out" | grep -qx "ankify/gap-x" && _pass "list --status pending incluye la propuesta" || _fail "pending: '$out'"

# show imprime el contenido
python3 "$CPT" proposal show ankify gap-x | grep -q "ANTES: foo" && _pass "proposal show imprime contenido" || _fail "show"

# set-status approved → sale de pending, entra en approved
python3 "$CPT" proposal set-status ankify gap-x approved >/dev/null
p=$(python3 "$CPT" proposal list --status pending)
a=$(python3 "$CPT" proposal list --status approved)
{ [ -z "$p" ] && echo "$a" | grep -qx "ankify/gap-x"; } \
    && _pass "set-status approved: pending→approved" || _fail "set-status: pending='$p' approved='$a'"

# set-status discarded queda como registro
python3 "$CPT" proposal save ankify gap-y - >/dev/null <<'EOF'
---
status: pending
---
y
EOF
python3 "$CPT" proposal set-status ankify gap-y discarded >/dev/null
d=$(python3 "$CPT" proposal list --status discarded)
echo "$d" | grep -qx "ankify/gap-y" && _pass "set-status discarded queda como registro" || _fail "discarded: '$d'"

# feedback apply: applied:false → true + applied_at, sale de --pending
python3 "$CPT" feedback save ankify gap-x - >/dev/null <<'EOF'
---
applied: false
patch_target: "skills/x/SKILL.md"
---
gap
EOF
python3 "$CPT" feedback apply ankify gap-x >/dev/null
body=$(python3 "$CPT" feedback show ankify gap-x)
pend=$(python3 "$CPT" feedback list --pending)
{ echo "$body" | grep -qx "applied: true" && echo "$body" | grep -q "^applied_at:" && [ -z "$pend" ]; } \
    && _pass "feedback apply: applied true + applied_at, fuera de --pending" \
    || _fail "apply: body=$(echo "$body" | grep applied) pend='$pend'"

# apply de un feedback inexistente → error (rc≠0)
rc=0; python3 "$CPT" feedback apply ankify no-existe >/dev/null 2>&1 || rc=$?
[ "$rc" -ne 0 ] && _pass "apply inexistente → error" || _fail "apply inexistente debería fallar"

echo ""
echo "Resultado: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ] && exit 0 || exit 1
