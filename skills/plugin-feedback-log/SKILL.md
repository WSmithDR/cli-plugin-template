---
name: plugin-feedback-log
description: "Captura fricción/corrección sobre la skill de un plugin propio y la guarda en el store de evolución (bin/cpt feedback save). No parchea — solo loguea para que plugin-hotpatch lo procese después."
when_to_use: "Invocar cuando, usando un plugin propio (ankify, este, otro registrado), aparece una corrección, fricción, escenario no contemplado o preferencia, y querés dejarlo anotado sin interrumpir el flujo. La fricción se atribuye al plugin por su skill namespace, no por el cwd."
---

# plugin-feedback-log — captura de fricción de plugins

Una sola vía: `bin/cpt feedback save <plugin> <slug> -`.

**No parchea.** Solo loguea con `applied: false`. `plugin-hotpatch` (P2) aplica el
patch cuando `needs_patch: true`, contra el repo del plugin (`local_path` del registry).

La fricción se atribuye al **plugin dueño de la skill que falló**, identificado por su
**skill namespace** (ej. `ankify:anki-capture` → `ankify`), aunque estés trabajando en
otro proyecto.

---

## Step 1: Identificar el plugin (skill namespace → registry)

1. Determinar qué **skill namespace** causó la fricción. Sale del contexto de la
   conversación: la skill que estabas usando cuando apareció el problema
   (ej. `ankify:anki-capture`, `cli-plugin-template:plugin-audit`). Si solo tenés el
   nombre del plugin, alcanza con ese prefijo.
2. Resolver contra el registry (allowlist):
   ```bash
   PLUGIN=$(python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" registry resolve "<skill_namespace>")
   ```
3. **Si NO resuelve** (vacío / rc=1): el plugin no está en el allowlist. NO guardar.
   Avisar: *"Ese plugin no está registrado. Decime 'registrá este plugin' en su repo
   (skill plugin-register) para que cli-plugin-template administre su evolución."* y terminar.

El registry es la baranda: el meta-plugin solo administra plugins dados de alta.

---

## Step 2: Recibir input

| Campo | Fuente | Requerido |
|---|---|---|
| `description` | argumento / contexto | sí |
| `skill_namespace` | skill que causó la fricción (Step 1) | sí |
| `signal` | clasificar según tipo | sí |
| `needs_patch` | ¿requiere cambio en un archivo del plugin? | sí (default: false) |
| `patch_target` | ruta **relativa al repo del plugin** a parchear | solo si needs_patch=true |
| `source` | skill o contexto que invoca | opcional |

**Clasificar `signal`:**
- `correccion` — el usuario dijo que algo estuvo mal
- `friccion` — algo fue más difícil de lo que debería, faltó algo
- `escenario` — caso válido que el plugin no supo manejar
- `preferencia` — guía de comportamiento sin error explícito
- `discovery` — aprendizaje positivo sobre compatibilidad multi-CLI descubierto durante desarrollo (ver `capture-learning.sh`)
- `capability-gap` — el usuario pidió algo que el plugin **no tiene código para hacer** (se improvisa una solución manual que debería ser automática)

**Detectar `capability-gap`** — se dispara cuando: el agente dice "no hay skill/código para esto", el flujo se desvía del pipeline del plugin por falta de una pieza, o una función que debería ser automática se hace a mano.

**`needs_patch`:** `true` si el fix requiere editar un archivo del plugin (SKILL.md,
config, script); `false` si es preferencia/guía que no cambia código.

`patch_target` es **relativo a la raíz del repo del plugin** (no al cwd): el patch de P2
es cross-repo contra `local_path` del registry.

---

## Step 3: Generar slug

```
slug = description → lowercase → no-alnum a '-' → truncar 40 → quitar '-' extremos
```
Verificar que no exista:
```bash
python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" feedback list --plugin "$PLUGIN" | grep "<slug>"
```
Si existe: sufijo `-2`, `-3`, etc.

---

## Step 4: Escribir via cpt feedback save (única vía)

Construí el documento según `references/feedback-template.md` (rellenando los
placeholders) y guardalo pasándolo por stdin a:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" feedback save "$PLUGIN" "<slug>" -
```

Escribe a `<data_dir>/<plugin>/feedbacks/feedback_<slug>.md`. No hay otra vía.

---

## Step 5: Confirmar

```
Feedback guardado ✓
  Plugin:  <PLUGIN>
  Slug:    <slug>
  Signal:  <signal>
  Patch:   <needs_patch> <→ patch_target si aplica>
```

Si `needs_patch: true`: agregar *"→ plugin-hotpatch lo aplicará al repo del plugin cuando
sea conveniente (con tu aprobación)."*

---

## Step 6: Detección proactiva mid-session (opcional)

Mientras usás un plugin registrado, auto-detectá fricción **en el momento**, sin esperar a
que el usuario invoque la skill.

**Señales de capability-gap** (el plugin no tiene código para lo pedido):
- vas a implementar algo a mano porque no hay skill para eso
- el flujo se desvía del pipeline normal del plugin por falta de una pieza

→ Preguntá: *"Esto que pedís el plugin no lo cubre con código. ¿Lo registro como
`capability-gap` para desarrollarlo después?"*

**Señales de fricción / desacuerdo del usuario:**
- "no me gusta" / "prefiero" → `preferencia`
- "está mal" / "no funciona" → `correccion`
- "no sirve" / "incompleto" / "falta algo" → `friccion`

→ Preguntá: *"Veo que esto no te convenció. ¿Lo registro como feedback del plugin?"*

Si confirma → Step 1→4 (resolvé el plugin por la skill namespace activa). Si no, seguí el flujo.

---

## Step 7: Auto-harvest post-sesión (opcional)

Al cierre de sesión (o on-demand), mineá eventos no cubiertos y proponé feedbacks. Es
**agnóstico de plugin**: la fuente de eventos es externa (context-mode / engram), no un log
propio del meta-plugin.

1. **Leer eventos** recientes vía la fuente disponible (ej. `ctx_search(sort:"timeline")` de
   context-mode, o memoria de engram): `error` / `blocker` / `decision` / `rejected-approach` /
   `user-prompt` que pidió algo sin cobertura.
2. **Atribuir plugin**: por cada evento, identificá la skill namespace involucrada → resolvé el
   plugin (Step 1). Descartá eventos cuyo plugin no esté registrado.
3. **Contrastar** contra lo ya logueado: `cpt feedback list --plugin "$PLUGIN"` — si ya hay un
   feedback equivalente (por keyword/descripción), skip.
4. **Clasificar** el candidato: `error`→`correccion`, `blocker`→`friccion`,
   `decision`→`preferencia`/`correccion`, gap sin skill→`capability-gap`.
5. **Presentar** la lista al usuario (opciones: `todos` / índices `1 2` / `ninguno` / `editar N`).
6. **Guardar** los confirmados con Step 1→4, agregando `auto_detected: true` al frontmatter.
