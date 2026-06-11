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
| "¿qué me falta?", "revisá mi plugin", "está bien armado?" | `plugin-audit` |
| "integrá <feature>", "agregá versionado/hooks/health-check" | `plugin-feature` |
| "quiero X", "cómo hago que mis skills se disparen", "necesito Y" | `plugin-recommend` |
| "esto sirve para todos", "subí esto al catálogo" | `plugin-promote` |

Si la intención es ambigua, preguntá con una opción corta antes de enrutar.

## Contexto

El catálogo vive en `${CLAUDE_PLUGIN_ROOT}/features/`. Cada feature tiene `README.md`
(qué/por qué/cómo) + `files/` (esqueletos) + `meta.yml` (version, cli_compat, depends_on).
El índice es `${CLAUDE_PLUGIN_ROOT}/CATALOG.md`.
