---
name: plugin-dev
description: Use when developing a Claude Code or multi-CLI plugin and you want guidance from the cli-plugin-template catalog — to audit the plugin, integrate a feature, find which feature solves a need, or promote an improvement back. Entry point; routes to the right capability.
---

# plugin-dev — router del catálogo

Punto de entrada único para las pautas del catálogo. Elegí la capacidad según la intención
del usuario; NO invoques las sub-skills directamente como respuesta — pasá por acá.

## Routing

| Intención del usuario | Skill |
|---|---|
| chequear el plugin contra el catálogo: "¿qué me falta?", "revisá mi plugin", "está bien armado?" | `plugin-audit` |
| nombra uno o más **features concretos** del catálogo (versionado, hooks, health-check…), con cualquier verbo ("integrá", "agregá", "quiero meter") | `plugin-feature` |
| describe una **necesidad o síntoma sin nombrar un feature** ("que mis skills se disparen mejor", "no perder datos entre sesiones") | `plugin-recommend` |
| menciona el **catálogo** o "para todos los plugins": "esto sirve para todos", "subí/promové esto al catálogo" | `plugin-promote` |

**Desempate:** el verbo no decide la ruta —decide *qué* se nombra. Si el mensaje nombra un
feature concreto del catálogo → `plugin-feature`, aunque diga "quiero/necesito". Si solo
describe una necesidad sin nombrar feature → `plugin-recommend`. Si menciona "al catálogo /
para todos los plugins" → `plugin-promote`, aunque diga "quiero".

Si la intención es ambigua (p.ej. "mejorá mi plugin"), preguntá con una opción corta antes
de enrutar. Si no es desarrollo de un plugin (código de app, bugs, tests de un módulo), no
enrutes: `plugin-dev` no aplica.

## Contexto

El catálogo vive en `${CLAUDE_PLUGIN_ROOT}/features/`. Cada feature tiene `README.md`
(qué/por qué/cómo) + `files/` (esqueletos) + `meta.yml` (version, cli_compat, depends_on).
El índice es `${CLAUDE_PLUGIN_ROOT}/CATALOG.md`.
