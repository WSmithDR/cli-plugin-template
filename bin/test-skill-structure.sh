#!/bin/bash
# Tests de bin/audit-skill-structure.py. Cada caso en un tmpdir aislado.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUDIT="$SCRIPT_DIR/../features/skill-structure-audit/files/audit-skill-structure.py"
PASS=0; FAIL=0
_pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
_fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

run_in_tmpdir() {
    local dir; dir=$(mktemp -d)
    (cd "$dir" && eval "$1"); local rc=$?
    rm -rf "$dir"; return $rc
}

echo ""
echo "=== audit-skill-structure.py ==="

# Caso 1: sin skills/ → WARNING, exit 2 (WARN threshold default)
result=$(run_in_tmpdir '
    out=$(python3 '"$AUDIT"' 2>&1); rc=$?
    echo "rc=$rc out=$out"
')
echo "$result" | grep -q "No hay skills" && _pass "sin skills/ → avisa" || _fail "sin skills/ → $result"

# Caso 2: skill limpia (solo SKILL.md) → sin hallazgos
result=$(run_in_tmpdir '
    mkdir -p skills/foo
    echo "# Foo skill" > skills/foo/SKILL.md
    out=$(python3 '"$AUDIT"' --json 2>&1); rc=$?
    [ "$out" = "[]" ] && echo OK || echo "rc=$rc out=$out"
')
[ "$result" = "OK" ] && _pass "skill limpia → 0 hallazgos" || _fail "skill limpia → $result"

# Caso 3: script suelto en raíz → ERROR
result=$(run_in_tmpdir '
    mkdir -p skills/foo
    echo "# Foo" > skills/foo/SKILL.md
    echo "echo hola" > skills/foo/install.sh
    out=$(python3 '"$AUDIT"' --json 2>&1); rc=$?
    echo "$out" | grep -q "\"severity\": \"ERROR\"" && echo OK || echo "rc=$rc no ERROR"
')
[ "$result" = "OK" ] && _pass ".sh en raíz → ERROR" || _fail ".sh en raíz → $result"

# Caso 4: .md extra en raíz → WARNING
result=$(run_in_tmpdir '
    mkdir -p skills/foo
    echo "# Foo" > skills/foo/SKILL.md
    echo "notas" > skills/foo/notas.md
    out=$(python3 '"$AUDIT"' --json 2>&1); rc=$?
    echo "$out" | grep -q "\"severity\": \"WARNING\"" && echo OK || echo "rc=$rc no WARNING"
')
[ "$result" = "OK" ] && _pass ".md extra en raíz → WARNING" || _fail ".md extra en raíz → $result"

# Caso 5: bloque bash de >2 líneas → ERROR
result=$(run_in_tmpdir '
    mkdir -p skills/foo
    printf "# Foo\n\n\`\`\`bash\n" > skills/foo/SKILL.md
    for i in $(seq 1 15); do echo "  echo \"linea \$i\""; done >> skills/foo/SKILL.md
    printf "\`\`\`\n" >> skills/foo/SKILL.md
    out=$(python3 '"$AUDIT"' --json 2>&1); rc=$?
    echo "$out" | grep -q "\"severity\": \"ERROR\"" && echo OK || echo "rc=$rc out=$out"
')
[ "$result" = "OK" ] && _pass "bloque bash >2 líneas → ERROR" || _fail "bloque bash >2 líneas → $result"

# Caso 5b: bloque bash de ≤2 líneas (invocación corta) → tolerado, sin hallazgos
result=$(run_in_tmpdir '
    mkdir -p skills/foo
    printf "# Foo\n\n\`\`\`bash\npython3 bin/cpt feedback list\n\`\`\`\n" > skills/foo/SKILL.md
    out=$(python3 '"$AUDIT"' --json 2>&1); rc=$?
    [ "$out" = "[]" ] && echo OK || echo "rc=$rc out=$out"
')
[ "$result" = "OK" ] && _pass "bloque bash ≤2 líneas → tolerado" || _fail "bloque bash ≤2 líneas → $result"

# Caso 5c: bloque sin lenguaje (árbol de directorios, ```text) → no se marca
result=$(run_in_tmpdir '
    mkdir -p skills/foo
    printf "# Foo\n\n\`\`\`\nskills/foo/\n  SKILL.md\n\`\`\`\n" > skills/foo/SKILL.md
    out=$(python3 '"$AUDIT"' --json 2>&1); rc=$?
    [ "$out" = "[]" ] && echo OK || echo "rc=$rc out=$out"
')
[ "$result" = "OK" ] && _pass "bloque sin lenguaje → ignorado" || _fail "bloque sin lenguaje → $result"

# Caso 6: --threshold ERROR → solo ERROR bloquea, WARNING no
result=$(run_in_tmpdir '
    mkdir -p skills/bar
    echo "# Bar" > skills/bar/SKILL.md
    echo "notas" > skills/bar/extra.md
    python3 '"$AUDIT"' --quiet --threshold ERROR 2>&1; rc=$?
    [ $rc -eq 0 ] && echo OK || echo "rc=$rc"
')
[ "$result" = "OK" ] && _pass "--threshold ERROR ignora WARNING → exit 0" || _fail "--threshold ERROR → $result"

# Caso 7: --threshold ERROR + script en raíz → exit 1
result=$(run_in_tmpdir '
    mkdir -p skills/baz
    echo "# Baz" > skills/baz/SKILL.md
    echo "echo hola" > skills/baz/deploy.sh
    python3 '"$AUDIT"' --quiet --threshold ERROR 2>&1; rc=$?
    [ $rc -eq 1 ] && echo OK || echo "rc=$rc"
')
[ "$result" = "OK" ] && _pass "--threshold ERROR + .sh → exit 1" || _fail "--threshold ERROR + .sh → $result"

echo ""
echo "Resultado: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ] && exit 0 || exit 1
