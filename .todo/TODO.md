# TODOs — cli-plugin-template

_Última revisión: 2026-08-23_

## Q1 — Urgente e Importante
> Hacer ahora. Fallos en producción, pérdida de datos, sin respuesta al usuario.

## Q2 — No urgente e Importante
> Planificar. Features críticas, bugs no bloqueantes, mejoras arquitectónicas.

- [ ] Prevención de drift de APIs externas: convención "afirmación negativa con fecha de verificación" + chequeo automático — bin/audit-doc-drift.py (grepea marcadores como "no expone"/"sin equivalente" y exige fecha fresca ≤6 meses, excluyendo archivos históricos) + Parte D en skills/plugin-audit/SKILL.md + fechar las afirmaciones vivas existentes (stop-hook.ts, multi-cli-compat README tras verificar Gemini, tool-mapping PreCompact) + casos en la suite.



## Q3 — Urgente y No importante
> Hacer rápido o delegar. Cambios de bajo impacto que no pueden esperar.

## Q4 — No urgente y No importante
> Diferir o eliminar. Deuda técnica, cosméticos, nice-to-haves.
