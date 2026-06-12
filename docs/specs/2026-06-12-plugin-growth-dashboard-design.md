# P4 — plugin-growth: dashboard de evolución

## Contexto

Con P0-P2 el meta-plugin registra plugins, captura fricción y la parchea. Faltaba
**observabilidad**: ver de un vistazo el estado de evolución de todos los plugins sin
correr varios `list` a mano. P4 agrega esa vista.

## Diseño

- **Agregación determinista** en `bin/cpt status` (bundled-script, testeable), no en la skill.
  Reusa `feedback_list` y `proposal_list`; nueva `gateway.growth_summary(plugin=None)`.
- **Skill fina `plugin-growth`** que invoca `cpt status`, presenta la tabla y ofrece
  drill-down + el siguiente paso (`plugin-hotpatch` si hay pendientes). No modifica nada.

`growth_summary` devuelve por plugin: `feedbacks {pending, applied, total}` y
`proposals {pending, approved, discarded, total}`, más `totals`. Incluye plugins registrados
y cualquier subdir con datos (helper `_known_plugins`).

`cpt status` imprime tabla humana por default; `--json` para consumo programático;
`--plugin <name>` filtra.

## Verificación

- `bin/test-cpt-status.sh`: store vacío → mensaje guía; con datos mixtos (pendientes/aplicados,
  propuestas en varios status) → conteos correctos en `--json`; `--plugin` filtra.
- Sin regresiones en validate-catalog / portability / suites previas.

## Fuera de alcance

P3 (vocabulary guardian) y P5 (migración de ankify) siguen pendientes, cada uno con su spec.
