# TODOs — cli-plugin-template

_Última revisión: 2026-08-23_

## Q1 — Urgente e Importante
> Hacer ahora. Fallos en producción, pérdida de datos, sin respuesta al usuario.

## Q2 — No urgente e Importante
> Planificar. Features críticas, bugs no bloqueantes, mejoras arquitectónicas.



## Q3 — Urgente y No importante
> Hacer rápido o delegar. Cambios de bajo impacto que no pueden esperar.

## Q4 — No urgente y No importante
> Diferir o eliminar. Deuda técnica, cosméticos, nice-to-haves.

- [ ] **Externalización de knobs de scripts** — los umbrales están hardcodeados en el código (FRESH_DAYS en bin/audit-doc-drift.py, umbrales/severidades del portability-audit), así que un consumidor que quiera otros valores debe tocar código; migrarlos a config/*.json habilita el feature externalized-config _(creado por: SmithDR · 2026-08-23)_
