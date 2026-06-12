#!/bin/bash
# Tests de bump-version.py. Cada caso en un tmpdir aislado con manifiestos fixture.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUMP="$SCRIPT_DIR/bump-version.py"
PASS=0; FAIL=0
_pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
_fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

# crea un repo fixture con plugin.json + marketplace.json + un manifiesto CLI
make_fixture() {
    local dir="$1" v="$2"
    mkdir -p "$dir/.claude-plugin"
    printf '{\n  "name": "demo",\n  "version": "%s"\n}\n' "$v" > "$dir/.claude-plugin/plugin.json"
    printf '{\n  "metadata": { "version": "%s" },\n  "plugins": [ { "name": "demo", "version": "%s" } ]\n}\n' "$v" "$v" > "$dir/.claude-plugin/marketplace.json"
    printf '{\n  "name": "demo",\n  "version": "%s"\n}\n' "$v" > "$dir/gemini-extension.json"
}

ver() { python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['version'])" "$1"; }
mkt_meta() { python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['metadata']['version'])" "$1"; }

echo ""
echo "=== bump-version.py ==="

# Caso 1: minor bumpea y sincroniza TODO
d=$(mktemp -d); make_fixture "$d" "1.2.3"
python3 "$BUMP" minor --root "$d" >/dev/null
if [ "$(ver "$d/.claude-plugin/plugin.json")" = "1.3.0" ] \
   && [ "$(ver "$d/gemini-extension.json")" = "1.3.0" ] \
   && [ "$(mkt_meta "$d/.claude-plugin/marketplace.json")" = "1.3.0" ] \
   && [ "$(ver "$d/.claude-plugin/marketplace.json" 2>/dev/null || echo)" != "1.2.3" ]; then
    _pass "minor 1.2.3 → 1.3.0 en todos"
else
    _fail "minor no sincronizó todo"
fi
rm -rf "$d"

# Caso 2: major y patch
d=$(mktemp -d); make_fixture "$d" "1.2.3"
python3 "$BUMP" major --root "$d" >/dev/null
[ "$(ver "$d/.claude-plugin/plugin.json")" = "2.0.0" ] && _pass "major → 2.0.0" || _fail "major"
python3 "$BUMP" patch --root "$d" >/dev/null
[ "$(ver "$d/gemini-extension.json")" = "2.0.1" ] && _pass "patch → 2.0.1 propagado" || _fail "patch"
rm -rf "$d"

# Caso 3: --set fija versión exacta
d=$(mktemp -d); make_fixture "$d" "1.2.3"
python3 "$BUMP" --set 5.4.3 --root "$d" >/dev/null
[ "$(ver "$d/.claude-plugin/plugin.json")" = "5.4.3" ] && _pass "--set 5.4.3" || _fail "--set"
rm -rf "$d"

# Caso 4: --check detecta drift (exit 1)
d=$(mktemp -d); make_fixture "$d" "1.0.0"
printf '{\n  "name": "demo",\n  "version": "9.9.9"\n}\n' > "$d/gemini-extension.json"
python3 "$BUMP" --check --root "$d" >/dev/null 2>&1 && _fail "drift no detectado" || _pass "--check drift → exit 1"
# y --sync lo arregla
python3 "$BUMP" --sync --root "$d" >/dev/null
[ "$(ver "$d/gemini-extension.json")" = "1.0.0" ] && _pass "--sync corrige drift" || _fail "--sync"
python3 "$BUMP" --check --root "$d" >/dev/null 2>&1 && _pass "--check tras sync → exit 0" || _fail "--check post-sync"
rm -rf "$d"

# Caso 5: --set con semver inválido falla
d=$(mktemp -d); make_fixture "$d" "1.0.0"
python3 "$BUMP" --set 1.2 --root "$d" >/dev/null 2>&1 && _fail "semver inválido aceptado" || _pass "--set inválido → error"
rm -rf "$d"

echo ""
echo "Resultado: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ] && exit 0 || exit 1
