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

# plugin_version: gana el que declara quien captura, se preserva como created, y a un
# feedback viejo sin sello no se le inventa uno aunque el manifiesto diga otra cosa
REPO=$(mktemp -d); mkdir -p "$REPO/.claude-plugin"
echo '{"version": "2.0.0"}' > "$REPO/.claude-plugin/plugin.json"
python3 "$CPT" registry register versionado "$REPO" >/dev/null
python3 "$CPT" feedback save versionado "observado" - >/dev/null <<'EOF'
---
plugin_version: "1.88.8"
---
la fricción se vio corriendo 1.88.8, no la del repo
EOF
python3 "$CPT" feedback save versionado "del-manifiesto" - >/dev/null <<'EOF'
---
status: pending
---
sin declarar versión: la completa el store
EOF
v="$DATA/versionado/feedbacks/feedback_observado.md"
m="$DATA/versionado/feedbacks/feedback_del-manifiesto.md"
grep -q 'plugin_version: "1.88.8"' "$v" && grep -q 'plugin_version: 2.0.0' "$m" \
    && _pass "plugin_version: gana el declarado; si falta, sale del manifiesto" \
    || _fail "plugin_version: observado='$(cat "$v")' manifiesto='$(cat "$m")'"
python3 "$CPT" feedback save versionado "observado" - >/dev/null <<'EOF'
---
---
re-guardado sin declarar versión
EOF
printf -- '---\n---\nviejo, capturado antes de que existiera el sello\n' \
    > "$DATA/versionado/feedbacks/feedback_sin-sello.md"
python3 "$CPT" feedback save versionado "sin-sello" - >/dev/null <<'EOF'
---
---
re-guardado: sigue sin saberse con qué versión se observó
EOF
grep -q 'plugin_version: "1.88.8"' "$v" \
    && ! grep -q "plugin_version" "$DATA/versionado/feedbacks/feedback_sin-sello.md" \
    && _pass "plugin_version: se preserva al re-guardar y no se inventa para los viejos" \
    || _fail "plugin_version re-save: '$(cat "$v")' / '$(cat "$DATA/versionado/feedbacks/feedback_sin-sello.md")'"
# plugin_path: solo sobrevive si difiere de local_path; nunca se infiere
OTRO=$(mktemp -d)
python3 "$CPT" feedback save versionado "otro-arbol" - <<EOF >/dev/null
---
plugin_path: "$OTRO"
---
la friccion se vio corriendo con --plugin-dir, en otro arbol
EOF
python3 "$CPT" feedback save versionado "mismo-arbol" - <<EOF >/dev/null
---
plugin_path: "$REPO"
---
el --plugin-dir apuntaba al mismo repo del registry
EOF
o="$DATA/versionado/feedbacks/feedback_otro-arbol.md"
s="$DATA/versionado/feedbacks/feedback_mismo-arbol.md"
grep -q "plugin_path: \"$OTRO\"" "$o" && ! grep -q "plugin_path" "$s" \
    && _pass "plugin_path: se sella el arbol ajeno y se borra el redundante" \
    || _fail "plugin_path: otro='$(cat "$o")' mismo='$(cat "$s")'"
python3 "$CPT" feedback save versionado "otro-arbol" - <<'EOF' >/dev/null
---
---
re-guardado sin declarar la ruta
EOF
grep -q "plugin_path: \"$OTRO\"" "$o" \
    && _pass "plugin_path: se preserva al re-guardar" || _fail "plugin_path re-save: '$(cat "$o")'"
rm -rf "$REPO" "$OTRO"

echo ""
echo "=== cpt feedback audit / watch ==="

REPO=$(mktemp -d)
git -C "$REPO" init -q
git -C "$REPO" -c user.email=t@t -c user.name=t commit -q --allow-empty \
    -m "carga: primer commit del repo de pruebas"
HASH=$(git -C "$REPO" rev-parse HEAD)

mkdir -p "$REPO/.claude-plugin"
printf '{"name":"plugtest","version":"0.0.1"}' > "$REPO/.claude-plugin/plugin.json"
python3 "$CPT" registry register plugtest "$REPO" >/dev/null

# caso A: marker RESUELTO con hash real en el cuerpo
python3 "$CPT" feedback save plugtest normalizador-fantasma \
    "el gate inventó formas.

