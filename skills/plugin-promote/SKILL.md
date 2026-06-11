---
name: plugin-promote
description: Use when an improvement born in the current plugin is reusable for any plugin and should go back to the cli-plugin-template catalog. Creates features/<name>/ in the catalog working tree following CONTRIBUTING.md — does NOT commit.
---

# plugin-promote — promover una mejora al catálogo

Sube una mejora reusable al catálogo. **Deja todo en working tree del catálogo, sin commitear.**

## Proceso

1. Confirmá que la mejora es reusable para CUALQUIER plugin (no lógica de dominio del
   plugin actual). Si es específica, no va al catálogo.
2. Leé `${CLAUDE_PLUGIN_ROOT}/CONTRIBUTING.md` y seguí su estructura.
3. Creá en el catálogo `${CLAUDE_PLUGIN_ROOT}/features/<nombre>/`:
   - `README.md` con: Qué hace · Por qué · Integración · Tests · Changelog.
   - `files/` con los esqueletos reusables (si aplica).
   - `meta.yml` con `name`, `version: 1.0.0`, `cli_compat`, `depends_on`, `description`.
4. Agregá la fila en `${CLAUDE_PLUGIN_ROOT}/CATALOG.md`.
5. Corré la validación: `python3 "${CLAUDE_PLUGIN_ROOT}/bin/validate-catalog.py"`.
6. **No commitees.** Avisá al usuario que revise el working tree del catálogo y commitee él.

## Reglas

- El `name` de `meta.yml` debe coincidir con el nombre de la carpeta (lo valida el CI).
- Cada feature listado en CATALOG.md debe existir, y viceversa (lo valida el CI).
