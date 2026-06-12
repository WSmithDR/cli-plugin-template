# cli-plugin-template — guía para agentes

Este repo **no es** un scaffold de copia única. Es un **catálogo vivo de features**
reusables para plugins multi-CLI (Claude Code, OpenCode, Gemini CLI…).

Cualquier CLI que esté desarrollando un plugin usa este repo de dos formas:

## 1. Integrar un feature en el plugin que estás desarrollando

Cuando, desarrollando un plugin, detectás una mejora que conviene tener (versionado
automático, git hooks, compatibilidad multi-CLI, convenciones de docs…):

1. Leé **`CATALOG.md`** — índice de una línea por feature.
2. Abrí **`features/<nombre>/README.md`** — explica *qué es*, *por qué*, y *cómo
   integrarlo paso a paso* en un plugin.
3. Adaptá los archivos de `features/<nombre>/files/` al contexto del plugin
   (rutas, nombres, idioma). No los copies a ciegas: el README dice qué ajustar.
4. Revisá `features/<nombre>/meta.yml` → `version`. Si el plugin ya tiene ese
   feature pero con versión menor, integrá las diferencias.

## 2. Promover una mejora de vuelta al catálogo (loop inverso)

Si la mejora que hiciste en un plugin **sirve para todos los plugins**, no la dejes
solo en ese repo: promovéla acá. Seguí **`CONTRIBUTING.md`**.

Regla de decisión rápida:
- ¿Sirve para **un solo** plugin? → queda en ese plugin.
- ¿Sirve para **cualquier** plugin? → va a `features/` de este repo.

## Contrato

- Cada feature es **autocontenido**: README + files + meta.yml.
- Cada feature tiene su **propio `version`** en `meta.yml` (semver). Así un plugin
  sabe si está atrasado respecto al catálogo.
- Los READMEs están escritos **para que un agente los ejecute**, no solo para humanos:
  pasos concretos, comandos, y qué adaptar.
- Este archivo (`AGENTS.md`) y `CLAUDE.md` son el mismo contenido — `CLAUDE.md`
  existe para que Claude Code lo cargue automáticamente.

## Modo plugin

Este repo también es un plugin instalable (`.claude-plugin/plugin.json`), con manifiestos
para Gemini CLI, OpenCode, Codex, Cursor y Copilot (dogfooding de `multi-cli-compat`).
Instalado en otro proyecto, expone las skills `plugin-dev` (router), `plugin-audit`,
`plugin-feature`, `plugin-recommend`, `plugin-promote`, `plugin-register`,
`plugin-feedback-log`, `plugin-hotpatch`, `plugin-growth` y `cli-plugin-template-health` (diagnóstico), que leen el catálogo de
`features/` localmente. No hay comando slash: el router es la skill `plugin-dev`, que se
invoca al expresar la intención (evita chocar con el `/plugin` nativo de Claude Code). El
hook `SessionStart` sugiere una auditoría la primera vez en un proyecto de plugin. El
propio repo se excluye con el sentinel `.catalog-root`.

**Self-dogfooding (a propósito):** este repo habilita su propio plugin vía
`.claude/settings.json` (`enabledPlugins`), para que al desarrollar el catálogo las skills
estén activas y se apliquen sobre sí mismo. Ese archivo está committeado adrede — no lo
borres. Solo `.claude/settings.local.json` (overrides personales) queda fuera de git.
