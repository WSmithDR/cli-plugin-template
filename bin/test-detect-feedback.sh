#!/bin/bash
# Tests del Stop hook detect-pending-feedback.py. Data dir aislado.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CPT="$SCRIPT_DIR/cpt"
HOOK="$SCRIPT_DIR/hooks/detect-pending-feedback.py"
PASS=0; FAIL=0
_pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
_fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

DATA=$(mktemp -d)
export CLI_PLUGIN_TEMPLATE_DATA_DIR="$DATA"
trap 'rm -rf "$DATA"' EXIT

echo ""
echo "=== detect-pending-feedback.py ==="

# sin pendientes → sin output, exit 0
out=$(echo '{"transcript_path":""}' | python3 "$HOOK" 2>&1); rc=$?
[ $rc -eq 0 ] && [ -z "$out" ] && _pass "sin pendientes → sin output" || _fail "vacío: rc=$rc out=$out"

# con un pendiente → systemMessage con count y la referencia a plugin-hotpatch
python3 "$CPT" feedback save ankify foo - >/dev/null <<'EOF'
---
applied: false
---
x
EOF
out=$(echo '{"transcript_path":""}' | python3 "$HOOK" 2>&1)
echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'systemMessage' in d; assert 'PENDING PLUGIN FEEDBACK' in d['systemMessage']; assert 'plugin-hotpatch' in d['systemMessage']" \
    && _pass "pendiente → systemMessage válido" || _fail "pendiente: $out"

# input inválido (sin transcript_path) no rompe
out=$(echo 'no-json' | python3 "$HOOK" 2>&1); rc=$?
[ $rc -eq 0 ] && _pass "input no-JSON no rompe el hook" || _fail "no-JSON: rc=$rc out=$out"

# fricción en transcript con plugin registrado → sugiere feedback-harvester
python3 "$CPT" registry register ankify /tmp/x >/dev/null
TRANSCRIPT="$DATA/t.jsonl"
printf '{"type":"user","message":{"content":"la skill ankify:anki-capture no funciona"}}\n' > "$TRANSCRIPT"
out=$(echo "{\"transcript_path\":\"$TRANSCRIPT\"}" | python3 "$HOOK" 2>&1)
echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'POSSIBLE PLUGIN FRICTION' in d['systemMessage']; assert 'feedback-harvester' in d['systemMessage']" \
    && _pass "fricción → sugiere feedback-harvester" || _fail "fricción: $out"

# segundo Stop sin contenido nuevo → no repite la sugerencia (idempotente por offset)
out=$(echo "{\"transcript_path\":\"$TRANSCRIPT\"}" | python3 "$HOOK" 2>&1)
echo "$out" | grep -q "POSSIBLE PLUGIN FRICTION" \
    && _fail "idempotencia: repitió la sugerencia" || _pass "sin contenido nuevo → no repite"

# fallo del plugin SIN queja del usuario → igual dispara la cosecha
printf '{"type":"tool_result","is_error":true,"content":"Traceback: /tmp/x/ankify/bin/cpt: command not found"}\n' >> "$TRANSCRIPT"
out=$(echo "{\"transcript_path\":\"$TRANSCRIPT\"}" | python3 "$HOOK" 2>&1)
echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'POSSIBLE PLUGIN FRICTION' in d['systemMessage']; assert 'observed failures' in d['systemMessage']" \
    && _pass "error sin queja → dispara cosecha" || _fail "error: $out"

# error que no nombra un plugin registrado → no dispara (código del usuario)
printf '{"type":"tool_result","is_error":true,"content":"Traceback: src/app.py line 3"}\n' >> "$TRANSCRIPT"
out=$(echo "{\"transcript_path\":\"$TRANSCRIPT\"}" | python3 "$HOOK" 2>&1)
echo "$out" | grep -q "POSSIBLE PLUGIN FRICTION" \
    && _fail "error ajeno: disparó igual" || _pass "error ajeno al plugin → no dispara"

# promote: repo registrado con cambios sin commitear en infra → sugiere plugin-promote
REPO="$DATA/repo"
mkdir -p "$REPO/hooks"
git -C "$REPO" init -q 2>/dev/null
git -C "$REPO" -c user.email=t@t -c user.name=t commit -q --allow-empty -m init
python3 "$CPT" registry register promo-plugin "$REPO" >/dev/null
echo "x" > "$REPO/hooks/thing.sh"; git -C "$REPO" add -A
out=$(cd "$REPO" && echo '{"transcript_path":""}' | python3 "$HOOK" 2>&1)
echo "$out" | grep -q "POSSIBLE CATALOG PROMOTION" \
    && _pass "infra sin commitear → sugiere promote" || _fail "promote: $out"

# mismo set de archivos → no repite
out=$(cd "$REPO" && echo '{"transcript_path":""}' | python3 "$HOOK" 2>&1)
echo "$out" | grep -q "POSSIBLE CATALOG PROMOTION" \
    && _fail "promote: repitió con el mismo set" || _pass "mismo set → no repite"

# cambio de dominio (no infra) → no sugiere promote
git -C "$REPO" -c user.email=t@t -c user.name=t commit -q -m infra
mkdir -p "$REPO/src"; echo "y" > "$REPO/src/domain.py"; git -C "$REPO" add -A
out=$(cd "$REPO" && echo '{"transcript_path":""}' | python3 "$HOOK" 2>&1)
echo "$out" | grep -q "POSSIBLE CATALOG PROMOTION" \
    && _fail "promote: disparó con cambio de dominio" || _pass "cambio de dominio → no sugiere"

echo ""
echo "Resultado: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ] && exit 0 || exit 1
