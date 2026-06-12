#!/bin/bash
# Tests del dashboard de evolución (cpt status). Data dir aislado.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CPT="$SCRIPT_DIR/cpt"
PASS=0; FAIL=0
_pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
_fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

DATA=$(mktemp -d)
export CLI_PLUGIN_TEMPLATE_DATA_DIR="$DATA"
trap 'rm -rf "$DATA"' EXIT

# helper: extrae un valor de totals del --json
total() { python3 -c "import json,sys;print(json.load(sys.stdin)['totals']['$1'])"; }

echo ""
echo "=== cpt status ==="

# store vacío → mensaje guía, no rompe
out=$(python3 "$CPT" status); rc=$?
[ $rc -eq 0 ] && echo "$out" | grep -q "sin plugins registrados" && _pass "store vacío → mensaje guía" || _fail "vacío: $out"

# datos mixtos
python3 "$CPT" registry register ankify /repos/ankify --namespace ankify >/dev/null
python3 "$CPT" registry register mitool /repos/mitool >/dev/null
python3 "$CPT" feedback save ankify a - >/dev/null <<<$'---\napplied: false\n---\nx'
python3 "$CPT" feedback save ankify b - >/dev/null <<<$'---\napplied: true\n---\ny'
python3 "$CPT" proposal save ankify a - >/dev/null <<<$'---\nstatus: pending\n---\np'
python3 "$CPT" proposal save ankify b - >/dev/null <<<$'---\nstatus: approved\n---\nq'

# conteos en --json
j=$(python3 "$CPT" status --json)
[ "$(echo "$j" | total plugins)" = "2" ]            && _pass "totals.plugins = 2" || _fail "plugins"
[ "$(echo "$j" | total feedbacks_pending)" = "1" ]  && _pass "feedbacks_pending = 1" || _fail "fb_pending"
[ "$(echo "$j" | total feedbacks_applied)" = "1" ]  && _pass "feedbacks_applied = 1" || _fail "fb_applied"
[ "$(echo "$j" | total proposals_pending)" = "1" ]  && _pass "proposals_pending = 1" || _fail "pr_pending"
[ "$(echo "$j" | total proposals_approved)" = "1" ] && _pass "proposals_approved = 1" || _fail "pr_approved"

# --plugin filtra
n=$(python3 "$CPT" status --plugin ankify --json | python3 -c "import json,sys;print(len(json.load(sys.stdin)['plugins']))")
[ "$n" = "1" ] && _pass "--plugin filtra a 1 fila" || _fail "--plugin: $n"

# tabla humana lista el plugin
python3 "$CPT" status | grep -q "ankify" && _pass "tabla humana muestra el plugin" || _fail "tabla humana"

echo ""
echo "Resultado: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ] && exit 0 || exit 1
