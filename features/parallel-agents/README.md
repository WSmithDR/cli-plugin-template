# Feature: parallel-agents

## Qué hace

Patrón para abanicar trabajo **independiente** a varios subagentes que corren en
paralelo, y después integrar sus resultados — sin inundar el contexto principal con los
detalles intermedios.

## Por qué

Cuando una tarea se descompone en partes que no dependen entre sí (auditar 3 áreas de un
codebase, analizar varios diffs), correrlas en serie es lento y cada lectura llena el
contexto. Despacharlas en paralelo es más rápido y el orquestador solo retiene las
conclusiones. Aplica directo a casos como `todo-audit`.

## El patrón

1. **Identificar dominios independientes** — partes sin estado compartido ni orden entre sí.
2. **Escribir una task enfocada por dominio** — cada subagente recibe contexto, objetivo
   y constraints explícitos; devuelve solo la conclusión, no volcados de archivos.
3. **Despachar en paralelo** — todas las invocaciones en un solo mensaje (un tool-use por
   agente) para que corran concurrentes.
4. **Integrar** — el orquestador combina los resultados.

## Cuándo NO usar

- Las partes comparten estado o se modifican entre sí.
- El resultado de una determina la entrada de otra → usá `agent-pipeline` (secuencial).
- Fallos relacionados que conviene diagnosticar juntos.

## Integración

1. Antes de despachar, verificá que los dominios son realmente independientes.
2. En cada prompt de subagente incluí: contexto necesario, objetivo, qué devolver
   (formato), y qué NO hacer.
3. Pedí conclusiones, no transcripciones — el subagente filtra; vos te quedás con el resultado.

## Tests

Despachá 2+ subagentes sobre partes independientes y verificá que el contexto principal
recibe conclusiones acotadas (no el contenido completo que leyó cada uno).

## Changelog

- **1.0.0** — patrón de `superpowers` (dispatching-parallel-agents).
