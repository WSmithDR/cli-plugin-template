---
name: plugin-audit
description: Use when you want to check the current plugin project against the cli-plugin-template catalog — which catalog features are missing or look outdated. Reports gaps with the feature that fills each one.
---

# plugin-audit — auditar el plugin vs catálogo

Compara el proyecto actual (un plugin) contra el catálogo y reporta gaps.

## Proceso

1. Confirmá que la cwd es un proyecto de plugin: existe `.claude-plugin/plugin.json`.
   Si no, decilo y salí.
2. Leé el índice del catálogo: `cat "${CLAUDE_PLUGIN_ROOT}/CATALOG.md"`.
3. Para cada categoría relevante, chequeá señales en el proyecto y marcá faltante/presente:
   - **versioning**: ¿hay un git hook que bumpea versión? (buscar `bin/dev/git-hooks/post-commit` o similar)
   - **git-hooks**: ¿hay `bin/dev/setup.sh` + tests?
   - **health-check**: ¿hay una skill `*-health`?
   - **claude-code-hooks / advanced-hooks**: ¿hay `hooks/hooks.json`?
   - **docs-conventions**: ¿el README tiene secciones de install/update/versionado?
   - **multi-cli-compat**: ¿hay manifiestos para otros CLIs (gemini-extension.json, .codex-plugin, opencode.json)?
   - **project-config / health-check / data-gateway / etc.**: señales análogas.
4. Reportá una tabla: Feature | Estado (✓ presente / ✗ falta) | Cómo integrarlo (`/plugin-feature <x>`).
5. No modifiques nada. Solo reportás.

## Salida sugerida

```
Auditoría de <plugin> vs catálogo:
  ✓ git-hooks
  ✗ versioning      → /plugin-feature versioning
  ✗ health-check    → /plugin-feature health-check
  ✓ docs-conventions
Sugerencia: empezá por versioning (alto valor, bajo costo).
```
