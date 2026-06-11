# Feature: advanced-hooks

## Qué hace

Tres mecanismos de hooks de Claude Code más allá del exit-2/stderr básico (ver
`claude-code-hooks`): **asyncRewake** (revisión en background que re-despierta al agente),
**filtrado por patrón de comando**, y **correr un agente LLM dentro de un hook**.

## Por qué

Un hook bloqueante (exit 2) frena el flujo. Para revisiones que son "informativas pero no
críticas" (un security review tras `git commit`), querés que corran en background y el
agente siga; cuando terminan, te avisan. Y querés disparar el hook solo en los comandos
que importan, no en cada Bash.

## Patrones

### 1. asyncRewake — background + re-despertar

El hook corre asíncrono; al terminar, Claude Code **re-despierta al agente** con los
hallazgos. No bloquea la respuesta al usuario.

```json
{
  "type": "command",
  "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/review.sh",
  "if": "Bash(git commit:*)",
  "asyncRewake": true,
  "rewakeMessage": "Revisión en background del commit — atendé o reconocé los hallazgos abajo, luego seguí con el pedido original:",
  "rewakeSummary": "La revisión del commit encontró issues"
}
```

El script entrega el contexto según el evento:
- **PostToolUse**: vía `hookSpecificOutput.additionalContext` en el JSON de stdout.
- **Stop/SubagentStop**: guía por `stderr` + `{"decision":"block","reason":...}` en stdout.

### 2. Filtrado por patrón de comando (`if`)

`matcher` filtra por tipo de tool; `if` filtra por **patrón del comando** dentro de Bash:

```json
{ "matcher": "Edit|Write|MultiEdit", "hooks": [ ... ] }          // por tool
{ "if": "Bash(git push:*)", "hooks": [ ... ] }                   // por comando
```

`Bash(git commit:*)` matchea cualquier `git commit ...`. Evita correr hooks costosos en
comandos irrelevantes.

### 3. Agente LLM dentro de un hook

Un hook puede correr un agente completo (con Read/Grep/Glob) en background para análisis
profundo, no solo lógica determinista. Combinalo con un fast-path determinista (ver
`bundled-scripts`): patrón rápido por defecto, agente como deep-dive. Degradá con gracia
si el SDK/credenciales no están (fallback al fast-path).

## Integración

1. Identificá la revisión que NO debe bloquear → `asyncRewake: true` con `rewakeMessage`.
2. Acotá con `if: "Bash(<cmd>:*)"` o `matcher`.
3. Para análisis profundo, corré el agente en background y devolvé el contexto por el canal
   correcto según el evento.

## Tests

Dispará el comando objetivo y verificá que el flujo NO se bloquea y que el agente recibe el
rewake con los hallazgos.

## Changelog

- **1.0.0** — mecanismos extraídos de `security-guidance` (hooks.json + security_reminder_hook.py).
