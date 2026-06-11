# Tool mapping entre CLIs

Las skills se escriben con los nombres de tools de **Claude Code**. En otros CLIs, el
nombre cambia. Esta tabla traduce los más comunes. Incluí el subset que usen tus skills.

## Tabla principal

| Claude Code | Gemini CLI | Copilot CLI | Codex | OpenCode |
|---|---|---|---|---|
| `Read` | `read_file` | `view` | tool de archivo nativo | nativo |
| `Write` | `write_file` | `create` | tool de archivo nativo | nativo |
| `Edit` | `replace` | `edit` | tool de archivo nativo | nativo |
| `Bash` | `run_shell_command` | `bash` | shell nativo | nativo |
| `Skill` (tool) | `activate_skill` | `skill` | se cargan nativamente | `skill` |
| `Task` (subagente) | `@generalist` | `task` con `agent_type` | `spawn_agent` | subagente nativo |
| `TodoWrite` | — | — | `update_plan` | `todowrite` |
| `WebSearch` | — | `web_fetch` | — | — |
| `WebFetch` | `web_fetch` | `web_fetch` | — | — |

> Las celdas vacías (—) no tienen equivalente directo; documentá una alternativa o evitá
> esa tool en skills que deban ser multi-CLI.

## Cómo cada CLI recibe esta tabla

- **Gemini CLI**: referenciá este archivo con un `@`-include en `GEMINI.md`
  (`@./.../tool-mapping.md`). Se inyecta en cada sesión.
- **Copilot / Codex**: el `AGENTS.md` apunta a este archivo; el usuario/agent lo consulta.
- **Claude Code**: no lo necesita (usa los nombres nativos).

## Detección de entorno (worktrees, etc.)

Para lógica que dependa del entorno git, usá comandos read-only universales en vez de
tools específicas (ver feature `worktree-redirect`):

```bash
[ "$(git rev-parse --git-dir)" != "$(git rev-parse --git-common-dir)" ] && echo "worktree"
```
