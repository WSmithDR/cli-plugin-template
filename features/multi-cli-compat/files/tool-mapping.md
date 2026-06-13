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

> - **OpenCode**: las tools de archivo (`Read`, `Write`, `Edit`, `Bash`) son nativas
>   (mismos nombres). Los hooks tienen diferencias críticas — ver "Hook mapping" abajo.
> - Las celdas vacías (—) no tienen equivalente directo; documentá una alternativa o evitá
>   esa tool en skills que deban ser multi-CLI.

## Hook mapping (Claude Code → OpenCode)

@opencode-ai/plugin v1.4.3+ expone hooks equivalentes. Todos reciben `(input, output)`
y mutan `output` por referencia.

| Claude Code | OpenCode | Comportamiento |
|---|---|---|
| `SessionStart` | `config` + `messages.transform` | `config` solo paths; bootstrap inyectado en el primer mensaje |
| `PreToolUse` | `tool.execute.before` | `input.tool` = string ID del tool. Muta `output.args` para bloquear — el objeto args es el MISMO que recibe el tool |
| `PostToolUse` | `tool.execute.after` | `input.args` contiene args originales. `output.(output\|title\|metadata)` mutable. Firma: `(input, output)` |
| `Stop` / `SubagentStop` | `event` | Captura `input.event.type === "global.disposed"` |
| `PreCompact` | `experimental.session.compacting` | Muta `output.context` / `output.prompt` |

Notas:
- Throwing en hooks propaga como fallo del tool (bloqueo real).
- Shell tool ID = `"bash"` (source: `packages/opencode/src/tool/shell/id.ts`).

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
