#!/usr/bin/env bash
set -euo pipefail
[ -f "${CLAUDE_PLUGIN_ROOT}/CATALOG.md" ] \
  && echo "✓ CATALOG.md presente" || echo "✗ falta CATALOG.md"
[ -d "${CLAUDE_PLUGIN_ROOT}/features" ] \
  && echo "✓ features/ presente" || echo "✗ falta features/ (catálogo vacío)"
python3 "${CLAUDE_PLUGIN_ROOT}/bin/validate-catalog.py" \
  && echo "✓ validate-catalog OK" || echo "✗ validate-catalog falló (ver salida arriba)"
