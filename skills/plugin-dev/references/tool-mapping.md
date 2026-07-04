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

@opencode-ai/plugin v1.4.3+ tiene hooks equivalentes a los de Claude Code, pero con
firmas diferentes. Todos los hooks reciben `(input, output)` y mutan `output` por referencia.

| Claude Code | OpenCode | Comportamiento |
|---|---|---|
| `SessionStart` | `config` + `messages.transform` | `config` solo paths; bootstrap inyectado en el primer mensaje |
| `PreToolUse` | `tool.execute.before` | `input.tool` = string ID del tool (`"bash"` para shell). Muta `output.args` para bloquear — el objeto args es el MISMO que ejecuta el tool |
| `PostToolUse` | `tool.execute.after` | `input.args` contiene args originales. `output.(output\|title\|metadata)` mutable. Firma: `(input, output)` — NO `(tool, input, output)` |
| `Stop` / `SubagentStop` | `event` | Captura `input.event.type === "global.disposed"` |
| `PreCompact` | `experimental.session.compacting` | Muta `output.context` / `output.prompt` |
| — (shell env) | `shell.env` | Modifica vars de entorno del shell antes de ejecutar |
| — (bash command) | `command.execute.before` | Solo para comandos del Task tool interno, NO para Bash directo |

Notas:
- Throwing en hooks propaga como fallo del tool (bloqueo real).
- `tool.execute.before` es la herramienta correcta para gates de bash. Ejemplo:
  ```js
  'tool.execute.before': async (input, output) => {
    if (input.tool !== 'bash') return;
    if (/* debe bloquear */) {
      output.args.command = 'true'; // hace el tool harmless
    }
  }
  ```
- Shell tool ID en OpenCode = `"bash"` (source: `packages/opencode/src/tool/shell/id.ts`).

## Cómo cada CLI recibe esta tabla

- **Gemini CLI**: se inyecta vía `@`-include en `GEMINI.md` (`@./skills/plugin-dev/references/tool-mapping.md`).
- **OpenCode**: el plugin JS (`.opencode/plugins/cli-plugin-template.js`) apunta a este archivo en el bootstrap.
- **Copilot / Codex**: `AGENTS.md` referencia el catálogo; consultá esta tabla al traducir tools.
- **Claude Code**: no la necesita (usa los nombres nativos).

## Contrato universal de hooks (cualquier CLI)

La lógica de los hooks NO vive en el adaptador de cada CLI: vive en scripts Python
(`bin/hooks/*.py`) con un contrato mínimo, agnóstico del host:

- **stdin**: JSON con el contexto que el CLI tenga (ej. `{"transcript_path": "..."}`;
  campos ausentes degradan en silencio, nunca rompen).
- **stdout**: JSON con `{"systemMessage": "..."}` si hay algo que reportar; vacío si no.
- **estado**: todo en el store externo vía `bin/lib/gateway.py` (nunca en el adaptador).

Un adaptador por CLI es solo: *mapear su evento de ciclo de vida → ejecutar el script
con ese JSON → mostrar `systemMessage`*. Claude Code lo hace nativo (`hooks/hooks.json`);
OpenCode con ~15 líneas de JS (`.opencode/plugins/cli-plugin-template.js`), que además
acepta `CPT_TRANSCRIPT_PATH` como knob para hosts que puedan proveer un transcript.
CLIs sin hooks de ciclo de vida (Gemini, Codex, Cursor, Copilot) quedan con manifiestos +
skills; el hook simplemente no corre ahí.

## Nota sobre el path del catálogo

Las skills referencian el catálogo con `${CLAUDE_PLUGIN_ROOT}/features/`. Esa variable la
define Claude Code; en otros CLIs resolvé la raíz del plugin de forma equivalente (el dir
raíz del repo o la variable de entorno que exponga ese CLI).
