# Feature: growth-engine

## Qué hace

Permite que el plugin **se mejore solo** capturando feedback y fricción en tiempo real.
Cuando el usuario corrige el comportamiento o aparece un caso no contemplado, se
loguea; un motor de hotpatch lo procesa después: articula el gap, encuentra el archivo
correcto, aplica el parche y lo commitea.

## Por qué

Las mejoras descubiertas mientras se usa el plugin se pierden si no hay un mecanismo
para capturarlas. Este patrón convierte la fricción en mejoras concretas sin necesidad
de sesiones de refactor dedicadas, y mantiene los gaps en memoria en vez de en deuda
técnica.

> Encaja directo con el modelo de este catálogo: una mejora capturada en un plugin que
> resulta reusable se promueve al catálogo (ver `CONTRIBUTING.md`).

## Integración

### 1. Logger — `skills/<plugin>-feedback-log/SKILL.md`

Captura sin interrumpir el flujo actual. Guarda en el datadir
(`<datadir>/memory/feedback_<slug>.md`) con frontmatter:
```markdown
---
signal: correccion | friccion | escenario | preferencia | discovery | capability-gap
needs_patch: true | false
patch_target: <archivo a editar, si aplica>
applied: false
---
<descripción del feedback>
```

**Captura proactiva (opcional).** El logger no solo espera a ser invocado: detecta fricción
mid-session (frases de desacuerdo del usuario, o un `capability-gap` cuando el plugin no tiene
código para lo pedido) y ofrece registrarla. Además, al cierre de sesión puede hacer
**auto-harvest**: minea eventos externos (context-mode / engram) — `error`/`blocker`/`decision` —
los atribuye al plugin por skill namespace, contrasta contra lo ya logueado y propone los
faltantes (`auto_detected: true`). Ver `plugin-feedback-log` Steps 6–7.

### 2. Motor — `skills/<plugin>-hotpatch/SKILL.md`

- **Step 0**: detecta feedbacks pendientes (`applied: false`).
- **Steps 1–4**: articula el gap, mapea el archivo correcto, propone el fix.
- **Step 5**: aplica el parche, marca `applied: true`, commitea.

### 3. Auto-descubrimiento — metadata `_hotpatch`

Cada archivo de control (config JSON, skill, template) lleva metadata que dice quién lo
posee y quién lo consume, para que el motor sepa dónde tocar:
```json
"_hotpatch": {
  "purpose": "qué hace este archivo",
  "owner": "hotpatch directo | skill-específico",
  "consumers": ["skills/...", "config/..."]
}
```

## Trigger

Invocá el logger cuando: el usuario corrige el comportamiento, se detecta fricción,
aparece un valor/escenario no contemplado, o el plugin manejó algo mal. Invocá el motor
cuando convenga procesar lo acumulado.

## Tests

Logueá un feedback de prueba con `applied: false` y verificá que el motor lo detecta en
su Step 0 y lo marca `applied: true` tras parchear.

## Changelog

- **1.1.0** — captura proactiva mid-session + auto-harvest post-sesión y signal `capability-gap`
  (portado de `ankify` al desmantelar su capa de mejora-de-plugins; ahora vive en el meta-plugin).
- **1.0.0** — patrón extraído de `ankify` (anki-feedback-log + anki-hotpatch).
