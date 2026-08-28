# Plan: paridad OpenCode + capa TS

> **Estado: ejecutado** (verificado 2026-08-27) — evidencia: `.opencode/hooks/` con paridad y `bin/test-opencode-shim.sh`.
> Los checkboxes de abajo quedaron sin tildar: en este repo el estado real de una
> tarea vive en `DONE.md` del store central, no en el plan. No los leas como pendientes.


**Fecha:** 2026-08-23
**Alcance decidido:** solo la capa `.opencode/` pasa a TypeScript; `bin/` (Python)
queda como núcleo universal que consumen todos los CLIs.

## Diagnóstico

El núcleo (`bin/*.py`) es compartido por Claude Code y OpenCode, así que la lógica
de negocio está en paridad por construcción. Lo desactualizado es la superficie de
integración host:

| Superficie | Claude Code | OpenCode hoy |
|---|---|---|
| Skills | auto-discovery | ✓ `config` hook |
| Stop (feedbacks/fricción) | `hooks.json` | ✓ `global.disposed` → script universal |
| Bootstrap AGENTS.md (repo propio) | SessionStart | ✓ transform, solo `isInOwnRepo()` |
| SessionStart en proyectos de plugin | ✓ audit 1 vez/proyecto, re-arme por versión, ofrece multi-cli-compat y alta en registry | ✗ no existe fuera del repo propio |
| Agente `feedback-harvester` | ✓ `agents/` | ✗ no registrado → el Stop sugiere un subagente inexistente |

Auditorías deterministas: portabilidad 0 CRITICAL / 5 WARNING documentales;
estructura de skills OK. La capa `.opencode/` son 137 líneas JS sin tipos.

## Cambios (estilo ankify)

```
.opencode/
  plugins/cli-plugin-template.ts   # entry: compone módulos
  lib/{paths,bootstrap,stop-hook}.ts
  hooks/session-start.ts           # Gap 1: corre bin/hooks/session-start.sh en cualquier repo (cacheado), inyecta su stdout si no es vacío. El script ya trae todos los guards (sentinel, marcador en .git, versión).
  hooks/discover-agents.ts         # Gap 2: agents/*.md → config.agent (frontmatter name/description → prompt + mode:"subagent", patrón ankify). Sin tools: el subagente OC trae bash/read/grep default.
```

- Guard anti doble-inyección: `BOOTSTRAP_MARKER` como primera línea también del
  mensaje de session-start (el transform es stateless entre steps).
- tsconfig.json estricto (esnext/bundler/noEmit) + `@types/node`.
- `package.json` main y `opencode.json` plugin → `.ts` (OpenCode corre Bun).
- `test-opencode-shim.sh`: runner bun → node `--experimental-strip-types`; nuevas
  assertions para agentes registrados y mensaje de session-start en proyecto externo.
- Docs: `.opencode/INSTALL.md`, nota de `features/multi-cli-compat/README.md`
  ("OpenCode plugin = .js") se actualiza solo tras verificar carga real del .ts,
  bump `meta.yml` 2.8.2 → 2.9.0.

## Fuera de alcance

- Migrar `bin/` Python a TS (núcleo agnóstico, rompería portabilidad).
- WARNINGs `claude-only-path` documentales (.gitignore/AGENTS.md/CLAUDE.md).

## Verificación

`bun x tsc --noEmit` + `bin/test-opencode-shim.sh` + suite completa de tests +
audit-portability.py sin CRITICAL nuevos.
