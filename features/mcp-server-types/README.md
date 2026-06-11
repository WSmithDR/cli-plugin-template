# Feature: mcp-server-types

## Qué hace

Cubre **todos** los transportes para declarar un MCP server en `.mcp.json`, no solo `npx`:
stdio (npx, bun, docker, uvx, php), HTTP, HTTP con auth, y SSE — con el patrón correcto de
autenticación sin hardcodear secrets.

## Por qué

`mcp-npx-wrapper` cubre el caso `npx` (MCP en npm). Pero los MCP reales se declaran de
muchas formas: un binario local, un contenedor Docker, un endpoint HTTP remoto con token.
Elegir el transporte correcto y manejar la auth bien es lo que hace que el MCP arranque.

## Transportes

### stdio (local) — el CLI lanza un proceso

```json
{ "<srv>": { "command": "npx",   "args": ["-y", "@scope/paquete"] } }   // Node/npm
{ "<srv>": { "command": "bun",   "args": ["run", "${CLAUDE_PLUGIN_ROOT}/server.ts"] } }
{ "<srv>": { "command": "uvx",   "args": ["--from", "git+https://...", "server"] } }   // Python
{ "<srv>": { "command": "php",   "args": ["artisan", "mcp:serve"] } }
{ "<srv>": {
    "command": "docker",
    "args": ["run", "-i", "--rm", "-e", "API_TOKEN", "imagen/mcp"],
    "env": { "API_TOKEN": "${API_TOKEN}" }
} }
```

### HTTP / SSE (remoto) — el CLI se conecta a un endpoint

```json
{ "<srv>": { "type": "http", "url": "https://api.ejemplo.com/mcp" } }
{ "<srv>": { "type": "sse",  "url": "https://mcp.ejemplo.com/sse" } }
```

### HTTP con auth — token por variable de entorno

```json
{ "<srv>": {
    "type": "http",
    "url": "https://api.ejemplo.com/mcp",
    "headers": { "Authorization": "Bearer ${API_KEY}" }
} }
```

## Tabla de decisión

| Tenés… | Transporte |
|---|---|
| Paquete MCP en npm | `command: npx -y` |
| Binario/script local (Node/TS) | `command: bun` o `node` |
| MCP en Python (PyPI/git) | `command: uvx` |
| Imagen Docker | `command: docker run -i --rm` |
| Servicio remoto | `type: http` o `type: sse` |
| Remoto con API key | `type: http` + `headers.Authorization: Bearer ${VAR}` |

## Auth sin hardcodear secrets

- Referenciá el secret con `${VAR}`; nunca lo escribas literal en `.mcp.json`.
- Para Docker, pasá `-e VAR` y dejá que tome el valor del entorno.
- El usuario exporta la variable (o la pone en su config local gitignored), no en el repo.

## Integración

1. Elegí el transporte según la tabla.
2. Copiá el ejemplo de `files/mcp-examples.json` que aplique.
3. Para auth, usá `${VAR}` y documentá qué variable exportar.
4. Si el plugin debe correr en OpenCode también, replicá en `opencode.json` (ver `multi-cli-compat`).

## Tests

Levantá el MCP en el CLI y verificá que sus tools aparecen. Para HTTP+auth, probá con y sin
la variable exportada (debe fallar claro si falta).

## Changelog

- **1.0.0** — relevado de los 15 plugins MCP del marketplace oficial (npx, bun, docker,
  uvx, php, http, http+auth, sse).
