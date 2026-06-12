# Evals de `plugin-dev`

Aplican el feature [`skill-evals`](../../../features/skill-evals/README.md) al router del
catálogo. Miden dos cosas que importan en un router:

1. **Triggering** — que `plugin-dev` se active ante una intención de desarrollo de plugin
   (y que NO se active ante código de app: ver casos `negativo-*`).
2. **Routing** — que enrute a la sub-skill correcta (`expected_route`), o que **pregunte**
   cuando la intención es ambigua (caso `ambiguo-*`).

Los casos viven en [`evals.json`](evals.json). El campo `expected_route` toma:
`plugin-audit` · `plugin-feature` · `plugin-recommend` · `plugin-promote` · `ask` (debe
desambiguar) · `none` (no debe dispararse).

## Validar la estructura (determinista, en CI)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/bin/validate-evals.py"
```
Chequea el schema (ids únicos, expectations no vacías, config bien tipada). Corre en el
pre-commit y en CI. La parte semántica (¿el routing es correcto?) la hace el loop de abajo.

## Correr el loop comparativo

Seguí `skill-evals` (Mecanismos → Corridas comparativas):

1. Para cada caso, corré el prompt **con** `plugin-dev` cargada y **sin** ella (baseline),
   ≥3 veces (`config.runs_per_config`).
2. Graderá cada corrida contra las `expectations` (un agente grader ciego; que audite que
   las aserciones no sean tautológicas).
3. Calculá `pass_rate` medio + desvío por config. El delta (con − sin) muestra si el router
   aporta sobre dejar que el modelo decida solo.

## Loop de optimización del `description`

Si el triggering falla (no dispara, o dispara de más en los `negativo-*`):

1. Dividí los casos 60% train / 40% test (`config.train_test_split`).
2. Proponé mejoras al `description` de `plugin-dev` (más síntomas/keywords; ver
   `skill-authoring`/CSO) — sin nombrar tools, para no romper agnosticismo multi-CLI.
3. Re-evaluá y elegí el wording por **test score**, no train (evita sobreajustar).

## Agregar casos

Editá `evals.json`. Mantené representadas las 4 rutas + al menos un `ambiguo-*` y un
`negativo-*`; `validate-evals.py` falla si el schema se rompe.