**RESUELTO 2026-08-24, commit \`$HASH\`.**" >/dev/null
# caso B: sin ninguna evidencia
python3 "$CPT" feedback save plugtest otra-cosa "no hay evidencia acá" >/dev/null
# caso C: slug en el subject de un commit posterior
git -C "$REPO" -c user.email=t@t -c user.name=t commit -q --allow-empty \
    -m "gate: cierra plugtest-buscar-sin-proyeccion de raíz"
python3 "$CPT" feedback save plugtest buscar-sin-proyeccion "sin proyección de campos" >/dev/null
# caso D: palabras del slug en el subject SIN el slug literal (drift era ciego acá)
git -C "$REPO" -c user.email=t@t -c user.name=t commit -q --allow-empty \
    -m "feat: núcleo del loop de aprendizajes vivos"
python3 "$CPT" feedback save plugtest loop-aprendizajes-vivos-por-todo "memoria viva del taller" >/dev/null

out=$(python3 "$CPT" feedback audit plugtest)
echo "$out" | grep -q "plugtest/normalizador-fantasma" \
    && echo "$out" | grep -q "plugtest/buscar-sin-proyeccion" \
    && echo "$out" | grep -q "plugtest/loop-aprendizajes-vivos-por-todo" \
    && ! echo "$out" | grep -q "otra-cosa" \
    && echo "$out" | grep -q "$(git -C "$REPO" rev-parse --short HEAD)" \
    && _pass "audit: marker + slug-en-subject + solapamiento-de-palabras detectados" \
    || _fail "audit salida inesperada: '$out'"

python3 "$CPT" feedback watch plugtest
[ -x "$REPO/.git/hooks/post-commit" ] \
    && _pass "watch: instala post-commit ejecutable" \
    || _fail "watch: no instaló el hook"

python3 "$CPT" feedback watch plugtest --remove
[ ! -e "$REPO/.git/hooks/post-commit" ] \
    && _pass "watch --remove: quita el hook" \
    || _fail "watch --remove: el hook sigue ahí"

# léxico de fricción: learn + dedupe + consumo del hook
python3 "$CPT" feedback learn plugtest "esto es un bardo" >/dev/null
python3 "$CPT" feedback learn plugtest "esto es un bardo" >/dev/null
python3 "$CPT" feedback learn plugtest "otra vez este tema" >/dev/null
short=$(python3 "$CPT" feedback learn plugtest "no")
echo "$short" | grep -q '"ok": false' \
    && _pass "learn: frase corta rechazada" || _fail "learn corto: '$short'"
lex=$(LEXDIR="$DATA" python3 -c "import json,sys; sys.path.insert(0,'$SCRIPT_DIR/lib'); import gateway, paths; print(json.dumps(gateway._read_json(paths.friction_lexicon_file(), {})))")
echo "$lex" | grep -q '"hits": 2' && echo "$lex" | grep -q 'otra vez este tema' \
    && _pass "learn: dedupe suma hits y frases distintas conviven" || _fail "lexicon: '$lex'"

# stop hook: _drift_message detecta el hallazgo y se calla en la segunda pasada (dedupe)
HOOKS="$SCRIPT_DIR/hooks"
drift_run() {
    (cd "$REPO" && HOOKS="$HOOKS" python3 - <<'PYEOF'
import importlib.util, os
spec = importlib.util.spec_from_file_location(
    "dpf", os.environ["HOOKS"] + "/detect-pending-feedback.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print(m._drift_message())
PYEOF
)
}
drift=$(drift_run)
echo "$drift" | grep -q "normalizador-fantasma" \
    && _pass "stop-hook: _drift_message lista el hallazgo" \
    || _fail "stop-hook drift vacío: '$drift'"
kw=$(cd "$REPO" && HOOKS="$HOOKS" python3 - <<'PYEOF'
import importlib.util, os
spec = importlib.util.spec_from_file_location(
    "dpf", os.environ["HOOKS"] + "/detect-pending-feedback.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print(any("bardo" in k for k in m._keywords()) and "otra vez este tema" in m._keywords())
PYEOF
)
[ "$kw" = "True" ] && _pass "hook: _keywords() incluye el léxico aprendido" \
    || _fail "hook keywords: '$kw'"
drift2=$(drift_run)
[ -z "$drift2" ] && _pass "stop-hook: segunda pasada callada (dedupe por stamp)" \
    || _fail "stop-hook repite mensaje: '$drift2'"

# audit sin plugin conocido no explota
python3 "$CPT" feedback audit plugtest-inexistente >/dev/null 2>&1 \
    && _pass "audit: plugin desconocido devuelve vacío sin error" \
    || _fail "audit falló con plugin desconocido"
rm -rf "$REPO"

echo ""
echo "=== cpt feedback dedup + defer ==="

# save new feedback creates it
python3 "$CPT" feedback save test-plugin "new-feature" - >/dev/null <<'EOF'
---
name: feedback-new-feature
plugin: test-plugin
---
nuevo feedback
EOF
f="$DATA/test-plugin/feedbacks/feedback_new-feature.md"
[ -f "$f" ] && _pass "save creates new feedback" || _fail "save: no existe $f"

# re-save with same slug and pending status → skip (dedup)
out=$(python3 "$CPT" feedback save test-plugin "new-feature" - <<< "duplicado" 2>&1)
echo "$out" | grep -q "ya existe con status pending" && _pass "dedup: pending feedback not duplicated" \
    || _fail "dedup: should have returned pending dedup message, got: $out"

# defer a feedback
python3 "$CPT" feedback defer test-plugin "new-feature" >/dev/null
grep -q "^status: deferred" "$f" && _pass "defer: status changes to deferred" \
    || _fail "defer: '$(cat "$f")'"

# re-save with same slug while deferred → skip (dedup)
out=$(python3 "$CPT" feedback save test-plugin "new-feature" - <<< "duplicado" 2>&1)
echo "$out" | grep -q "ya existe con status deferred" && _pass "dedup: deferred feedback not duplicated" \
    || _fail "dedup: should have returned deferred dedup message, got: $out"

# apply then re-save → preserves applied status, dedup does not block
python3 "$CPT" feedback apply test-plugin "new-feature" >/dev/null
python3 "$CPT" feedback save test-plugin "new-feature" - >/dev/null <<'EOF'
---
name: feedback-new-feature
plugin: test-plugin
---
reactivado
EOF
grep -q "^status: applied" "$f" && grep -q "reactivado" "$f" \
    && _pass "re-save: applied feedback preserves status, updates body" \
    || _fail "re-save applied: '$(cat "$f")'"

# discard then re-save → preserves discarded status, dedup does not block
python3 "$CPT" feedback discard test-plugin "new-feature" >/dev/null
python3 "$CPT" feedback save test-plugin "new-feature" - >/dev/null <<'EOF'
---
name: feedback-new-feature
plugin: test-plugin
---
reactivado2
EOF
grep -q "^status: discarded" "$f" && grep -q "reactivado2" "$f" \
    && _pass "re-save: discarded feedback preserves status, updates body" \
    || _fail "re-save discarded: '$(cat "$f")'"

# list --deferred shows only deferred feedbacks
python3 "$CPT" feedback save test-plugin "deferred-test" - >/dev/null <<'EOF'
---
name: feedback-deferred-test
plugin: test-plugin
---
para deferir
EOF
python3 "$CPT" feedback defer test-plugin "deferred-test" >/dev/null
out=$(python3 "$CPT" feedback list --deferred 2>&1)
echo "$out" | grep -q "test-plugin/deferred-test" \
    && ! echo "$out" | grep -q "test-plugin/new-feature" \
    && _pass "list --deferred: solo los pospuestos" \
    || _fail "list --deferred: '$out'"

# plugin como argumento posicional == --plugin, y el volcado cross-plugin avisa por stderr
pos=$(python3 "$CPT" feedback list ankify)
flag=$(python3 "$CPT" feedback list --plugin ankify)
[ "$pos" = "$flag" ] && [ -n "$pos" ] \
    && _pass "list <plugin> posicional == --plugin" \
    || _fail "posicional: pos='$pos' flag='$flag'"

err=$(python3 "$CPT" feedback list --pending 2>&1 >/dev/null)
echo "$err" | grep -q "filtrá con" \
    && _pass "list sin plugin y multi-plugin → hint por stderr" \
    || _fail "hint stderr: '$err'"

# --update: sobrescribe un pending existente (acumular ocurrencias) sin duplicar
python3 "$CPT" feedback save nuevo "recurrente" - >/dev/null <<'EOF'
---
status: pending
---
ocurrencia 1
EOF
out=$(python3 "$CPT" feedback save nuevo "recurrente" - <<'EOF'
---
status: pending
---
ocurrencia 1
ocurrencia 2
EOF
)
echo "$out" | grep -q "ya existe" \
    && _pass "save sin --update: dedup intacto sobre pending" \
    || _fail "dedup: '$out'"

python3 "$CPT" feedback save nuevo "recurrente" - --update >/dev/null <<'EOF'
---
status: pending
---
ocurrencia 1
ocurrencia 2
EOF
body="$DATA/nuevo/feedbacks/feedback_recurrente.md"
grep -q "ocurrencia 2" "$body" && grep -qx "status: pending" "$body" \
    && _pass "save --update: suma la ocurrencia y conserva status pending" \
    || _fail "--update: '$(cat "$body")'"

echo ""
echo "Resultado: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ] && exit 0 || exit 1
