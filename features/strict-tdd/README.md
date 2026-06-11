# Feature: strict-tdd

## Qué hace

Hace cumplir TDD con **evidencia verificable**, no solo con la afirmación de que se hizo:
una tabla de ciclo por unidad de trabajo y una auditoría que detecta tests falsos
(tautologías, ghost loops, mocks sin verificar).

## Por qué

"Hice TDD" reportado por el agente no garantiza nada — puede haber escrito el test después,
o tests que pasan siempre. La evidencia (el test existe, pasa ahora, cubre los escenarios
del spec) y la auditoría de assertions convierten TDD en algo chequeable.

## Es una discipline-skill

Usa la estructura de `discipline-skills` (Iron Law + Red Flags + proceso). La Iron Law:
> NINGÚN código de producción sin un test que falle primero.

## Tabla de evidencia (por unidad)

| RED | GREEN | TRIANGULATE | SAFETY NET | REFACTOR |
|---|---|---|---|---|
| el test existe y se escribió antes | pasa al correr el runner | ≥1 caso por escenario del spec | si el archivo se modificó, los tests previos siguen verdes | calidad (subjetivo) |

Verificación: cada fila se chequea contra la ejecución real del runner, no contra el reporte.

## Auditoría de assertions (patrones prohibidos)

- Tautologías: `expect(true).toBe(true)`.
- Condiciones siempre verdaderas / ghost loops (loops que nunca iteran).
- Chequeos solo de tipo, o "smoke tests" sin aserción real.
- Mocks sin verificación de llamada.
- Aserciones sobre detalles de implementación (ej. CSS interno) en vez de comportamiento.

## Integración

1. Escribí la skill TDD con la Iron Law y la tabla de evidencia (ver `files/tdd-evidence.md`).
2. En el paso de verificación, cruzá la tabla contra la corrida real del test runner.
3. Aplicá la auditoría de assertions antes de aceptar los tests.

## Tests

Inyectá un test tautológico y verificá que la auditoría lo rechaza; reportá un GREEN sin
correr el runner y verificá que el cruce lo detecta.

## Changelog

- **1.0.0** — patrón de `gentle-pi` (strict-tdd.md + strict-tdd-verify.md).
