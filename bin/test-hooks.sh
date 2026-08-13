#!/bin/bash
# Tests del hook SessionStart del meta-plugin. Cada caso en un tmpdir aislado.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$SCRIPT_DIR/hooks/session-start.sh"
PASS=0; FAIL=0
_pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
_fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

run_in_tmpdir() {
    local dir; dir=$(mktemp -d)
    (cd "$dir" && eval "$1"); local rc=$?
    rm -rf "$dir"; return $rc
}

echo ""
echo "=== session-start.sh ==="

# Caso 1: repo del catálogo (.catalog-root) → exit 0, sin output
result=$(run_in_tmpdir '
    touch .catalog-root
    out=$(bash '"$HOOK"' 2>&1); rc=$?
    [ $rc -eq 0 ] && [ -z "$out" ] && echo OK || echo "rc=$rc out=$out"
')
[ "$result" = "OK" ] && _pass ".catalog-root → exit 0 silencioso" || _fail ".catalog-root → $result"

# Caso 2: no es proyecto de plugin → exit 0, sin output
result=$(run_in_tmpdir '
    out=$(bash '"$HOOK"' 2>&1); rc=$?
    [ $rc -eq 0 ] && [ -z "$out" ] && echo OK || echo "rc=$rc out=$out"
')
[ "$result" = "OK" ] && _pass "sin .claude-plugin/ → exit 0 silencioso" || _fail "sin .claude-plugin/ → $result"

# Caso 3: proyecto de plugin, primera vez → avisa + crea marcador
result=$(run_in_tmpdir '
    git init -q; mkdir -p .claude-plugin
    out=$(bash '"$HOOK"' 2>&1); rc=$?
    marker="$(git rev-parse --git-dir)/cli-plugin-template.seen"
    [ $rc -eq 0 ] && echo "$out" | grep -q "CLI-PLUGIN-TEMPLATE" && [ -f "$marker" ] && echo OK || echo "rc=$rc out=$out"
')
[ "$result" = "OK" ] && _pass "plugin nuevo → avisa + marcador" || _fail "plugin nuevo → $result"

# Caso 4: segunda vez (marcador presente) → sin output
result=$(run_in_tmpdir '
    git init -q; mkdir -p .claude-plugin
    bash '"$HOOK"' >/dev/null 2>&1
    out=$(bash '"$HOOK"' 2>&1); rc=$?
    [ $rc -eq 0 ] && [ -z "$out" ] && echo OK || echo "rc=$rc out=$out"
')
[ "$result" = "OK" ] && _pass "segunda sesión → sin aviso" || _fail "segunda sesión → $result"

# Caso 5: plugin con plugin.json, NO registrado → aviso incluye oferta de registro
result=$(run_in_tmpdir '
    export CLI_PLUGIN_TEMPLATE_DATA_DIR=$(mktemp -d)
    git init -q; mkdir -p .claude-plugin
    printf "{\"name\":\"testplug\"}" > .claude-plugin/plugin.json
    out=$(bash '"$HOOK"' 2>&1); rc=$?
    rm -rf "$CLI_PLUGIN_TEMPLATE_DATA_DIR"
    [ $rc -eq 0 ] && echo "$out" | grep -q "registry de evolución" && echo OK || echo "rc=$rc out=$out"
')
[ "$result" = "OK" ] && _pass "plugin no registrado → ofrece registrarlo (plugin-register)" || _fail "no registrado → $result"

# Caso 6: plugin ya registrado → aviso de auditoría SIN la oferta de registro
result=$(run_in_tmpdir '
    export CLI_PLUGIN_TEMPLATE_DATA_DIR=$(mktemp -d)
    git init -q; mkdir -p .claude-plugin
    printf "{\"name\":\"testplug\"}" > .claude-plugin/plugin.json
    python3 '"$SCRIPT_DIR/cpt"' registry register testplug "$PWD" >/dev/null
    out=$(bash '"$HOOK"' 2>&1); rc=$?
    rm -rf "$CLI_PLUGIN_TEMPLATE_DATA_DIR"
    echo "$out" | grep -q "CLI-PLUGIN-TEMPLATE" && ! echo "$out" | grep -q "registry de evolución" && echo OK || echo "rc=$rc out=$out"
')
[ "$result" = "OK" ] && _pass "plugin registrado → sin oferta de registro" || _fail "registrado → $result"

# Caso 7: el catálogo avanzó desde la última auditoría → vuelve a avisar (drift)
result=$(run_in_tmpdir '
    git init -q; mkdir -p .claude-plugin
    echo "0.0.1" > "$(git rev-parse --git-dir)/cli-plugin-template.seen"
    out=$(bash '"$HOOK"' 2>&1); rc=$?
    [ $rc -eq 0 ] && echo "$out" | grep -q "el catálogo avanzó" && echo OK || echo "rc=$rc out=$out"
')
[ "$result" = "OK" ] && _pass "catálogo avanzó → re-sugiere auditoría" || _fail "drift → $result"

# Caso 8: plugin solo-Claude-Code → ofrece multi-cli-compat; con manifiesto ajeno, no
result=$(run_in_tmpdir '
    git init -q; mkdir -p .claude-plugin
    out=$(bash '"$HOOK"' 2>&1)
    echo "$out" | grep -q "multi-cli-compat" || { echo "falta oferta: $out"; exit 0; }
    rm -f "$(git rev-parse --git-dir)/cli-plugin-template.seen"
    touch AGENTS.md
    out=$(bash '"$HOOK"' 2>&1)
    echo "$out" | grep -q "multi-cli-compat" && echo "ofreció igual: $out" || echo OK
')
[ "$result" = "OK" ] && _pass "solo Claude Code → ofrece multi-cli-compat" || _fail "multi-cli → $result"

echo ""
echo "Resultado: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ] && exit 0 || exit 1
