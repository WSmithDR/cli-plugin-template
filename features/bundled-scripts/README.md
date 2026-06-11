# Feature: bundled-scripts

## Qué hace

Mueve el trabajo determinista del plugin a scripts incluidos (`bin/` o `scripts/`), y le
deja al LLM solo lo que requiere juicio.

## Por qué

El LLM es poco fiable y caro para tareas mecánicas: enumerar archivos, contar líneas,
parsear estructura, aplicar reglas fijas. Un script lo hace igual cada vez, rápido y sin
gastar contexto. Tus plugins ya lo hacen en parte (ankify con `bin/lib/`); este feature
lo formaliza como principio.

## Regla

> Si la tarea tiene una respuesta determinista (mismo input → mismo output), es un
> script. Si requiere juicio (resumir, clasificar, decidir), es el LLM.

| Determinista (script) | Juicio (LLM) |
|---|---|
| listar/contar/filtrar archivos | resumir qué hace un módulo |
| extraer imports/estructura | inferir relaciones semánticas |
| validar contra un schema | decidir prioridad/categoría |
| aplicar una regla fija | manejar un caso ambiguo |

## Integración

1. Identificá los pasos deterministas de tu flujo.
2. Implementálos como scripts en `bin/` o `scripts/` (Python/Node), invocables desde las
   skills. Centralizá lógica compartida en una lib (ver `data-gateway`).
3. En las skills, llamá al script y pasale el resultado al LLM para la parte de juicio
   (encaja con la fase 2 de `agent-pipeline`).

## Tests

Corré el script con un input fijo dos veces → salida idéntica. Verificá que ninguna skill
le pide al LLM contar/enumerar lo que el script ya resuelve.

## Changelog

- **1.0.0** — patrón de `understand-anything` (scripts bundled) y `ankify` (bin/lib).
