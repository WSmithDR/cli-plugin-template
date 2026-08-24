# TODOs — cli-plugin-template

_Última revisión: 2026-08-23_

## Q1 — Urgente e Importante
> Hacer ahora. Fallos en producción, pérdida de datos, sin respuesta al usuario.

## Q2 — No urgente e Importante
> Planificar. Features críticas, bugs no bloqueantes, mejoras arquitectónicas.

- [ ] intent-nudge: `startswith(local_path)` hereda el nudge a dirs hermanos con prefijo (`/tmp/proj-ankify2` matchea `/tmp/proj-ankify`) — comparar por segmento de ruta (`cwd == lp or cwd.startswith(lp + "/"`), en paridad py (`bin/hooks/intent-nudge.py:31`) y TS (`.opencode/hooks/bootstrap-inject/intent.ts:20`). Caso de test en ambas suites.

## Q3 — Urgente y No importante
> Hacer rápido o delegar. Cambios de bajo impacto que no pueden esperar.

## Q4 — No urgente y No importante
> Diferir o eliminar. Deuda técnica, cosméticos, nice-to-haves.
