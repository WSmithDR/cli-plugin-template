# Feature: mcp-npx-wrapper

## Qué hace

Empaqueta un MCP server externo publicado en npm como un plugin de Claude Code, con la
estructura mínima: un `.mcp.json` que lo lanza vía `npx` y un `plugin.json` chico. Sin
código local.

## Por qué

Si el MCP ya existe en npm (mantenido por un tercero o por vos en otro repo), no hace
falta replicar su lógica. Un wrapper fino lo expone como plugin con fricción casi nula y
deja el versionado del MCP en npm.

> Distinto de `multi-cli-compat`, que es para declarar el MCP **propio** del plugin junto
> a sus skills. Este es para envolver un MCP **externo** sin código propio.

## Integración

1. `.mcp.json`:
   ```json
   {
     "<nombre>": {
       "command": "npx",
       "args": ["-y", "@scope/paquete-mcp"]
     }
   }
   ```
   - `npx -y` instala sin preguntar.
   - Para MCP con auth, pasá la API key por `env` o dejá que el MCP la tome de su propia
     config upstream.
2. `.claude-plugin/plugin.json` mínimo:
   ```json
   {
     "name": "<nombre>",
     "description": "<qué hace el MCP>",
     "author": { "name": "<autor>" }
   }
   ```
3. Nada más — sin `skills/`, `hooks/` ni `bin/`.

## Tests

Instalá el plugin y verificá que las tools del MCP aparecen y responden.

## Changelog

- **1.0.0** — patrón de `context7` (wrapper de `@upstash/context7-mcp` vía npx).
