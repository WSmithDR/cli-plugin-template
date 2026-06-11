# Feature: discipline-skills

## Qué hace

Patrón para skills que **hacen cumplir** una regla en vez de solo explicarla. Convierte
una norma ("siempre revisá antes de crear", "no toques datos sin aprobación") en un
proceso repetible que el agente no puede racionalizar para saltear.

## Por qué

"Saber" una regla no basta — el agente la saltea bajo presión con racionalizaciones
("esto es simple", "ya lo verifiqué a ojo"). Una discipline-skill anticipa esas excusas
y las bloquea explícitamente. Encaja con reglas que tus plugins ya tienen
(proposal-gate, vocabulary-guardian): este patrón les da una estructura probada.

## Estructura

```markdown
---
name: <regla-kebab>
description: Use when <situación donde la regla debe aplicarse>
---

# <Regla>

## Iron Law
> <LA REGLA EN MAYÚSCULAS, INNEGOCIABLE, SIN EXCEPCIONES>

## Por qué el orden importa
<Qué se rompe si saltás pasos — justifica la rigidez.>

## Proceso (obligatorio, en orden)
1. <paso>
2. <paso>

## Red Flags — STOP
| Pensamiento | Realidad |
|---|---|
| "Es un caso simple, no hace falta" | <por qué sí hace falta> |
| "Ya lo verifiqué informalmente" | <por qué no cuenta> |

## Checklist de verificación
- [ ] <condición que prueba que se cumplió la regla>
```

## Integración

1. Identificá una regla de tu plugin que se saltea bajo presión.
2. Escribí la skill con Iron Law + Red Flags + proceso ordenado.
3. En la tabla de Red Flags, listá las racionalizaciones **reales** que observaste
   (no hipotéticas). Cada vez que aparezca una nueva, agregala.

## Tests

Corré un escenario de presión: pedí la tarea sin recordar la regla y observá si el
agente la saltea. Si aparece una racionalización nueva, agregala a Red Flags y reintentá.

## Changelog

- **1.0.0** — patrón extraído de `superpowers` (TDD, verification-before-completion,
  systematic-debugging).
