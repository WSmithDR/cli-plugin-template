# Plan — feedbacks pendientes de cli-plugin-template

7 pendientes en el store (`cpt feedback list --pending`). Uno ya está resuelto en el
código y solo hay que cerrarlo; uno no es un patch sino una feature con spec propio.
Quedan **4 patches reales + 1 cierre + 1 feature diferida**.

---

## F0 — Cierre sin trabajo: `plugin-version-se-lee-del-activo-no-del`

Ya aplicado el 2026-08-22: `skills/plugin-feedback-log/SKILL.md` Step 2 documenta de
dónde sale `plugin_version` (base directory / `CLAUDE_PLUGIN_ROOT`, nunca del cache) y
el campo `plugin_path` para `--plugin-dir`.

```bash
cpt feedback apply cli-plugin-template plugin-version-se-lee-del-activo-no-del
```

---

## F1 — `catalog-guard` bloquea `src/features/` de apps que no son plugins  ⚠️ P0

**Por qué primero:** hoy vuelve inusable Write/Edit/Read en cualquier repo con
`src/features/` (pasó en eminat-app). Es el único pendiente que rompe trabajo ajeno.

**Causa:** `FEATURES_RE = (^|/)features/([^/]+)/` matchea cualquier segmento del path.

**Fix:** exigir que el feature viva en el repo del catálogo. Ya existe el sentinel:
subir desde `feat_dir` buscando `.catalog-root`; si no aparece, no aplicar la regla 1.

- `bin/hooks/catalog-guard.py` — gate en `violations()`, antes del chequeo de `meta.yml`.
- `.opencode/lib/catalog-guard.ts` — espejo 1-a-1 (el .ts documenta paridad).
- Test en `bin/test-catalog-hooks.sh`: caso `src/features/x/y.ts` sin `.catalog-root` → allow;
  caso `features/x/y.md` bajo `.catalog-root` sin meta.yml → block (regresión).

La regla 2 (SKILL.md con scripts embebidos) no se toca: aplica a cualquier plugin.

---

## F2 — `portability-audit` escanea archivos gitignoreados  P1

Falsos CRITICAL en `.claude/settings.local.json` (rutas absolutas que Claude Code
auto-agrega) bloquean el pre-commit. Workaround actual: `.portabilityignore`.

**Fix:** en `walk()` (`features/portability-audit/files/audit-portability.py:138`),
saltar lo que git ignora — `git check-ignore --stdin` por lote, fallback silencioso si
no hay git. `.portabilityignore` sigue vivo para exclusiones extra.

Bump del feature en `features/portability-audit/meta.yml` (patch). Espejar en la copia
viva del repo si difiere del archivo del catálogo.

---

## F3 — `FRICTION_KEYWORDS` no cubre cómo se queja el usuario de verdad  P1

Una sesión entera con cuatro correcciones no disparó el Stop hook: los keywords son
literales ("no funciona", "está mal", "no me gusta").

**Fix:** en `bin/hooks/detect-pending-feedback.py:24`, pasar de tupla de literales a
heurística regex barata (sin LLM — el análisis fino sigue siendo del subagente):

- imperativos de re-trabajo: `corregí|corrige|corregilo`, `rehacé|rehazlo|rehacelo`,
  `cambiá|cambialo`, `arreglá|arreglalo`, `de nuevo`, `otra vez`
- juicios blandos: `le falta`, `no está bien`, `quedó raro`, `no cuadra`, `incoherente`
- variantes sin tilde de todas

Mantener `friction_lexicon()` del store combinándose igual. Casos nuevos en
`bin/test-detect-feedback.sh` con las frases textuales del feedback.

---

## F4 — Step 6 pide permiso antes de registrar fricción  P1 · trivial

`skills/plugin-feedback-log/SKILL.md` Step 6 instruye preguntar antes de guardar. El
usuario lo corrigió: registrar en el acto y avisar.

**Fix:** reemplazar los dos "→ Preguntá: …" por registrar directo + una línea de aviso
(`slug + signal`). Dejar la pregunta solo para el caso dudoso (no está claro si la
fricción es del plugin o del usuario). Principio a dejar escrito: *se pide permiso para
cambiar código, no para tomar nota* — el gate ya está en `plugin-hotpatch`.

---

## F5 — Registrar un plugin desde cualquier cwd  P2

La fricción con un plugin aparece usándolo en otro proyecto, y ahí `plugin-register`
no sirve: da de alta el plugin **del repo actual**. Resultado: el hallazgo se pierde.

**Desvío deliberado del feedback:** su `patch_target` dice `commands/plugin-register.md`,
pero este repo **no tiene `commands/`** a propósito (decisión de no chocar con comandos
nativos de Claude Code). Lo implemento como argumento de la skill existente, no como
slash command.

