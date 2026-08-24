#!/bin/bash
# Instala las skills del plugin en el directorio de cada CLI vía symlink.
# Para CLIs que no tienen marketplace propio y que consumen skills desde un
# directorio local. Correr una vez tras clonar.
# Codex no entra en este flujo: usa plugin nativo con `.codex-plugin/plugin.json`.
#
# Dos estilos:
#   per-skill : un symlink por skill dentro del dir del CLI
#   folder    : un symlink a toda la carpeta skills/
#
# Ajustá SKILLS_SRC y la tabla de plataformas a tu plugin.

set -euo pipefail

REPO="$(git rev-parse --show-toplevel)"
SKILLS_SRC="$REPO/skills"
PLUGIN="<plugin>"

# plataforma | dir destino | estilo
PLATFORMS="
gemini    $HOME/.agents/skills       per-skill
opencode  $HOME/.agents/skills       per-skill
cline     $HOME/.cline/skills        folder
"

link_per_skill() {
    local dst="$1"; mkdir -p "$dst"
    for skill in "$SKILLS_SRC"/*/; do
        ln -sfn "$skill" "$dst/$(basename "$skill")"
    done
}

link_folder() {
    local dst="$1"; mkdir -p "$dst"
    ln -sfn "$SKILLS_SRC" "$dst/$PLUGIN"
}

echo "$PLATFORMS" | while read -r name dst style; do
    [ -z "$name" ] && continue
    case "$style" in
        per-skill) link_per_skill "$dst" ;;
        folder)    link_folder "$dst" ;;
    esac
    echo "✓ $name → $dst ($style)"
done
