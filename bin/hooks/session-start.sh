#!/bin/bash
# SessionStart: en un proyecto de plugin (no el catálogo), sugiere una auditoría
# del catálogo — una sola vez por proyecto. Informativo (exit 0), no bloquea.
set -euo pipefail

# Guard de auto-referencia: el catálogo lleva .catalog-root
[ -f ".catalog-root" ] && exit 0

# Solo en proyectos de plugin
[ -d ".claude-plugin" ] || exit 0

# Marcador "ya avisado" en .git (no se commitea); fallback si no hay git
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null || echo "")
if [ -n "$GIT_DIR" ]; then
    MARKER="$GIT_DIR/cli-plugin-template.seen"
else
    MARKER=".claude-plugin/.cli-template-seen"
fi
[ -f "$MARKER" ] && exit 0
touch "$MARKER"

MSG="CLI-PLUGIN-TEMPLATE: Esto parece un proyecto de plugin.
El catálogo cli-plugin-template está instalado — corré /plugin-audit para ver qué features te faltan, o /plugin para el menú de capacidades."

# Si el plugin no está en el registry de evolución, ofrecer el alta. El registry
# es el allowlist: el meta-plugin solo administra/parchea plugins dados de alta.
CPT="$(cd "$(dirname "$0")/.." && pwd)/cpt"
NAME=$(python3 -c "import json;print(json.load(open('.claude-plugin/plugin.json')).get('name',''))" 2>/dev/null || echo "")
if [ -n "$NAME" ] && [ -x "$CPT" -o -f "$CPT" ]; then
    REGISTERED=$(python3 "$CPT" registry resolve "$NAME" 2>/dev/null || true)
    if [ -z "$REGISTERED" ]; then
        MSG="$MSG
Este plugin no está en el registry de evolución — decí 'registrá este plugin' (skill plugin-register) para que cli-plugin-template administre su evolución (captura de fricción y parcheo asistido)."
    fi
fi

echo "$MSG"
exit 0
