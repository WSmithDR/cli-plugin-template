#!/bin/bash
# Tests de bin/audit-catalog-gaps.py. Cada caso en un tmpdir aislado.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUDIT="$SCRIPT_DIR/audit-catalog-gaps.py"
PASS=0; FAIL=0
_pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
_fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

run_in_tmpdir() {
    local dir; dir=$(mktemp -d)
    (cd "$dir" && eval "$1"); local rc=$?
    rm -rf "$dir"; return $rc
}

echo ""
echo "=== audit-catalog-gaps.py ==="

# Caso 1: dir sin .claude-plugin/ → exit 2
result=$(run_in_tmpdir '
    out=$(python3 '"$AUDIT"' . 2>&1); rc=$?
    [ $rc -eq 2 ] && echo "$out" | grep -qi "plugin.json" && echo OK || echo "rc=$rc out=$out"
')
[ "$result" = "OK" ] && _pass "sin .claude-plugin/ → exit 2" || _fail "sin .claude-plugin/ → $result"

# Caso 2: plugin fixture mínimo → detecciones correctas.
# Construye un plugin con: hooks/hooks.json (claude-code-hooks ✓),
# config/vocabulary.json (externalized-config ✓ + vocabulary-guardian ✓),
# bin/foo.py (bundled-scripts ✓), gemini-extension.json (multi-cli-compat ✓).
# NO tiene: post-commit (versioning ✗), setup.sh+test (git-hooks ✗),
# skill *health* (health-check ✗), README con secciones (docs-conventions ✗),
# cli.py/gateway.py (data-gateway ✗), skill *propos* (proposal-gate ✗).
result=$(run_in_tmpdir '
    mkdir -p .claude-plugin hooks config bin
    echo "{\"name\":\"fix\"}" > .claude-plugin/plugin.json
    echo "{}" > hooks/hooks.json
    echo "{}" > config/vocabulary.json
    echo "print(1)" > bin/foo.py
    echo "{}" > gemini-extension.json
    out=$(python3 '"$AUDIT"' . --json 2>&1); rc=$?
    [ $rc -eq 0 ] || { echo "rc=$rc out=$out"; exit 0; }
    echo "$out"
')
get_status() { echo "$result" | python3 -c "import sys,json;d=json.load(sys.stdin);print(next(x['status'] for x in d if x['feature']=='$1'))" 2>/dev/null; }

[ "$(get_status claude-code-hooks)" = "present" ] && _pass "hooks/hooks.json → claude-code-hooks present" || _fail "claude-code-hooks (got: $(get_status claude-code-hooks))"
[ "$(get_status externalized-config)" = "present" ] && _pass "config/*.json → externalized-config present" || _fail "externalized-config (got: $(get_status externalized-config))"
[ "$(get_status vocabulary-guardian)" = "present" ] && _pass "vocabulary.json → vocabulary-guardian present" || _fail "vocabulary-guardian (got: $(get_status vocabulary-guardian))"
[ "$(get_status bundled-scripts)" = "present" ] && _pass "bin/*.py → bundled-scripts present" || _fail "bundled-scripts (got: $(get_status bundled-scripts))"
[ "$(get_status multi-cli-compat)" = "present" ] && _pass "gemini-extension.json → multi-cli-compat present" || _fail "multi-cli-compat (got: $(get_status multi-cli-compat))"
[ "$(get_status versioning)" = "missing" ] && _pass "sin post-commit → versioning missing" || _fail "versioning (got: $(get_status versioning))"
[ "$(get_status git-hooks)" = "missing" ] && _pass "sin setup+test → git-hooks missing" || _fail "git-hooks (got: $(get_status git-hooks))"
[ "$(get_status health-check)" = "missing" ] && _pass "sin skill health → health-check missing" || _fail "health-check (got: $(get_status health-check))"
[ "$(get_status data-gateway)" = "missing" ] && _pass "sin cli/gateway → data-gateway missing" || _fail "data-gateway (got: $(get_status data-gateway))"
[ "$(get_status entry-point-router)" = "na" ] && _pass "entry-point-router → n/d (requiere juicio)" || _fail "entry-point-router (got: $(get_status entry-point-router))"

# Caso 3: señales positivas de versioning + git-hooks + health-check + docs + proposal.
result=$(run_in_tmpdir '
    mkdir -p .claude-plugin bin/dev/git-hooks skills/foo-health skills/bar-proposal
    echo "{\"name\":\"fix\"}" > .claude-plugin/plugin.json
    printf "#!/bin/bash\n# bump version\n" > bin/dev/git-hooks/post-commit
    printf "#!/bin/bash\nln -s .git/hooks/pre-commit\n" > bin/dev/setup.sh
    printf "#!/bin/bash\necho test\n" > bin/test-hooks.sh
    printf "# Plugin\n## Instalación\n## Actualización\n## Versionado\n" > README.md
    echo "---" > skills/foo-health/SKILL.md
    echo "---" > skills/bar-proposal/SKILL.md
    out=$(python3 '"$AUDIT"' . --json 2>&1); rc=$?
    [ $rc -eq 0 ] || { echo "rc=$rc out=$out"; exit 0; }
    echo "$out"
')
[ "$(get_status versioning)" = "present" ] && _pass "post-commit+version → versioning present" || _fail "versioning2 (got: $(get_status versioning))"
[ "$(get_status git-hooks)" = "present" ] && _pass "setup.sh+test*.sh → git-hooks present" || _fail "git-hooks2 (got: $(get_status git-hooks))"
[ "$(get_status health-check)" = "present" ] && _pass "skills/*health* → health-check present" || _fail "health-check2 (got: $(get_status health-check))"
[ "$(get_status docs-conventions)" = "present" ] && _pass "README install/update/version → docs-conventions present" || _fail "docs-conventions2 (got: $(get_status docs-conventions))"
[ "$(get_status proposal-gate)" = "present" ] && _pass "skills/*propos* → proposal-gate present" || _fail "proposal-gate2 (got: $(get_status proposal-gate))"

# Caso 4: default cwd (sin argumento RUTA) sobre dir sin plugin → exit 2
result=$(run_in_tmpdir '
    out=$(python3 '"$AUDIT"' 2>&1); rc=$?
    [ $rc -eq 2 ] && echo OK || echo "rc=$rc out=$out"
')
[ "$result" = "OK" ] && _pass "default cwd sin plugin → exit 2" || _fail "default cwd → $result"

echo ""
echo "Resultado: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ] && exit 0 || exit 1
