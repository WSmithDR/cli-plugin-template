# Feature: learning-system

## Qué hace

Memoria de **aprendizajes vigentes** sobre cómo se desarrolla el plugin: convenciones,
decisiones de compat multi-CLI, integraciones. A diferencia del feedback store (que
acumula con ciclo lineal pending → applied), un aprendizaje se **corrige** cuando la
realidad lo desmiente y se **borra** cuando deja de valer — nunca se "cierra".

El valor está en el loop de hooks que aplica el conocimiento en el momento justo:

| Momento | Hook | Qué hace |
|---|---|---|
| Al abrir un Edit | PreToolUse | Recuerda los learnings vigentes ANTES de decidir el enfoque |
| Después de editar | PostToolUse | Detecta si el diff captura una convención nueva o contradice un aprendizaje |
| Falla una suite | PostToolUseFailure | Si el output contradice un aprendizaje, sugiere corregir código Y aprendizaje juntos |
| Al cierre de sesión | Stop | Barre learnings modificados hoy: "los tocaste, verificalos" |

## Por qué

Los feedbacks capturan qué salió mal; los aprendizajes capturan qué se aprendió. Sin
store propio, cada corrección del usuario se vuelve a pagar en la siguiente sesión. Y
sin hooks, el store es un cemento de documentos que nadie consulta: el momento importa
— al abrir sesión nadie tiene una decisión que tomar; al editar, sí.

Requiere `growth-engine`: reusa su registry (`registry.json`) para saber a qué plugin
pertenece un archivo, y la convención de datadir + CLI (`cpt learning ...`).

## Integración

### 1. Store — `files/learning_store.py`

Módulo standalone (~90 líneas). Copiar a `<plugin>/bin/lib/`. Estructura en disco:

```
<datadir>/
  _global/learnings/learning_<slug>.md     ← del taller: aplica a todos los plugins
  <plugin>/learnings/learning_<slug>.md    ← específico del plugin
```

Cada learning es markdown con frontmatter sellado por el store:

```markdown
---
scope: miplugin
created: 2026-08-25
last_updated: 2026-08-25
category: convencion
---
el shim delega en el .py
```

Reglas del store:
- **Upsert por tema**: guardar dos veces el mismo slug CORRIGE, no duplica.
  `created` se preserva del archivo previo; `last_updated` es siempre hoy.
- **Categorías**: `convencion | integracion-cli | compat-multi-cli` (ajustalas a tu dominio).
- `learning_list(plugin)` devuelve lo del plugin MÁS `_global` — un aprendizaje del
  taller nacido en un plugin aplica en todos.

### 2. CLI — `cpt learning`

Subcomando con `save | list | show | delete` sobre el store (ver `cpt` de este repo,
líneas ~143–252, como referencia). `save` acepta `--plugin`, `--category`, y contenido
por arg o stdin (`-`).

### 3. Hooks — `files/*.py`

Los cuatro skeletons asumen la estructura `bin/hooks/` + `bin/lib/` de este repo y
leen `registry.json` del datadir (via `_plugin_of()`, incluida en cada skeleton).
Adaptar:
- El nombre del datadir/env override (`CLI_PLUGIN_TEMPLATE_DATA_DIR` → el tuyo).
- La ruta del CLI en los mensajes (`_CPT`).
- Los patrones de convención de `detect-learning.py` (`_diff_shows_convention`) son
  de este taller: reemplazalos por los patrones de TU plugin.

Registro en `hooks/hooks.json` (Claude Code):
```json
{"type": "command", "hooks": [{"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/bin/shims/<hook>.sh"}]}
```
con matcher `PreToolUse` / `PostToolUse` (Edit|Write|MultiEdit) / `PostToolUseFailure` (Bash) / `Stop`.

**Paridad multi-CLI:** PostToolUse no existe en OpenCode (verificado 2026-08-25);
PreToolUse ahí solo puede mutar args o bloquear, no inyectar contexto. El sweep de
Stop es portable vía evento `session.compacted`/equivalente.

### 4. Heurística de contradicción

Tanto `detect-learning.py` como `test-failure-nudge.py` matchean keywords: extraen
palabras (≥4 chars, truncadas a 8, sin frontmatter ni headings) del body del
aprendizaje, normalizan texto (minúsculas, sin tildes), y disparan con ≥2 hits.
Es deliberadamente simple — se afina con uso real; el cooldown por archivo/sesión
mitiga falsos positivos.

## Tests

1. Store: save dos veces el mismo slug → un solo archivo, `created` preservado,
   `last_updated` = hoy. Delete → archivo fuera.
2. Nudge: primera edición en plugin con learnings → mensaje; segunda → silencio;
   sesión nueva → vuelve.
3. Detect: diff con 2+ keywords de un learning → propone update; diff con patrón de
   convención → propone save; plugin sin learnings → silencio.
4. Failure-nudge: error con keywords del body → mensaje incluye "aprendizaje";
   sin overlap → solo feedback.
5. Sweep: learning con `last_updated` = hoy → reportado; sin learnings de hoy → silencio.

Referencia completa: `bin/test-cpt-learning.sh` de este repo (29 casos).

## Changelog

- 1.0.0 — Promovido desde la infra de cli-plugin-template (loop F6 completo).
