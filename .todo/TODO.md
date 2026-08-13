# TODOs — cli-plugin-template

_Última revisión: 2026-08-12_

## Q1 — Urgente e Importante
> Hacer ahora. Fallos en producción, pérdida de datos, sin respuesta al usuario.

## Q2 — No urgente e Importante
> Planificar. Features críticas, bugs no bloqueantes, mejoras arquitectónicas.

- [ ] **Suites de test fuera del CI** — `.github/workflows/validate.yml` corre solo 5 de las 13 suites de `bin/test-*.sh`: quedan afuera `test-detect-feedback.sh`, `test-cpt-registry/feedback/proposal/status/crossrepo.sh`, `test-opencode-shim.sh` y `test-skill-structure.sh`. Hoy esas solo se ejecutan en el hook `pre-commit` local, así que un commit hecho desde la web de GitHub (o con `--no-verify`) puede romper el recolector de feedback, el gateway `cpt` o el shim de OpenCode y el CI igual pasa verde. _(creado por: SmithDR · 2026-08-12)_

## Q3 — Urgente y No importante
> Hacer rápido o delegar. Cambios de bajo impacto que no pueden esperar.

## Q4 — No urgente y No importante
> Diferir o eliminar. Deuda técnica, cosméticos, nice-to-haves.
