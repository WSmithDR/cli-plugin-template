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

# el store sella status + created + last_updated, y convierte el booleano viejo
TODAY=$(python3 -c 'import datetime; print(datetime.datetime.now(datetime.timezone.utc).date())')
grep -q "^status: pending" "$f" && grep -qx "created: $TODAY" "$f" && grep -qx "last_updated: $TODAY" "$f" \
    && ! grep -qE "^applied:" "$f" \
    && _pass "save → status + created + last_updated, sin booleanos viejos" \
    || _fail "save frontmatter: '$(cat "$f")'"

# re-guardar preserva created y el status ya marcado; el cuerpo sí se actualiza
python3 "$CPT" feedback save nuevo "fechas" - >/dev/null <<'EOF'
---
created: 2020-01-01
status: applied
---
primera versión
EOF
python3 "$CPT" feedback save nuevo "fechas" - >/dev/null <<'EOF'
---
created: 1999-12-31
status: pending
---
descripción corregida
EOF
g="$DATA/nuevo/feedbacks/feedback_fechas.md"
grep -qx "created: 2020-01-01" "$g" && grep -qx "status: applied" "$g" \
    && grep -qx "last_updated: $TODAY" "$g" && grep -q "descripción corregida" "$g" \
    && _pass "re-save: preserva created y status, refresca last_updated y el cuerpo" \
    || _fail "re-save: '$(cat "$g")'"

# list --pending lo incluye (formato viejo applied:false → retro-compat)
out=$(python3 "$CPT" feedback list --pending)
echo "$out" | grep -qx "ankify/namespace-issue" && _pass "retro-compat: list --pending incluye applied:false" \
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

# status: <estado> (formato actual) manda sobre los booleanos viejos
python3 "$CPT" feedback save nuevo "con-status" - >/dev/null <<'EOF'
---
status: applied
applied: false
---
el status manda
EOF
pend=$(python3 "$CPT" feedback list --pending --plugin nuevo)
appl=$(python3 "$CPT" feedback list --plugin nuevo --state applied)
[ -z "$pend" ] && echo "$appl" | grep -qx "nuevo/con-status" \
    && _pass "status: applied gana sobre applied:false (formato viejo)" \
    || _fail "status manda: pend='$pend' appl='$appl'"

# discard: sale de --pending, aparece en --state discarded, no cuenta como aplicado
python3 "$CPT" feedback discard ankify "namespace-issue" >/dev/null
grep -q "^status: discarded" "$f" && grep -q "^last_updated: " "$f" \
    && _pass "discard → status: discarded + last_updated" || _fail "discard: frontmatter '$(cat "$f")'"
grep -qE "^(applied|discarded)(_at)?:" "$f" \
    && _fail "quedaron booleanos viejos: '$(cat "$f")'" \
    || _pass "marcar limpia los booleanos viejos del frontmatter"

# el body no se toca aunque cite 'applied:' en un snippet
python3 "$CPT" feedback save nuevo "body-intacto" - >/dev/null <<'EOF'
---
applied: false
---
el usuario escribió `applied: true` en su config
EOF
python3 "$CPT" feedback apply nuevo "body-intacto" >/dev/null
b="$DATA/nuevo/feedbacks/feedback_body-intacto.md"
grep -q 'su config' "$b" && grep -q '`applied: true`' "$b" \
    && _pass "el body queda intacto (solo se limpia el frontmatter)" || _fail "body: '$(cat "$b")'"
pend=$(python3 "$CPT" feedback list --pending --plugin ankify)
disc=$(python3 "$CPT" feedback list --plugin ankify --state discarded)
echo "$pend" | grep -q "namespace-issue" && _fail "descartado sigue en --pending" \
    || { echo "$disc" | grep -qx "ankify/namespace-issue" \
         && _pass "descartado: fuera de --pending, dentro de --state discarded" \
         || _fail "--state discarded: '$disc'"; }
counts=$(python3 "$CPT" status --plugin ankify --json)
echo "$counts" | python3 -c 'import json,sys; fb=json.load(sys.stdin)["plugins"][0]["feedbacks"]; \
    assert fb=={"pending":0,"applied":1,"discarded":1,"total":2}, fb' \
    && _pass "status: descartado no cuenta como aplicado" || _fail "status: $counts"

echo ""
echo "Resultado: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ] && exit 0 || exit 1
