#!/bin/bash
# capture-learning.sh — captura descubrimientos de compatibilidad multi-CLI.
#
# Entry point para el meta-plugin. Delega en features/multi-cli-compat/files/capture-learning.sh
# apuntando al plugin correcto y seteando PLUGIN_ROOT.
#
# Uso: bash bin/capture-learning.sh <plugin> <slug>  (lee cuerpo de STDIN)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

exec bash "$PLUGIN_ROOT/features/multi-cli-compat/files/capture-learning.sh" "$@"
