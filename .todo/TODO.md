# TODOs — cli-plugin-template

_Última revisión: 2026-08-23_

## Q1 — Urgente e Importante
> Hacer ahora. Fallos en producción, pérdida de datos, sin respuesta al usuario.

## Q2 — No urgente e Importante
> Planificar. Features críticas, bugs no bloqueantes, mejoras arquitectónicas.

- [ ] **Guard ciego ante MultiEdit** — bin/hooks/catalog-guard.py:48 solo escanea `content`/`new_string` plano, así que un MultiEdit (edits[]) puede inyectar un fenced script >2 líneas en SKILL.md sin ser bloqueado en el momento; hoy lo agarra recién el pre-commit audit-skill-structure.py _(creado por: SmithDR · 2026-08-23)_
- [ ] **SUITE_RE de OpenCode ignora npm test** — .opencode/hooks/tool-guard/index.ts:17 no incluye `\bnpm (run )?test\b` como la versión Python (bin/hooks/test-failure-nudge.py:10), entonces un `npm test` fallido en OC no dispara el nudge de fricción y ese feedback se pierde silenciosamente _(creado por: SmithDR · 2026-08-23)_

## Q3 — Urgente y No importante
> Hacer rápido o delegar. Cambios de bajo impacto que no pueden esperar.

## Q4 — No urgente y No importante
> Diferir o eliminar. Deuda técnica, cosméticos, nice-to-haves.

- [ ] **tool-mapping.md sin fila PostToolUseFailure** — la tabla de eventos de skills/plugin-dev/references/tool-mapping.md documenta PreToolUse/PostToolUse/UserPromptSubmit/Stop/PreCompact pero omite PostToolUseFailure, así que un agente portando hooks no sabe que CC distingue fallo (input.error con exit code) y OC no (tool.execute.after corre siempre) _(creado por: SmithDR · 2026-08-23)_
