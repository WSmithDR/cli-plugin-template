#!/usr/bin/env bash
# Instala las skills de cli-plugin-template en el directorio de cada CLI vía symlink.
# Para CLIs que NO tienen marketplace propio (Gemini, Codex, OpenCode, Cline…).
# Correr una vez tras clonar. Es idempotente: re-correrlo sólo refresca los symlinks.
#
# Estilos:
#   per-skill : un symlink por skill dentro del dir del CLI
#   folder    : un symlink a toda la carpeta skills/
#
# No usa rutas absolutas hardcodeadas: la raíz del repo se resuelve relativa a este
# script (bin/ → repo root), con git rev-parse como verificación.

set -euo pipefail

# Raíz del repo, resuelta desde la ubicación de este script (no desde el cwd).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"

# Si git está disponible y estamos dentro del repo, preferí su raíz (maneja worktrees).
if command -v git >/dev/null 2>&1; then
    if GIT_ROOT="$(git -C "$REPO" rev-parse --show-toplevel 2>/dev/null)"; then
        REPO="$GIT_ROOT"
    fi
fi

SKILLS_SRC="$REPO/skills"
PLUGIN="cli-plugin-template"

if [ ! -d "$SKILLS_SRC" ]; then
    echo "✗ No se encontró $SKILLS_SRC" >&2
    exit 1
fi

# plataforma | dir destino | estilo
PLATFORMS="
gemini    $HOME/.gemini/skills     per-skill
codex     $HOME/.codex/skills      per-skill
opencode  $HOME/.config/opencode/skills  per-skill
cline     $HOME/.cline/skills      folder
"

link_per_skill() {
    local dst="$1"
    mkdir -p "$dst"
    for skill in "$SKILLS_SRC"/*/; do
        [ -d "$skill" ] || continue
        ln -sfn "$skill" "$dst/$(basename "$skill")"
    done
}

link_folder() {
    local dst="$1"
    mkdir -p "$dst"
    ln -sfn "$SKILLS_SRC" "$dst/$PLUGIN"
}

echo "$PLATFORMS" | while read -r name dst style; do
    [ -z "$name" ] && continue
    case "$style" in
        per-skill) link_per_skill "$dst" ;;
        folder)    link_folder "$dst" ;;
        *) echo "✗ estilo desconocido para $name: $style" >&2; continue ;;
    esac
    echo "✓ $name → $dst ($style)"
done
