# P2 — plugin-hotpatch: parcheo cross-repo asistido

## Contexto

El meta-plugin ya captura fricción (P0+P1): `plugin-feedback-log` escribe feedbacks con
`applied:false` en el store externo (`<plugin>/feedbacks/`), y el hook Stop
`detect-pending-feedback` avisa cuando hay pendientes, apuntando a `plugin-hotpatch`. Pero
ese motor de **procesamiento** todavía no existe — el hook apunta a una skill ausente.

P2 construye ese motor: el meta-plugin lee un feedback pendiente, propone un fix, lo pasa por
un gate de aprobación humana, y lo aplica **en el repo del plugin target** (aunque no estés
ahí), commiteando de forma acotada. Es la materialización del modelo central que el usuario
eligió: el meta-plugin administra la evolución; cada plugin no necesita su propio motor.

Dos barandas (decididas en P0): **registry-allowlist** (solo se tocan plugins dados de alta) y
**gate de aprobación humana** antes de cada patch.

## Decisiones de diseño (acordadas)

- **Ruteo (Step 3): híbrido.** `patch_target` del feedback → scan estructural genérico →
  component-map opcional si el plugin lo tiene.
- **Gate: propuesta persistida.** Antes de aplicar, se escribe `<plugin>/proposals/<slug>.md`
  con `status: pending|approved|discarded` (materializa el feature `proposal-gate`).
- **Commit: preguntar y commitear solo lo parcheado** en el repo target (`git -C <local_path>`).

## Flujo de la skill `plugin-hotpatch`

- **Step 0 · Pendientes** — `cpt feedback list --pending` (cross-plugin). Si el hook señaló uno,
  tomarlo; si hay varios, `AskUserQuestion` cuál procesar.
- **Step 1 · Resolver target (baranda 1)** — leer `plugin` del feedback → `registry_get(plugin)`
  → `local_path`. Si el plugin no está en el registry → abortar ("registralo primero"). Verificar
  que el repo existe en `local_path`.
- **Step 2 · Leer feedback** — `cpt feedback show <plugin> <slug>`; parsear frontmatter
  (`description`, `signal`, `patch_target`, `skill_namespace`).
- **Step 3 · Localizar el archivo (híbrido)**:
  1. `patch_target` presente → `<local_path>/<patch_target>`.
  2. si no → scan estructural: keywords del gap en `<local_path>/{skills,hooks,bin,config,commands}`.
  3. si existe `<local_path>/.plugin-meta/component-map.md` (opcional, opt-in) → usarlo para desempatar.
  4. ambiguo → listar candidatos + `AskUserQuestion`.
- **Step 4 · Propuesta persistida (baranda 2)** — `cpt proposal save <plugin> <slug>` con
  frontmatter `status: pending`, `patch_target`, `effect`, `gap`, y el `before`/`after` en el
  cuerpo. Mostrar preview en chat + `AskUserQuestion` Sí/Editar/Descartar →
  `cpt proposal set-status` a `approved` o `discarded`. `Editar` reescribe la propuesta y repite.
- **Step 5 · Aplicar (solo si approved)** — `Edit`/`Write` sobre `<local_path>/<patch_target>`;
  `cpt feedback apply <plugin> <slug>` (marca `applied:true` + `applied_at`); `AskUserQuestion`
  commit → si sí, `git -C <local_path> add <archivos del patch>` + `commit -m "hotpatch(<comp>): …"`.
  Confirmar archivo, efecto y propuesta.

## Superficie nueva

**`bin/lib/gateway.py`:**
- `feedback_mark_applied(plugin, slug, applied_at=None)` — `applied: false`→`true` + `applied_at`.
- `proposal_save(plugin, slug, content)` / `proposal_load` / `proposal_list(plugin=None, status=None)`
  / `proposal_set_status(plugin, slug, status)` — análogas a `feedback_*`, en `<plugin>/proposals/`.

**`bin/cpt`:**
- `feedback show <plugin> <slug>`, `feedback apply <plugin> <slug> [--at DATE]`.
- `proposal save <plugin> <slug> [- | content]`, `proposal show`, `proposal list [--plugin] [--status]`,
  `proposal set-status <plugin> <slug> <status>`.

**`skills/plugin-hotpatch/SKILL.md`** — el flujo de arriba.

**Integración:** sumar `plugin-hotpatch` al router `plugin-dev` y al health-check (8 skills de
catálogo + health).

## Límites deliberados

- El patch toca el **working repo** del plugin (fuente de verdad). La copia *corriendo* (cache del
  marketplace) no lo refleja hasta reinstalar — caveat "próxima sesión", documentado en la skill.
- Los `status` (`pending/approved/discarded`) se documentan como constantes de la skill. El
  **vocabulary-guardian centralizado es P3** — no se incluye acá.
- Sin self-discovery del propio meta-plugin sobre el target más allá del scan estructural; el
  component-map opcional cubre los casos donde el scan no alcanza.

## Verificación

- `bin/test-cpt-proposal.sh` — `proposal save/show/list/set-status` + `feedback apply` (applied flip).
- Test cross-repo: crear un **repo git dummy** como target, registrarlo, resolver `local_path`,
  aplicar un patch trivial y verificar el commit acotado (`git -C` toca solo el archivo del patch).
- `validate-catalog.py` y `audit-portability.py` sin regresiones.
