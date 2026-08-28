---
name: plugin-feedback-log
description: "Captura fricción/corrección sobre la skill de un plugin propio y la guarda en el store de evolución (bin/cpt feedback save). No parchea — solo loguea para que plugin-hotpatch lo procese después."
when_to_use: "Invocar cuando, usando un plugin propio (ankify, este, otro registrado), aparece una corrección, fricción, escenario no contemplado o preferencia, y querés dejarlo anotado sin interrumpir el flujo. La fricción se atribuye al plugin por su skill namespace, no por el cwd."
---

# plugin-feedback-log — captura de fricción de plugins

Una sola vía: `bin/cpt feedback save <plugin> <slug> -`.

**No parchea.** Solo loguea con `status: pending`. `plugin-hotpatch` (P2) aplica el
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
3. **Si NO resuelve** (vacío / rc=1): el plugin no está en el allowlist. NO guardar
   todavía — pero **tampoco termines mandando al usuario a otro repo**: está describiendo
   la fricción justo ahora, es el peor momento para interrumpirlo. Ofrecé el alta en el
   acto: *"`<plugin>` no está registrado. ¿Lo doy de alta ahora y sigo con el feedback?"*
   Si acepta → corré `plugin-register` desde acá (resuelve el repo por nombre o ruta, no
   hace falta moverse) y volvé a este Step 1. Si no acepta, terminá sin guardar.

El registry es la baranda: el meta-plugin solo administra plugins dados de alta.

---

## Step 2: Recibir input

| Campo | Fuente | Requerido |
|---|---|---|
| `description` | argumento / contexto | sí |
| `skill_namespace` | skill que causó la fricción (Step 1) | sí |
| `signal` | clasificar según tipo | sí |
| `plugin_version` | la versión que **estabas usando** cuando apareció la fricción | sí, si la sabés |
| `plugin_path` | la raíz desde donde **corrió** el plugin | solo si NO es el repo del registry |
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

**`plugin_version` es la versión que corrías, no la del repo.** Sale del `Base directory for
this skill:` que encabeza la invocación, o del `CLAUDE_PLUGIN_ROOT` del hook que corre — esa
ruta ya trae la versión instalada. **Nunca** de listar `plugins/cache/<plugin>/<plugin>/` y
quedarse con el semver más alto: ahí se acumulan versiones viejas y prototipos abandonados, y
el mayor no es el activo. Declarala siempre que la sepas: el clon local puede estar atrasado
respecto de lo instalado, y un `patch_target` puede dejar de existir entre la captura y el
patch. Si no la declarás, el store la completa desde el manifiesto del repo — una aproximación,
no lo que observaste.

**`plugin_path` cubre el caso `--plugin-dir`.** Si el plugin corrió desde un árbol que no es
el `local_path` del registry (un `claude --plugin-dir <ruta>`, un worktree, otro clon),
declaralo: es la misma base directory de arriba. El store lo descarta solo si coincide con
`local_path`. Importa porque `plugin-hotpatch` parchea `local_path`: sin este campo, el fix
aterriza en un árbol distinto del que produjo la fricción, y nada lo avisa.

---

## Step 3: Generar slug

```
slug = description → lowercase → no-alnum a '-' → truncar 40 → quitar '-' extremos
```
Verificar que no exista:
```bash
python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" feedback list --plugin "$PLUGIN" | grep "<slug>"
```
Si existe, mirá **qué** es lo que existe:

- **La misma fricción, que volvió a pasar** → no crees un gemelo: enriquecé el que está,
  sumándole la ocurrencia nueva (fecha + qué pasó esta vez) al cuerpo. El dedup del store
  bloquea sobrescribir un `pending`/`deferred`, así que va con `--update`:
  `cpt feedback save "$PLUGIN" <slug> - --update` (conserva `status` y `created`).
  Un feedback con `needs_patch: false` pide justamente acumular ocurrencias: sin esto,
  la segunda vez que pasa no queda registrada en ningún lado.
- **Otra fricción distinta que colisiona en el slug** → ahí sí, sufijo `-2`, `-3`, etc.

---

## Step 4: Escribir via cpt feedback save (única vía)

Construí el documento según `references/feedback-template.md` (rellenando los
placeholders) y guardalo pasándolo por stdin a:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" feedback save "$PLUGIN" "<slug>" -
```

Escribe a `<data_dir>/<plugin>/feedbacks/feedback_<slug>.md`. No hay otra vía.

Además, si la queja original del usuario usa una frase característica que NO esté
entre las keywords base ("no me gusta", "está mal", "no funciona"...), enseñásela
al Stop hook para que la próxima vez la cace sola:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" feedback learn "$PLUGIN" "<frase literal>"
```

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

**Registrá en el acto, no pidas permiso.** Guardar un feedback es barato y reversible
(`feedback discard`); lo que sí necesita aprobación es el patch, y de eso ya se ocupa
`plugin-hotpatch`. Preguntar por cada hallazgo convierte al usuario en cuello de botella
de su propia sesión, y el costo real es que los hallazgos se pierden cuando no está
mirando. El principio: **se pide permiso para cambiar código, no para tomar nota.**

**Señales de capability-gap** (el plugin no tiene código para lo pedido):
- vas a implementar algo a mano porque no hay skill para eso
- el flujo se desvía del pipeline normal del plugin por falta de una pieza

→ Registralo como `capability-gap` (Step 1→4) y avisá en una línea:
*"Anotado: `<slug>` · capability-gap — el plugin no cubre esto con código."*

**Señales de fricción / desacuerdo del usuario:**
- "no me gusta" / "prefiero" → `preferencia`
- "está mal" / "no funciona" → `correccion`
- "no sirve" / "incompleto" / "falta algo" → `friccion`

→ Registralo (Step 1→4, resolviendo el plugin por la skill namespace activa) y avisá en
una línea: *"Anotado: `<slug>` · `<signal>`."* Después seguí con lo que estabas haciendo:
el aviso no abre una conversación.

**El único caso que sí se pregunta** es el dudoso: cuando no está claro si la fricción es
del plugin o del usuario (un error propio, una decisión que el usuario tomó a sabiendas).
Ahí preguntá antes de guardar — un feedback mal atribuido ensucia el store de otro plugin.

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
