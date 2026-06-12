#!/bin/bash
# Tests del registry (allowlist) de bin/cpt. Data dir aislado por test.
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
echo "=== cpt registry ==="

# register → aparece en list
python3 "$CPT" registry register ankify /repos/ankify --remote git@x/ankify >/dev/null
out=$(python3 "$CPT" registry list)
echo "$out" | grep -q '"name": "ankify"' && echo "$out" | grep -q '/repos/ankify' \
    && _pass "register → list" || _fail "register → list: $out"

# idempotencia: re-register mismo name con path nuevo no duplica y actualiza
python3 "$CPT" registry register ankify /repos/ankify-moved >/dev/null
count=$(python3 "$CPT" registry list | grep -c '"name": "ankify"')
moved=$(python3 "$CPT" registry list | grep -c '/repos/ankify-moved')
[ "$count" -eq 1 ] && [ "$moved" -eq 1 ] && _pass "re-register actualiza, no duplica" \
    || _fail "idempotencia: count=$count moved=$moved"

# resolve: namespace con sufijo → name
got=$(python3 "$CPT" registry resolve "ankify:anki-capture" || true)
[ "$got" = "ankify" ] && _pass "resolve 'ankify:anki-capture' → ankify" || _fail "resolve: '$got'"

# resolve: plugin fuera del allowlist → vacío + rc=1
got=$(python3 "$CPT" registry resolve "otro:x" || true)
rc=0; python3 "$CPT" registry resolve "otro:x" >/dev/null 2>&1 || rc=$?
[ -z "$got" ] && [ "$rc" -eq 1 ] && _pass "resolve fuera de allowlist → vacío rc=1" \
    || _fail "resolve desconocido: got='$got' rc=$rc"

# namespace custom: registrar con --namespace distinto del name
python3 "$CPT" registry register mitool /repos/mitool --namespace mt >/dev/null
got=$(python3 "$CPT" registry resolve "mt:algo" || true)
[ "$got" = "mitool" ] && _pass "resolve por --namespace custom" || _fail "namespace custom: '$got'"

echo ""
echo "Resultado: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ] && exit 0 || exit 1
