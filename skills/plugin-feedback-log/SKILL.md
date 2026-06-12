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
   Avisar: *"Ese plugin no está registrado. Corré /plugin register en su repo para que
   cli-plugin-template administre su evolución."* y terminar.

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

```bash
python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" feedback save "$PLUGIN" "<slug>" - << 'FEEDBACK_EOF'
---
name: feedback-<slug>
description: "<description — una línea, específica>"
plugin: <PLUGIN resuelto>
skill_namespace: <ej. ankify:anki-capture>
applied: false
needs_patch: <true|false>
patch_target: "<ruta relativa al repo del plugin, o vacío si needs_patch=false>"
source: <source>
signal: <correccion|friccion|escenario|preferencia>
---

<Descripción del gap en 2-4 líneas: qué ocurrió, qué faltaba, contexto mínimo.>

**Why:** <por qué importa — consecuencia concreta si no se corrige>
**How to apply:** <qué debe hacer el plugin en situaciones similares>
FEEDBACK_EOF
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
