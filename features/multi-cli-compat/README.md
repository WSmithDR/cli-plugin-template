# Feature: multi-cli-compat

## Qué hace

Hace que el mismo plugin funcione en varios CLIs —Claude Code, OpenCode, Gemini CLI,
LSP— declarando el manifiesto que cada uno espera y compartiendo una sola definición
de servidores MCP.

## Por qué

Un plugin atado a un solo CLI se queda fuera del resto del ecosistema. Cada CLI lee su
propio archivo de config, pero la lógica del plugin (skills, scripts) puede ser
agnóstica si los manifiestos apuntan a los mismos recursos.

## Mapa de manifiestos

| CLI | Archivo | Qué declara |
|---|---|---|
| Claude Code | `.claude-plugin/plugin.json` | metadata + `"skills": "./skills/"` (auto-discovery) |
| Claude Code | `.mcp.json` | `mcpServers` (command + args por servidor) |
| OpenCode | `opencode.json` | `mcp` (type local/remote + command) |
| LSP | `.lsp.json` | config LSP (puede ser mínima `{"lsp":{}}`) |
| Todos (agentes) | `AGENTS.md` | instrucciones que cualquier CLI lee |
| Claude Code | `CLAUDE.md` | symlink o copia de `AGENTS.md` |
| Gemini CLI | `GEMINI.md` | symlink o copia de `AGENTS.md` |

## Integración

1. **Manifiesto Claude Code** — `.claude-plugin/plugin.json`:
   ```json
   {
     "name": "<plugin>", "version": "1.0.0",
     "description": "...", "license": "MIT",
     "skills": "./skills/"
   }
   ```
   El `"skills": "./skills/"` auto-descubre toda carpeta con `SKILL.md`.

2. **MCP compartido** — definí cada servidor una vez. `.mcp.json` (Claude):
   ```json
   { "mcpServers": {
       "<srv>": { "command": "bash", "args": ["${CLAUDE_PLUGIN_ROOT}/bin/mcp/start-<srv>.sh"] }
   } }
   ```
   `opencode.json` (OpenCode) apunta al **mismo** script de arranque:
   ```json
   { "mcp": {
       "<srv>": { "type": "local", "command": ["bash", "bin/mcp/start-<srv>.sh"] }
   } }
   ```
   Mantené la lógica de arranque del MCP en `bin/mcp/start-<srv>.sh` para no duplicarla.

3. **Instrucciones agnósticas** — escribí todo en `AGENTS.md` y enlazá:
   ```bash
   ln -sf AGENTS.md CLAUDE.md
   ln -sf AGENTS.md GEMINI.md
   ```
   (Este mismo repo usa ese patrón: `CLAUDE.md → AGENTS.md`.)

## Tests

Verificá que cada CLI levante el plugin: abrí el proyecto en Claude Code y en OpenCode
y confirmá que las skills/MCPs aparecen en ambos.

## Changelog

- **1.0.0** — patrón extraído de `ankify` (opencode.json, .mcp.json, .lsp.json).
