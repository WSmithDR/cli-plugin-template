---
name: plugin-hotpatch
description: "Motor de evolución cross-repo del meta-plugin: lee un feedback pendiente de un plugin propio, propone un fix con gate de aprobación, y lo aplica en el repo de ESE plugin (aunque no estés ahí)."
when_to_use: "Invocar cuando el hook Stop avisa 'PENDING PLUGIN FEEDBACK', cuando el usuario pide procesar/aplicar fricción capturada, o cuando querés revisar y parchear los feedbacks pendientes de tus plugins registrados."
---

# plugin-hotpatch — parcheo cross-repo asistido

Procesa la fricción capturada por `plugin-feedback-log` y la convierte en un patch sobre el
repo del plugin afectado. **Cross-repo**: parchea el repo target resuelto desde el registry
(`local_path`), aunque tu cwd sea otro. **Acotado por el registry** (baranda 1: solo plugins
dados de alta) y con **gate de aprobación humana** (baranda 2: propuesta persistida + confirmación).

> **Vocabulario nuevo / términos de dominio** → es P3 (vocabulary-guardian centralizado), fuera
> de esta skill. Acá solo se parchean correcciones, fricciones y escenarios.

**Efecto del patch:** toca el **working repo** del plugin (la fuente de verdad). La copia que
está *corriendo* (cache del marketplace) no lo refleja hasta que el plugin se reinstale/actualice
— avisalo al confirmar.

Todas las ops de datos pasan por `python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt"`.

---

## Step 0: Elegir el feedback a procesar

```bash
python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" feedback list --pending
```

- Si el hook Stop señaló uno (o el usuario nombró uno) → tomar ese (`<plugin>/<slug>`).
- Si hay varios y no hay señal → `AskUserQuestion`: "¿Cuál procesamos primero?" listando los
  pendientes.
- Si no hay pendientes → "No hay feedbacks pendientes." y terminar.

---

## Step 1: Resolver el plugin target (baranda 1)

Del id `<plugin>/<slug>`, el `<plugin>` es el target. Confirmar que está en el allowlist y
obtener su ruta local:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" registry list
```

- Buscar la entrada cuyo `name == <plugin>` y leer `local_path`.
- Si no está en el registry → abortar: "Ese plugin no está registrado; no lo puedo tocar.
  Registralo primero (skill plugin-register)."
- Si `local_path` no existe en disco → abortar: "El repo de `<plugin>` no está en `<local_path>`
  (¿lo moviste? re-registralo)."

A partir de acá, `TARGET="<local_path>"` es la raíz del repo a parchear.

---

## Step 2: Leer el feedback

```bash
python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" feedback show <plugin> <slug>
```

Extraer del frontmatter: `description`, `signal`, `needs_patch`, `patch_target`,
`skill_namespace`. Si `needs_patch: false` → no requiere patch (es preferencia/guía); marcar
`feedback apply` y terminar con una nota, sin tocar archivos.

---

## Step 3: Localizar el archivo a parchear (híbrido)

En orden, parando en el primero que resuelva:

1. **`patch_target` presente** → el archivo es `$TARGET/<patch_target>`. Verificar que existe.
2. **Scan estructural** (si no hay `patch_target` o no existe) — buscar por palabras clave del
   gap dentro del repo target:
   ```bash
   grep -rl -i "<keyword>" "$TARGET"/skills "$TARGET"/hooks "$TARGET"/bin \
     "$TARGET"/config "$TARGET"/commands 2>/dev/null
   ```
3. **component-map opcional** — si existe `$TARGET/.plugin-meta/component-map.md`, leerlo con
   `Read` para desempatar entre candidatos (es opt-in; muchos plugins no lo tendrán).
4. **Ambiguo** (varios candidatos) → `AskUserQuestion` listando los archivos para que el usuario
   elija cuál parchear primero.

Si nada resuelve → pedir una pista al usuario en una sola pregunta acotada.

---

## Step 4: Propuesta persistida + gate (baranda 2)

Leer el archivo target con `Read`. Diseñar el **cambio más pequeño** que cierra el gap (no
refactorizar). Persistir la propuesta:

Construí la propuesta según `references/proposal-template.md` (rellenando los placeholders) y
guardala pasándola por stdin a:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" proposal save <plugin> <slug> -
```

`effect`: `config/`, `templates/`, `scripts/` → inmediato; `SKILL.md`, `hooks/`, `bin/`,
`commands/` → próxima sesión (y, cross-repo, recién tras reinstalar el plugin target).

Mostrar el mismo preview en el chat y llamar `AskUserQuestion`:
- question: "¿Aplicamos el hotpatch en `<plugin>`?"
- header: "Decisión"
- options: "Sí" / "Editar — ajustar antes de aplicar" / "Descartar"

Según la respuesta:
- **Sí** → `proposal set-status <plugin> <slug> approved` y seguir a Step 5.
- **Editar** → reescribir la propuesta (`proposal save` de nuevo) y volver a mostrar el gate.
- **Descartar** → `proposal set-status <plugin> <slug> discarded` y terminar ("Hotpatch descartado;
  la propuesta queda como registro").

---

## Step 5: Aplicar (solo si approved)

### 5a. Editar el repo target
Aplicar con `Edit` (cambios parciales) o `Write` (reescritura) sobre `$TARGET/<patch_target>`.
Es un repo distinto al cwd: usar la ruta absoluta `$TARGET/...`.

### 5b. Marcar el feedback aplicado
```bash
python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" feedback apply <plugin> <slug>
```
(Pone `applied: true` + `applied_at` en el store. El hook Stop deja de reportarlo.)

### 5c. Commit acotado (preguntar)
`AskUserQuestion`: "¿Commiteamos el hotpatch en el repo de `<plugin>`?" → "Sí" / "No".

Si sí — commitear **solo los archivos del patch** en el repo target, sin arrastrar otros
cambios sin commitear que pueda haber ahí:
```bash
git -C "$TARGET" add "<patch_target>"
git -C "$TARGET" commit -m "hotpatch(<componente>): <descripción breve>"
```

### 5d. Confirmar
```
Hotpatch aplicado ✓
  Plugin:    <plugin>
  Archivo:   <patch_target>   (en <local_path>)
  Efecto:    inmediato | próxima sesión
  Propuesta: <plugin>/<slug> (approved)
  Feedback:  marcado applied
```
Si el efecto es "próxima sesión": recordar que el plugin target debe reinstalarse/actualizarse
para que la copia corriendo tome el cambio.
