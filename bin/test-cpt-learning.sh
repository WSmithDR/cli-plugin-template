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

# restaurar registry para los tests siguientes
python3 "$CPT" registry register miplugin "$REPO" >/dev/null

echo ""
echo "=== detect-learning.py (PostToolUse) ==="

DETECT="$SCRIPT_DIR/hooks/detect-learning.py"

_detect() {  # $1=file_path $2=session_id $3=tool_output (diff)
    printf '{"tool_input":{"file_path":"%s"},"tool_output":{"diff":"%s"},"session_id":"%s"}' \
        "$1" "$3" "$2" | python3 "$DETECT" 2>&1
}

# Crear un aprendizaje para que detect-learning lo conozca
python3 "$CPT" learning save detect-test "los hooks usan json.load(sys.stdin)" \
    --plugin miplugin --category convencion >/dev/null

# Edit en plugin registrado con diff que contradice aprendizaje -> propone save
out=$(python3 -c "
import json, sys
payload = {'tool_input': {'file_path': sys.argv[1]},
           'tool_output': {'diff': 'hook uses json.load\nimport json'},
           'session_id': sys.argv[2]}
json.dump(payload, sys.stdout)
" "$REPO/skills/x/SKILL.md" s1 | python3 "$DETECT" 2>&1)
echo "$out" | grep -q "hookSpecificOutput" \
    && _pass "diff que contradice aprendizaje -> propone save" || _fail "contradiccion: $out"

# Segunda edicion del mismo archivo en la misma sesion -> callado (cooldown)
out=$(_detect "$REPO/skills/x/SKILL.md" s1 "hook uses regex")
[ -z "$out" ] && _pass "segunda edicion mismo archivo misma sesion -> callado" || _fail "repite: $out"

# Edit fuera de plugin -> silencio
out=$(_detect "/tmp/suelto.md" s1 "hook uses json.load")
[ -z "$out" ] && _pass "edit fuera de plugin -> silencio" || _fail "fuera: $out"

# Sesion nueva -> vuelve a hablar (diff con patron de convencion)
python3 -c "
import json, sys
payload = {'tool_input': {'file_path': sys.argv[1]},
           'tool_output': {'diff': 'hook uses json.load\ntry:\n    sys.path.insert'},
           'session_id': sys.argv[2]}
json.dump(payload, sys.stdout)
" "$REPO/skills/x/SKILL.md" s2 | python3 "$DETECT" 2>&1 | \
    grep -q "hookSpecificOutput" \
    && _pass "sesion nueva -> vuelve a proponer" || _fail "sesion nueva"

# Plugin registrado SIN aprendizajes -> silencio
REPO3=$(mktemp -d); trap 'rm -rf "$DATA" "$REPO" "$REPO2" "$REPO3"' EXIT
python3 "$CPT" registry register vacio2 "$REPO3" >/dev/null
out=$(_detect "$REPO3/a.md" s3 "add something")
[ -z "$out" ] && _pass "plugin sin aprendizajes -> silencio" || _fail "sin learnings: $out"

# Input basura no rompe el hook
rc=0; echo "no-json" | python3 "$DETECT" >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 0 ] && _pass "input no-JSON -> exit 0" || _fail "no-JSON: rc=$rc"

echo ""
echo "=== test-failure-nudge.py + learnings ==="

FAILURE_NUDGE="$SCRIPT_DIR/hooks/test-failure-nudge.py"

# Aprendizaje vigente sobre hooks (bajo cli-plugin-template, que es el plugin que el hook inspecciona)
python3 "$CPT" learning save hooks-en-ts "el shim delega en el .py" --plugin cli-plugin-template >/dev/null

# Suite fallida con output que menciona keywords del aprendizaje -> sugiere learning
out=$(printf '{"tool_input":{"command":"bash bin/test-miplugin.sh"},"error":"Exit code 1\\nshim delega failed"}' \
    | python3 "$FAILURE_NUDGE" 2>&1)
echo "$out" | grep -q "aprendizaje" \
    && _pass "suite fallida contradice aprendizaje -> sugiere learning" || _fail "contradice: $out"

# Suite fallida sin mencion de aprendizajes -> solo feedback (sin learning)
out=$(printf '{"tool_input":{"command":"bash bin/test-miplugin.sh"},"error":"Exit code 1\\nunrelated error"}' \
    | python3 "$FAILURE_NUDGE" 2>&1)
! echo "$out" | grep -q "aprendizaje" \
    && _pass "suite fallida sin mention -> solo feedback" || _fail "sin learning: $out"

# Suite exitosa -> silencio (misma behaviour que antes)
out=$(printf '{"tool_input":{"command":"bash bin/test-miplugin.sh"},"error":"Exit code 0"}' \
    | python3 "$FAILURE_NUDGE" 2>&1)
[ -z "$out" ] && _pass "suite exitosa -> silencio" || _fail "exitosa: $out"

echo ""
echo "Resultado: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ] && exit 0 || exit 1
