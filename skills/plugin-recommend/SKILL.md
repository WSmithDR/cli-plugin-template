---
name: plugin-recommend
description: Use when you describe a need for your plugin in plain language (e.g. "I want automatic versioning", "make my skills trigger reliably", "review changes for bugs") and want the catalog feature(s) that solve it.
---

# plugin-recommend — recomendar feature por necesidad

Matchea una necesidad en lenguaje natural contra el catálogo y sugiere el/los feature(s).

## Proceso

1. Leé `${CLAUDE_PLUGIN_ROOT}/CATALOG.md` (índice con descripciones por categoría).
2. Matcheá la necesidad del usuario contra las descripciones. Ejemplos:
   - "versionado automático" → `versioning`
   - "que mis skills se disparen" → `skill-authoring` (+ `skill-evals`)
   - "revisar cambios por bugs" → `dual-review`
   - "compatibilidad con otros CLIs" → `multi-cli-compat`
   - "memoria entre sesiones" → `session-memory`
3. Sugerí 1–3 features, citando una línea del README de cada uno (por qué resuelve la necesidad).
4. Ofrecé integrarlo: "corré `/plugin-feature <x>` o decime y lo integro".
5. Si no hay match claro, decilo y sugerí promover un feature nuevo (`plugin-promote`).
