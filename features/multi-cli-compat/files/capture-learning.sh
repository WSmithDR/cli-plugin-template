#!/bin/bash
# capture-learning.sh — captura un descubrimiento de compatibilidad multi-CLI.
#
# Cuando desarrollás un plugin downstream y aprendés algo sobre cómo otro CLI
# maneja una tool, hook o concepto de forma distinta, usá este script para
# formalizarlo. Entra al sistema de feedback del meta-plugin como `signal:
# discovery` y puede migrarse al template para futuros plugins.
#
# Uso:
#   bash capture-learning.sh <plugin> <slug> <<'EOF'
#   ## Descubrimiento
#   Gemini CLI no expone PostToolUse — solo PreToolUse.
#   ## CLI(s) involucrado(s)
#   gemini
#   ## Contexto
#   Al implementar el hook de logging en el plugin X, Gemini rechazó
#   PostToolUse porque no existe en su schema.
#   ## Recomendación
#   Usar tool.execute.after de OpenCode como alternativa, que sí existe en ambos.
#   ## ¿Aplica al template?
#   true
#   EOF
#
# Variables de entorno:
#   PLUGIN_ROOT   — raíz del meta-plugin (default: auto-detect)

set -euo pipefail

PLUGIN="${1:?Uso: capture-learning.sh <plugin> <slug>}"
SLUG="${2:?Uso: capture-learning.sh <plugin> <slug>}"
PLUGIN_ROOT="${PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
CPT="$PLUGIN_ROOT/bin/cpt"
TOOL_MAPPING="$PLUGIN_ROOT/features/multi-cli-compat/files/tool-mapping.md"

# Leer STDIN
BODY=$(cat)

# Validar que no exista ya
if "$CPT" feedback list --plugin "$PLUGIN" 2>/dev/null | grep -qx "$PLUGIN/$SLUG"; then
    echo "✗ Ya existe un feedback con slug '$SLUG' para '$PLUGIN'"
    echo "  Usá otro slug o revisalo con: $CPT feedback show $PLUGIN $SLUG"
    exit 1
fi

# Guardar como feedback con signal discovery
echo "$BODY" | "$CPT" feedback save "$PLUGIN" "$SLUG" -

echo ""
echo "✓ Descubrimiento guardado"
echo "  Plugin:  $PLUGIN"
echo "  Slug:    $SLUG"
echo "  Signal:  discovery"
echo "  Store:   \$DATA_DIR/$PLUGIN/feedbacks/feedback_$SLUG.md"
echo ""

# Si el descubrimiento aplica al template, sugerir contribución
if echo "$BODY" | grep -qi "aplica al template.*true"; then
    echo "→ Este descubrimiento aplica al template cli-plugin-template."

    # Extraer CLI(s) involucrado(s) para sugerir dónde documentar
    CLIS=$(echo "$BODY" | sed -n '/CLI.*involucrado/,/^$/p' | tail -n +2 | head -1)
    if [ -n "$CLIS" ]; then
        echo "  CLIs:    $CLIS"
    fi

    if [ -f "$TOOL_MAPPING" ]; then
        echo ""
        echo "  Migración sugerida: agregar entrada a tool-mapping.md:"
        echo "    $TOOL_MAPPING"
        echo "  Opción: contribuí al template via PR o copiando la entrada manualmente."
    fi
fi
