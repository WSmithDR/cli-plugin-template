# cli-plugin-template — contexto para Gemini CLI

Este repo es el meta-plugin **cli-plugin-template**: un catálogo vivo de features
reusables para plugins multi-CLI. Cuando guíes el desarrollo de un plugin, **no
improvises**: usá las skills del catálogo en `skills/`.

El entry point es el router `plugin-dev`, que enruta a `plugin-audit`,
`plugin-feature`, `plugin-recommend` y `plugin-promote` según la intención. Activá
el skill (`activate_skill`) en vez de responder a mano.

Las skills están escritas con los nombres de tools de Claude Code (`Skill`, `Task`,
`Read`, `Edit`…). En Gemini CLI esos nombres cambian: consultá la tabla de mapeo
incluida abajo.

Los `@`-includes siguientes se cargan automáticamente en cada sesión porque
`gemini-extension.json` declara `"contextFileName": "GEMINI.md"`:

@./skills/plugin-dev/SKILL.md
@./skills/plugin-dev/references/tool-mapping.md
