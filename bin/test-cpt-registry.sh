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
echo "=== gather-plugin-metadata (alta desde cualquier cwd) ==="

GATHER="$SCRIPT_DIR/../skills/plugin-register/scripts/gather-plugin-metadata.sh"
FAKE=$(mktemp -d)
trap 'rm -rf "$DATA" "$FAKE"' EXIT
mkdir -p "$FAKE/repo/.claude-plugin" "$FAKE/hogar/.claude/plugins/cache/foo/.claude-plugin"
echo '{"name": "miplugin"}' > "$FAKE/repo/.claude-plugin/plugin.json"
echo '{"name": "foo"}' > "$FAKE/hogar/.claude/plugins/cache/foo/.claude-plugin/plugin.json"

# ruta explícita desde un cwd que NO es el repo del plugin
out=$(cd / && bash "$GATHER" "$FAKE/repo")
echo "$out" | grep -q "^NAME=miplugin$" && echo "$out" | grep -q "^LOCAL_PATH=$FAKE/repo$" \
    && _pass "gather con ruta explícita desde otro cwd" || _fail "gather ruta explícita: $out"

# sin argumento → cwd (comportamiento histórico)
out=$(cd "$FAKE/repo" && bash "$GATHER")
echo "$out" | grep -q "^NAME=miplugin$" && _pass "gather sin argumento → cwd" \
    || _fail "gather sin arg: $out"

# ruta que no es un plugin → rc=1
rc=0; bash "$GATHER" "$FAKE" >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 1 ] && _pass "gather ruta sin manifiesto → rc=1" || _fail "gather sin manifiesto: rc=$rc"

# ruta inexistente → rc=1
rc=0; bash "$GATHER" "$FAKE/nope" >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 1 ] && _pass "gather ruta inexistente → rc=1" || _fail "gather inexistente: rc=$rc"

# copia del cache → rechazada (local_path debe ser el repo, no la instalación)
rc=0; err=$(HOME="$FAKE/hogar" bash "$GATHER" "$FAKE/hogar/.claude/plugins/cache/foo" 2>&1) || rc=$?
[ "$rc" -eq 1 ] && echo "$err" | grep -qi "cache" \
    && _pass "gather rechaza ruta del cache de plugins" || _fail "gather cache: rc=$rc $err"

echo ""
echo "Resultado: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ] && exit 0 || exit 1
