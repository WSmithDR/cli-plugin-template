# Tool mapping entre CLIs

Las skills de este plugin (`plugin-dev` y las que enruta: `plugin-audit`,
`plugin-feature`, `plugin-recommend`, `plugin-promote`) están escritas con los nombres
de tools de **Claude Code**. En otros CLIs esos nombres cambian. Esta tabla traduce los
que las skills nombran; si tu CLI no aparece, usá el equivalente nativo más cercano.

## Tabla principal

| Claude Code | Gemini CLI | Copilot CLI | Codex | OpenCode |
|---|---|---|---|---|
| `Skill` (invocar skill) | `activate_skill` | `skill` | se cargan nativamente (lee `SKILL.md`) | `skill` |
| `Task` (subagente) | `@generalist` | `task` con `agent_type` | `spawn_agent` | subagente nativo |
| `Read` | `read_file` | `view` | tool de archivo nativo | nativo |
| `Edit` | `replace` | `edit` | tool de archivo nativo | nativo |
| `Write` | `write_file` | `create` | tool de archivo nativo | nativo |
| `Bash` | `run_shell_command` | `bash` | shell nativo | nativo |

> El router `plugin-dev` enruta con `Skill(...)` en Claude Code. En cada CLI traducí esa
> invocación a la columna correspondiente: en Gemini es `activate_skill`, en OpenCode/Copilot
> es `skill`, y en Codex las skills se cargan solas leyendo `SKILL.md`.

## Hook mapping (Claude Code → OpenCode)

Estos hooks NO existen en OpenCode; planificá alternativas si tus skills dependen de ellos:

| Claude Code | OpenCode | Qué hacer |
|---|---|---|
| `PreToolUse` | No existe | Post-gate informativo en `tool.execute.after` (no bloquea) |
| `Stop` / `SubagentStop` | No existe | Detectores en `messages.transform` con flag de módulo `_checked` |
| `PostToolUse` | `tool.execute.after` | Equivalente directo |

## Cómo cada CLI recibe esta tabla

- **Gemini CLI**: se inyecta vía `@`-include en `GEMINI.md` (`@./skills/plugin-dev/references/tool-mapping.md`).
- **OpenCode**: el plugin JS (`.opencode/plugins/cli-plugin-template.js`) apunta a este archivo en el bootstrap.
- **Copilot / Codex**: `AGENTS.md` referencia el catálogo; consultá esta tabla al traducir tools.
- **Claude Code**: no la necesita (usa los nombres nativos).

## Nota sobre el path del catálogo

Las skills referencian el catálogo con `${CLAUDE_PLUGIN_ROOT}/features/`. Esa variable la
define Claude Code; en otros CLIs resolvé la raíz del plugin de forma equivalente (el dir
raíz del repo o la variable de entorno que exponga ese CLI).
