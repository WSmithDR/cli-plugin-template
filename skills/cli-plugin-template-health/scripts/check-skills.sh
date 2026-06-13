#!/usr/bin/env bash
set -euo pipefail
for s in plugin-dev plugin-audit plugin-feature plugin-recommend plugin-promote plugin-register plugin-feedback-log plugin-hotpatch plugin-growth plugin-capture-learning cli-plugin-template-health; do
  [ -f "${CLAUDE_PLUGIN_ROOT}/skills/$s/SKILL.md" ] && echo "✓ $s" || echo "✗ falta skill: $s"
done
