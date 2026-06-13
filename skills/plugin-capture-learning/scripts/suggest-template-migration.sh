#!/usr/bin/env bash
set -euo pipefail

TOOL_MAPPING="$CLAUDE_PLUGIN_ROOT/features/multi-cli-compat/files/tool-mapping.md"
if [ -f "$TOOL_MAPPING" ]; then
    echo ""
    echo "→ Este descubrimiento aplica al template cli-plugin-template."
    echo "  Migración sugerida: agregar entrada a:"
    echo "    $TOOL_MAPPING"
    echo "  O crear un PR contra cli-plugin-template para que futuros plugins lo hereden."
fi
