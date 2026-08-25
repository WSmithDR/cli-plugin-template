#!/bin/bash
# Tests de los aprendizajes vivos: store (cpt learning) + nudge de PreToolUse.
# Data dir aislado por corrida.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CPT="$SCRIPT_DIR/cpt"
NUDGE="$SCRIPT_DIR/hooks/learning-nudge.py"
PASS=0; FAIL=0
_pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
_fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

DATA=$(mktemp -d)
REPO=$(mktemp -d)
export CLI_PLUGIN_TEMPLATE_DATA_DIR="$DATA"
trap 'rm -rf "$DATA" "$REPO"' EXIT

echo ""
echo "=== cpt learning ==="

# save sin --plugin → scope global
out=$(python3 "$CPT" learning save comillas-en-bash "los paths van entre comillas" \
    --category convencion)
echo "$out" | grep -q "_global/learnings/learning_comillas-en-bash.md" \
    && _pass "save sin --plugin → scope global" || _fail "save global: $out"

# la categoría convencion es global aunque no se pase --plugin
grep -q "^scope: _global$" "$DATA/_global/learnings/learning_comillas-en-bash.md" \
    && grep -q "^category: convencion$" "$DATA/_global/learnings/learning_comillas-en-bash.md" \
    && _pass "frontmatter sellado con scope + category" || _fail "frontmatter global"

# save con --plugin → scope del plugin
out=$(python3 "$CPT" learning save hooks-en-ts "el shim delega en el .py" --plugin miplugin)
echo "$out" | grep -q "miplugin/learnings/learning_hooks-en-ts.md" \
    && _pass "save con --plugin → scope del plugin" || _fail "save plugin: $out"

# upsert por tema: guardar dos veces CORRIGE, no duplica
python3 "$CPT" learning save comillas-en-bash "los paths SIEMPRE entre comillas dobles" \
    --category convencion >/dev/null
count=$(ls "$DATA/_global/learnings/" | wc -l)
body=$(python3 "$CPT" learning show _global comillas-en-bash)
[ "$count" -eq 1 ] && echo "$body" | grep -q "SIEMPRE" \
    && _pass "upsert por slug: corrige, no duplica" || _fail "upsert: count=$count"

# created se preserva entre correcciones, last_updated se actualiza
python3 - "$DATA/_global/learnings/learning_comillas-en-bash.md" <<'PY'
import re, sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text()
p.write_text(re.sub(r"^created: .*$", "created: 2020-01-01", s, count=1, flags=re.M))
PY
python3 "$CPT" learning save comillas-en-bash "otra corrección más" --category convencion >/dev/null
out=$(python3 "$CPT" learning show _global comillas-en-bash)
echo "$out" | grep -q "^created: 2020-01-01$" \
    && ! echo "$out" | grep -q "^last_updated: 2020-01-01$" \
    && _pass "created se preserva, last_updated no" || _fail "fechas: $out"

# list de un plugin trae lo suyo MÁS lo del taller
out=$(python3 "$CPT" learning list --plugin miplugin)
echo "$out" | grep -q "miplugin/hooks-en-ts" && echo "$out" | grep -q "_global/comillas-en-bash" \
    && _pass "list --plugin: plugin + global" || _fail "list plugin: $out"

# list sin plugin trae solo el taller (no vuelca los aprendizajes de todos)
out=$(python3 "$CPT" learning list)
echo "$out" | grep -q "_global/comillas-en-bash" && ! echo "$out" | grep -q "miplugin/" \
    && _pass "list sin --plugin: solo el taller" || _fail "list global: $out"

# filtro por categoría
python3 "$CPT" learning save opencode-config "el hook config registra las skills" \
    --plugin miplugin --category integracion-cli >/dev/null
out=$(python3 "$CPT" learning list --plugin miplugin --category integracion-cli)
[ "$(echo "$out" | wc -l)" -eq 1 ] && echo "$out" | grep -q "opencode-config" \
    && _pass "list --category filtra" || _fail "list category: $out"

# categoría inválida → error, no se escribe
rc=0; python3 "$CPT" learning save x "y" --category inventada >/dev/null 2>&1 || rc=$?
[ "$rc" -ne 0 ] && _pass "categoría inválida → error" || _fail "categoría inválida: rc=$rc"

# delete borra de verdad
python3 "$CPT" learning delete miplugin hooks-en-ts >/dev/null
out=$(python3 "$CPT" learning list --plugin miplugin)
! echo "$out" | grep -q "hooks-en-ts" && _pass "delete borra el aprendizaje" || _fail "delete: $out"

rc=0; python3 "$CPT" learning show miplugin hooks-en-ts >/dev/null 2>&1 || rc=$?
[ "$rc" -ne 0 ] && _pass "show de uno borrado → error" || _fail "show borrado: rc=$rc"

echo ""
echo "=== learning-nudge.py (PreToolUse) ==="

python3 "$CPT" registry register miplugin "$REPO" >/dev/null

_nudge() {  # $1=file_path $2=session_id
    printf '{"tool_input":{"file_path":"%s"},"session_id":"%s"}' "$1" "$2" \
        | python3 "$NUDGE" 2>&1
}

# archivo fuera de todo plugin registrado → silencio
out=$(_nudge "/tmp/cualquier/cosa.md" s1)
[ -z "$out" ] && _pass "archivo fuera de plugin registrado → silencio" || _fail "fuera: $out"

# plugin registrado con aprendizajes → nudge con el comando
out=$(_nudge "$REPO/skills/x/SKILL.md" s1)
echo "$out" | grep -q "additionalContext" && echo "$out" | grep -q "learning list --plugin miplugin" \
    && _pass "plugin registrado con aprendizajes → nudge" || _fail "nudge: $out"

# una sola vez por sesión y plugin
out=$(_nudge "$REPO/otro.md" s1)
[ -z "$out" ] && _pass "segunda edición en la misma sesión → callado" || _fail "repite: $out"

# sesión nueva → vuelve a hablar
out=$(_nudge "$REPO/otro.md" s2)
echo "$out" | grep -q "additionalContext" && _pass "sesión nueva → vuelve a avisar" || _fail "sesión nueva: $out"

# plugin registrado SIN aprendizajes → silencio (nada que consultar)
REPO2=$(mktemp -d); trap 'rm -rf "$DATA" "$REPO" "$REPO2"' EXIT
python3 "$CPT" registry register vacio "$REPO2" >/dev/null
rm -rf "$DATA/_global"
out=$(_nudge "$REPO2/a.md" s3)
[ -z "$out" ] && _pass "plugin sin aprendizajes → silencio" || _fail "sin aprendizajes: $out"

# input basura no rompe el hook
rc=0; echo "no-json" | python3 "$NUDGE" >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 0 ] && _pass "input no-JSON → exit 0" || _fail "no-JSON: rc=$rc"

# store roto no rompe el hook
echo "{" > "$DATA/registry.json"
rc=0; out=$(_nudge "$REPO/x.md" s9) || rc=$?
[ "$rc" -eq 0 ] && [ -z "$out" ] && _pass "registry corrupto → exit 0 silencioso" \
    || _fail "registry corrupto: rc=$rc $out"

echo ""
echo "Resultado: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ] && exit 0 || exit 1
