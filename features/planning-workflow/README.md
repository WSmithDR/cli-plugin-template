# Feature: planning-workflow

## Qué hace

Estructura para planear una tarea multi-paso y después ejecutarla con checkpoints: el
plan se escribe como tasks concretas con criterios de aceptación, se auto-revisa antes de
ejecutar, y la ejecución para a pedir ayuda en vez de improvisar.

## Por qué

Saltar directo a codear en tareas multi-paso lleva a retrabajo y a perder el hilo. Un
plan con tasks atómicas y criterios verificables hace la ejecución predecible y permite
retomar tras una interrupción. Útil para features del propio catálogo y de tus plugins.

## Convenciones

### Escribir el plan

```markdown
# Plan: <objetivo>

## Task <N>: <título>
- **Descripción**: qué hacer (valores concretos, NO `[TODO]` ni placeholders)
- **Criterios de aceptación**: condiciones verificables de "listo"
- **Archivos**: rutas afectadas
```

- Tasks **bite-sized**: cada una se completa y verifica sola.
- **Sin placeholders**: todo valor concreto antes del handoff.
- **Self-review** antes de ejecutar: ¿alcanza el plan?, ¿algo ambiguo?

### Ejecutar el plan

1. Cargá el plan.
2. Ejecutá task por task; verificá los criterios de aceptación de cada una.
3. **Checkpoint**: si algo no calza o falta info, **pará y preguntá** — no improvises
   fuera del plan.

## Integración

1. Para una tarea multi-paso, escribí el plan antes de tocar código.
2. Guardalo (ej. `docs/plans/<slug>.md`) para poder retomarlo.
3. Ejecutá con checkpoints.

## Tests

Verificá que el plan no tiene placeholders y que cada task tiene criterios de aceptación
verificables antes de empezar a ejecutar.

## Changelog

- **1.0.0** — patrón de `superpowers` (writing-plans + executing-plans).
