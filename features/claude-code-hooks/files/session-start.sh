#!/bin/bash
# SessionStart:
# 1. Instala el git pre-commit hook si aplica (gotcha CLAUDE_PLUGIN_ROOT)
# 2. Detecta config faltante y la solicita (exit 2 = bloqueante)

set -euo pipefail

# Ajustar al datadir del plugin
DATADIR=".midata"

[ ! -d "$DATADIR" ] && exit 0

# Auto-instalar git hook — solo si el plugin se instaló via `claude plugin install`
if [ -d ".git" ] && [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    HOOK_DST=".git/hooks/pre-commit"
    HOOK_SRC="${CLAUDE_PLUGIN_ROOT}/bin/hooks/pre-commit.sh"
    if [ ! -L "$HOOK_DST" ] || [ "$(readlink "$HOOK_DST")" != "$HOOK_SRC" ]; then
        mkdir -p .git/hooks
        ln -sf "$HOOK_SRC" "$HOOK_DST"
        chmod +x "$HOOK_SRC"
        echo "SETUP: git pre-commit hook instalado"   # exit 0 → informativo
    fi
fi

# Detectar config faltante → bloqueante
[ -f "$DATADIR/config.json" ] && exit 0

echo "CONFIG-MISSING: $DATADIR existe pero falta config.json.
Invocar Skill('<plugin>-config') antes de cualquier operación." >&2
exit 2