- `skills/plugin-register/SKILL.md`: Step 1 acepta un target explícito (nombre o ruta).
  Resolución en cascada: argumento → `installPath` del plugin instalado → preguntar.
  Sin argumento, el comportamiento actual (cwd) queda igual.
- `skills/plugin-register/scripts/gather-plugin-metadata.sh`: aceptar la ruta por
  parámetro en vez de asumir cwd.
- `skills/plugin-feedback-log/SKILL.md` Step 1: cuando el resolve por namespace falla,
  ofrecer el alta en el acto en vez de terminar — el usuario ya está describiendo la
  fricción, es el peor momento para mandarlo a otro repo.
- Test en `bin/test-cpt-registry.sh`: alta desde un cwd que no es el repo del plugin.

---

## F6 — Loop de aprendizajes vivos por plugin  ▸ diferido, spec propio

`needs_patch: false`. Es una feature completa: `cpt learning save/list/update/delete`
(colección `<data_dir>/<plugin>/learnings/`, upsert por tema — no es el store de
feedbacks, que tiene ciclo lineal), más dos hooks nuevos (`learning-nudge.py` en
PreToolUse, `detect-learning.py` en PostToolUse) y extender `test-failure-nudge.py` y
`detect-pending-feedback.py`.

**No entra en esta pasada.** El brainstorming ya está hecho (24/08); lo que falta es
plan propio. Queda como el próximo bloque de trabajo cuando F1–F5 estén cerrados.

---

## Orden y cierre

1. F0 (cierre) → 2. F1 (P0, desbloquea otros repos) → 3. F2 + F3 + F4 (P1) → 4. F5 (P2).

Por cada uno: patch → suite (`bin/test-*.sh` del área) → commit → `cpt feedback apply`.
El pre-commit bumpea versión solo; no tocar manifiestos a mano.

---

## Lotes de ejecución (paralelismo por conflicto de archivos)

El criterio es uno solo: **dos ítems pueden ir en paralelo si no tocan el mismo archivo.**

| Ítem | Archivos que toca |
|---|---|
| F0 | ninguno (solo el store) |
| F1 | `bin/hooks/catalog-guard.py`, `.opencode/lib/catalog-guard.ts`, `bin/test-catalog-hooks.sh` |
| F2 | `features/portability-audit/files/audit-portability.py`, `features/portability-audit/meta.yml` |
| F3 | `bin/hooks/detect-pending-feedback.py`, `bin/test-detect-feedback.sh` |
| F4 | `skills/plugin-feedback-log/SKILL.md` (Step 6) |
| F5 | `skills/plugin-register/SKILL.md`, `skills/plugin-register/scripts/gather-plugin-metadata.sh`, `skills/plugin-feedback-log/SKILL.md` (Step 1), `bin/test-cpt-registry.sh` |

Único solapamiento: **F4 y F5 comparten `plugin-feedback-log/SKILL.md`** (Steps 6 y 1).
Van juntos, en serie, dentro del mismo lote.

### Lote 0 — inline, 1 comando
`cpt feedback apply cli-plugin-template plugin-version-se-lee-del-activo-no-del`

### Lote 1 — 3 en paralelo (código de hooks y audit, sets disjuntos)
- **F1** catalog-guard scopeado a `.catalog-root` (P0) + espejo `.ts` + tests
- **F2** portability-audit saltea gitignoreados + bump de meta.yml
- **F3** FRICTION_KEYWORDS → regex + tests

Sin worktrees: los tres escriben en archivos distintos del mismo árbol. Cada uno corre
su propia suite (`test-catalog-hooks.sh`, `test-hooks.sh`, `test-detect-feedback.sh`).

### Lote 2 — 1 solo, después del lote 1
- **F4 → F5** en ese orden, ambos sobre `plugin-feedback-log/SKILL.md`.

F5 depende de F4 solo por el archivo, no por la lógica; hacer F4 primero (es un
reemplazo de dos párrafos) deja el archivo estable para el cambio más grande de F5.

### Serialización obligatoria: los commits
El pre-commit bumpea versión y valida el catálogo, así que **los commits van uno por
vez** aunque los patches se hayan hecho en paralelo. Secuencia real:

```
F0 (apply)  →  [F1 ‖ F2 ‖ F3]  →  suite completa  →  commit F1, commit F2, commit F3
            →  F4 → F5  →  suite completa  →  commit F4, commit F5
            →  cpt feedback apply × 5
```

Camino crítico: F1 (el más largo del lote 1) + F5. Los otros tres salen gratis en
tiempo de pared.

### F6 fuera de todo lote
Feature con spec propio; no comparte archivos con nadie, pero tampoco es un patch.
Después de cerrar F1–F5.
