#!/bin/bash
# Tests de validate-evals.py. Cada caso en un tmpdir aislado con un skills/ fixture.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATOR="$SCRIPT_DIR/validate-evals.py"
PASS=0; FAIL=0
_pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
_fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

# corre el validador contra un skills/ fixture; devuelve el exit code
run_case() {
    local dir; dir=$(mktemp -d)
    mkdir -p "$dir/skills/demo/evals"
    printf '%s' "$2" > "$dir/skills/demo/evals/evals.json"
    python3 "$VALIDATOR" "$dir/skills" >/dev/null 2>&1; local rc=$?
    rm -rf "$dir"
    return $rc
}

echo ""
echo "=== validate-evals.py ==="

VALID='{"skill":"demo","evals":[{"id":"a","prompt":"x","expectations":["y"]}]}'
run_case ok "$VALID" && _pass "evals bien formado → exit 0" || _fail "válido rechazado"

NO_SKILL='{"evals":[{"id":"a","prompt":"x","expectations":["y"]}]}'
run_case noskill "$NO_SKILL" && _fail "sin skill aceptado" || _pass "falta 'skill' → exit 1"

EMPTY_EXP='{"skill":"demo","evals":[{"id":"a","prompt":"x","expectations":[]}]}'
run_case emptyexp "$EMPTY_EXP" && _fail "expectations vacías aceptadas" || _pass "expectations vacías → exit 1"

DUP_ID='{"skill":"demo","evals":[{"id":"a","prompt":"x","expectations":["y"]},{"id":"a","prompt":"z","expectations":["w"]}]}'
run_case dupid "$DUP_ID" && _fail "id duplicado aceptado" || _pass "id duplicado → exit 1"

BAD_CFG='{"skill":"demo","evals":[{"id":"a","prompt":"x","expectations":["y"]}],"config":{"train_test_split":2}}'
run_case badcfg "$BAD_CFG" && _fail "train_test_split fuera de rango aceptado" || _pass "config inválida → exit 1"

BAD_JSON='{ not json'
run_case badjson "$BAD_JSON" && _fail "JSON roto aceptado" || _pass "JSON inválido → exit 1"

echo ""
echo "Resultado: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ] && exit 0 || exit 1
