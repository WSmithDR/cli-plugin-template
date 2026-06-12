#!/bin/bash
# Test de la mecánica cross-repo de plugin-hotpatch (P2): registrar un repo target,
# resolver su local_path, aplicar un patch y commitear SOLO lo parcheado sin arrastrar
# cambios ajenos del working tree. La skill es markdown; acá se valida lo que invoca.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CPT="$SCRIPT_DIR/cpt"
PASS=0; FAIL=0
_pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
_fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

DATA=$(mktemp -d)
TARGET=$(mktemp -d)
export CLI_PLUGIN_TEMPLATE_DATA_DIR="$DATA"
trap 'rm -rf "$DATA" "$TARGET"' EXIT

echo ""
echo "=== plugin-hotpatch cross-repo (mecánica) ==="

# Repo target dummy con un archivo a parchear y un commit base
git -C "$TARGET" init -q
git -C "$TARGET" config user.email "t@t"; git -C "$TARGET" config user.name "t"
mkdir -p "$TARGET/skills/x"
printf 'linea original\n' > "$TARGET/skills/x/SKILL.md"
printf '{"name":"dummy"}\n' > "$TARGET/.claude-plugin-placeholder"
git -C "$TARGET" add -A; git -C "$TARGET" commit -qm "base"

# Registrar el target (Step 1 resuelve local_path desde acá)
python3 "$CPT" registry register dummy "$TARGET" >/dev/null
LP=$(python3 - "$CPT" <<PY
import json,subprocess,sys
out=subprocess.check_output(["python3",sys.argv[1],"registry","list"]).decode()
print(next(e["local_path"] for e in json.loads(out) if e["name"]=="dummy"))
PY
)
[ "$LP" = "$TARGET" ] && _pass "registry resuelve local_path del target" || _fail "local_path: '$LP' != '$TARGET'"

# Cambio ajeno sin commitear en el repo target (no debe entrar al commit del patch)
printf 'cambio ajeno\n' > "$LP/otro.txt"

# Step 5a: aplicar el patch vía ruta absoluta del registry (simula Edit/Write)
printf 'linea parcheada\n' > "$LP/skills/x/SKILL.md"
grep -qx "linea parcheada" "$LP/skills/x/SKILL.md" && _pass "patch aplicado en el repo target" || _fail "patch no aplicado"

# Step 5c: commit ACOTADO — solo el archivo del patch
git -C "$LP" add "skills/x/SKILL.md"
git -C "$LP" commit -qm "hotpatch(skills): patch de prueba"

# El último commit contiene SOLO skills/x/SKILL.md
files=$(git -C "$LP" show --name-only --format="" HEAD | grep -v '^$' || true)
[ "$files" = "skills/x/SKILL.md" ] && _pass "commit toca solo el archivo del patch" || _fail "commit incluyó: [$files]"

# El cambio ajeno sigue sin commitear (no fue arrastrado)
git -C "$LP" status --porcelain | grep -q "otro.txt" && _pass "cambio ajeno queda sin commitear" || _fail "el cambio ajeno fue arrastrado"

echo ""
echo "Resultado: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ] && exit 0 || exit 1
