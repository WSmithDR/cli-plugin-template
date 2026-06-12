#!/bin/bash
# Setup de desarrollo del catálogo cli-plugin-template.
# Uso: bash bin/dev/setup.sh   (ejecutar una vez después de clonar)
#
# Instala los git hooks por symlink, así viven versionados en bin/dev/git-hooks/
# y .git/hooks/ solo apunta a ellos (editor-agnóstico, ver feature `git-hooks`).
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"

install_hook() {
    local name="$1"
    local src="$REPO_ROOT/bin/dev/git-hooks/$name"
    local dst="$REPO_ROOT/.git/hooks/$name"
    [ -f "$src" ] || { echo "· $name: no existe, salteado"; return; }
    chmod +x "$src"
    if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then
        echo "✓ $name ya instalado"
    else
        ln -sf "$src" "$dst"
        echo "✓ $name instalado → .git/hooks/$name"
    fi
}

echo "cli-plugin-template — setup de desarrollo"
echo ""
install_hook "pre-commit"
echo ""
echo "Listo. El pre-commit valida el catálogo, corre los tests y audita portabilidad."
echo "  Auditar a mano:  python3 features/portability-audit/files/audit-portability.py ."
