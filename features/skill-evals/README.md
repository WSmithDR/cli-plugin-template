# Feature: skill-evals

## Qué hace

Testea y optimiza skills con **evals**: casos de evaluación con expectativas verificables,
corridas comparativas (con skill vs sin skill) con análisis de varianza, y un loop que
**optimiza el `description`** de la skill para mejorar cuándo se dispara.

## Por qué

Sin evals, "la skill funciona" es una opinión. Y el problema más común —que la skill no se
dispare— se ataca optimizando su `description` con método, no a ojo. Esto le da a
`skill-authoring` un bucle de mejora medible.

## Mecanismos

### Casos de eval

```json
{
  "evals": [
    { "id": "caso-1", "prompt": "<lo que el usuario pediría>",
      "files": ["fixtures/..."],
      "expectations": ["<aserción textual verificable sobre el resultado>"] }
  ]
}
```

### Corridas comparativas + varianza

Corré cada caso **con la skill** y **sin la skill** (baseline), varias veces (≥3), y
calculá media/desvío de `pass_rate`, tiempo y tokens. El delta (con − sin) muestra si la
skill realmente aporta.

### Loop de optimización del `description`

1. Dividí los casos: 60% train / 40% test.
2. Proponé mejoras al `description` (más síntomas, keywords; ver `skill-authoring`/CSO).
3. Re-evaluá.
4. Elegí el mejor por **test score**, no train → evita sobreajustar el wording a los casos
   vistos.

### Agentes de soporte

- **grader**: evalúa las expectations contra el transcript; audita que las aserciones no
  sean tautológicas.
- **comparator**: compara outputs baseline vs skill a ciegas (sin saber cuál es cuál).
- **analyzer**: post-mortem — fortalezas/debilidades y sugerencias categorizadas.

## Integración

1. Escribí `evals/evals.json` con casos que representen cómo se usaría la skill.
2. Corré con/sin skill (≥3 veces) y mirá el delta + varianza.
3. Si el triggering falla, corré el loop de optimización del `description`.

## Tests

Una skill con buen `description` debe ganarle al baseline en los casos; si no, el eval lo
muestra.

## Changelog

- **1.0.0** — patrón de `skill-creator` (evals, variance, description optimization loop).
