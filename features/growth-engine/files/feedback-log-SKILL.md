---
name: <plugin>-feedback-log
description: "Captura feedback/fricción mid-session sin interrumpir el flujo. Loguea en <datadir>/memory/ para que el hotpatch lo procese después. No parchea — solo registra."
---

# <plugin> — Feedback Log

Captura sin interrumpir. Invocar cuando: el usuario corrige el comportamiento, hay
fricción, aparece un caso no contemplado o una preferencia nueva.

## Proceso
1. Articulá el feedback en 1–3 líneas.
2. Guardá en `<datadir>/memory/feedback_<slug>.md` usando `feedback-template.md`:
   - `signal`: correccion | friccion | escenario | preferencia
   - `needs_patch`: true/false
   - `patch_target`: archivo a editar (si aplica)
   - `applied: false`
3. Confirmá brevemente y seguí con el flujo actual.
