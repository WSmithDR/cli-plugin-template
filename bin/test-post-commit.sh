#!/bin/bash
# Tests del post-commit de auto-bump. Cada caso en un repo git temporal aislado,
# con bump-version.py y el post-commit reales instalados.
set -euo pipefail

# Si este test corre DENTRO de un hook de git (pre-commit/CI), git exporta GIT_DIR,
# GIT_INDEX_FILE, etc. apuntando al repo real. Sin limpiarlas, los `git` de los
# repos temporales operarían sobre el repo real. Las desarmamos.
unset GIT_DIR GIT_INDEX_FILE GIT_WORK_TREE GIT_PREFIX GIT_CONFIG_PARAMETERS 2>/dev/null || true

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUMP_SRC="$SCRIPT_DIR/bump-version.py"
HOOK_SRC="$SCRIPT_DIR/dev/git-hooks/post-commit"
PASS=0; FAIL=0
_pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
_fail() { echo "  FAIL: $1 ($2)"; FAIL=$((FAIL + 1)); }

ver() { python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['version'])" "$1"; }

setup_repo() {
    local dir; dir=$(mktemp -d)
    (
        cd "$dir"
        git init -q
        git config user.email t@t.t; git config user.name t
        git config commit.gpgsign false
        mkdir -p .claude-plugin bin
        cp "$BUMP_SRC" bin/bump-version.py
        printf '{\n  "name": "demo",\n  "version": "1.0.0"\n}\n' > .claude-plugin/plugin.json
        printf '{\n  "metadata": { "version": "1.0.0" },\n  "plugins": [ { "name": "demo", "version": "1.0.0" } ]\n}\n' > .claude-plugin/marketplace.json
        printf '{\n  "name": "demo",\n  "version": "1.0.0"\n}\n' > gemini-extension.json
        cp "$HOOK_SRC" .git/hooks/post-commit
        chmod +x .git/hooks/post-commit
        # commit inicial: incluye plugin.json -> guard de bump manual -> NO bumpea
        git add -A && git commit -q -m "chore: init"
    )
    echo "$dir"
}

echo ""
echo "=== post-commit (auto-bump) ==="

# Caso 1: commit feat: que NO toca plugin.json -> minor en todos, en el mismo commit
d=$(setup_repo)
(
    cd "$d"
    echo "x" > nota.md
    git add nota.md && git commit -q -m "feat: algo nuevo"
)
if [ "$(ver "$d/.claude-plugin/plugin.json")" = "1.1.0" ] \
   && [ "$(ver "$d/gemini-extension.json")" = "1.1.0" ]; then
    _pass "feat: -> minor 1.1.0 sincronizado"
else
    _fail "feat: -> minor" "plugin=$(ver "$d/.claude-plugin/plugin.json") gemini=$(ver "$d/gemini-extension.json")"
fi
# el bump quedó en el mismo commit (HEAD incluye plugin.json) y el árbol está limpio
if (cd "$d" && git show --name-only --format="" HEAD | grep -qx ".claude-plugin/plugin.json") \
   && [ -z "$(cd "$d" && git status --porcelain)" ]; then
    _pass "bump en el mismo commit + árbol limpio"
else
    _fail "bump en el mismo commit" "$(cd "$d" && git status --porcelain | tr '\n' ' ')"
fi
rm -rf "$d"

# Caso 2: commit docs: -> patch
d=$(setup_repo)
(cd "$d"; echo y > b.md; git add b.md && git commit -q -m "docs: algo")
[ "$(ver "$d/.claude-plugin/plugin.json")" = "1.0.1" ] && _pass "docs: -> patch 1.0.1" || _fail "docs: -> patch" "$(ver "$d/.claude-plugin/plugin.json")"
rm -rf "$d"

# Caso 3: commit feat!: -> major
d=$(setup_repo)
(cd "$d"; echo z > c.md; git add c.md && git commit -q -m "feat!: rompe algo")
[ "$(ver "$d/.claude-plugin/plugin.json")" = "2.0.0" ] && _pass "feat!: -> major 2.0.0" || _fail "feat!: -> major" "$(ver "$d/.claude-plugin/plugin.json")"
rm -rf "$d"

# Caso 4: bump manual (plugin.json en el commit) -> NO doble bump
d=$(setup_repo)
(
    cd "$d"
    python3 bin/bump-version.py minor >/dev/null   # 1.0.0 -> 1.1.0
    git add -A && git commit -q -m "feat: cambio con bump manual"
)
[ "$(ver "$d/.claude-plugin/plugin.json")" = "1.1.0" ] && _pass "bump manual -> sin doble bump (1.1.0)" || _fail "bump manual" "$(ver "$d/.claude-plugin/plugin.json")"
rm -rf "$d"

# Caso 5 (regresión worktree): el auto-bump debe funcionar dentro de un git worktree.
# En un worktree, <root>/.git es un ARCHIVO (no un dir), así que un sentinel en
# $REPO_ROOT/.git/... falla con `set -e` y el bump quedaba colgando sin amendar.
# El hook resuelve el git-dir real con `git rev-parse --git-dir`; este caso lo cubre.
d=$(setup_repo)
wt=$(mktemp -d)
(
    cd "$d"
    git worktree add -q "$wt" -b wt-branch
)
test -f "$wt/.git" && _pass "worktree: .git es un archivo (precondición del bug)" || _fail "worktree precondición" "no es archivo"
(
    cd "$wt"
    echo w > w.md
    git add w.md && git commit -q -m "feat: cambio en worktree"
)
if [ "$(ver "$wt/.claude-plugin/plugin.json")" = "1.1.0" ]; then
    _pass "worktree: auto-bump amendó (feat: -> 1.1.0)"
else
    _fail "worktree: auto-bump" "version=$(ver "$wt/.claude-plugin/plugin.json")"
fi
# y el árbol del worktree quedó limpio (bump en el mismo commit, no colgando)
if [ -z "$(cd "$wt" && git status --porcelain)" ] \
   && (cd "$wt" && git show --name-only --format="" HEAD | grep -qx ".claude-plugin/plugin.json"); then
    _pass "worktree: bump en el mismo commit + árbol limpio"
else
    _fail "worktree: árbol limpio" "$(cd "$wt" && git status --porcelain | tr '\n' ' ')"
fi
(cd "$d" && git worktree remove --force "$wt" 2>/dev/null || true)
rm -rf "$wt" "$d"

echo ""
echo "Resultado: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ] && exit 0 || exit 1
