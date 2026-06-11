# Feature: session-memory

## Qué hace

Da memoria que **sobrevive entre sesiones**: un MCP server como almacén durable, más hooks
de sesión que inyectan el contexto relevante al arrancar, lo recuperan tras una compactación,
y empujan al agente a guardar lo importante.

## Por qué

Por defecto cada sesión arranca en cero y una compactación pierde contexto. Para estado que
debe persistir (progreso de un proceso largo, decisiones, el avance de un curriculum como en
ankify), necesitás un almacén externo + inyección automática, no depender de que el usuario
lo recuerde.

## Arquitectura

1. **MCP como almacén durable** — no es una skill, es un servicio en background con tools
   tipo `mem_save` / `mem_search` (ver `mcp-server-types` para declararlo).
2. **Hooks de sesión** que orquestan la memoria:
   - `SessionStart (startup)`: arranca el server, crea la sesión, importa el contexto del
     proyecto y lo inyecta como `additionalContext`.
   - `SessionStart (compact)`: re-inyecta contexto tras la compactación.
   - `UserPromptSubmit`: en el primer mensaje carga las tools diferidas; en los siguientes,
     nudge a guardar si pasó mucho sin `mem_save`.
   - `Stop`/`SubagentStop` (async): cierre/limpieza de la sesión.
3. **Lock distribuido** para el import: si dos sesiones arrancan a la vez, un lock con
   detección de stale evita la doble importación y los bloqueos infinitos.

## Inyección de contexto

El script de `SessionStart` escribe el contexto a stdout como `additionalContext` del JSON
del hook → Claude lo recibe sin que el usuario haga nada.

## Integración

1. Declará el MCP de memoria en `.mcp.json`.
2. Agregá los hooks de sesión (`SessionStart` startup+compact, `UserPromptSubmit`, `Stop`).
3. Implementá el lock con detección de stale en el script de import.
4. Definí un protocolo de "cuándo guardar" (como skill, ver `discipline-skills`) para que el
   guardado sea proactivo sin ser molesto.

## Tests

Guardá algo en una sesión, cerrala, abrí otra y verificá que el contexto se re-inyecta.
Simulá dos arranques concurrentes y verificá que el lock evita la doble importación.

## Changelog

- **1.0.0** — patrón de `engram` (.mcp.json + hooks de sesión + lock distribuido).
