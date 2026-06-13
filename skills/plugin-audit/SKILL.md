---
name: plugin-audit
description: Use when you want to check the current plugin project against the cli-plugin-template catalog — which catalog features are missing or look outdated, whether the plugin has portability/agnosticism problems (absolute paths, unrooted refs, CLI coupling, hardcoded secrets), AND whether its skills are modularized (no scripts loose in the skill root, no script blocks embedded in SKILL.md). Reports gaps and hygiene findings with how to fix each.
---

# plugin-audit — auditar el plugin

Auditá el proyecto actual (un plugin) en **tres dimensiones** y reportá. No modifiques
nada: solo reportás.

1. **Gap de catálogo** — qué features del catálogo faltan o están atrasados.
2. **Higiene de portabilidad y agnosticismo** — qué ata el plugin a una máquina o a un
   solo CLI (escalabilidad).
3. **Estructura de skills** — si las skills están modularizadas (sin scripts sueltos en
   la raíz ni bloques de script embebidos en `SKILL.md`).

Empezá confirmando que la cwd es un proyecto de plugin: existe `.claude-plugin/plugin.json`.
Si no, decilo y salí.

## Parte A — Gap de catálogo

Lo determinista lo hace un script bundled (principio `bundled-scripts`): no
enumeres las señales por feature a ojo. Corré el detector sobre la cwd:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/bin/audit-catalog-gaps.py" .
```

Para cada feature detectable por señales de archivo marca de forma determinista:

| Estado | Significa |
|---|---|
| ✓ presente | la señal del feature aparece en el árbol |
| ✗ falta    | no aparece → candidato a integrar con `/plugin-feature <x>` |
| · n/d      | no es detectable con baja tasa de falsos positivos (requiere juicio) |

El script cubre: `versioning`, `git-hooks`, `health-check`, `claude-code-hooks`,
`docs-conventions`, `multi-cli-compat`, `externalized-config`,
`vocabulary-guardian`, `data-gateway`, `bundled-scripts`, `proposal-gate` y marca
`entry-point-router` como n/d. Sale con exit 0 siempre (es un reporte, no un gate);
soporta `--json`.

Interpretá la salida (no la repitas cruda):
- **✗ falta** = candidato a integrar. Priorizá por valor/costo: features de alto
  valor y bajo costo primero (p.ej. `versioning`, `docs-conventions`).
- **· n/d** = revisalo a mano si tiene sentido para el plugin; el script no lo
  afirma ni lo niega.
- Para features fuera del set detectable (los semánticos del catálogo), usá
  `cat "${CLAUDE_PLUGIN_ROOT}/CATALOG.md"` como referencia y tu juicio.

Reportá una tabla: Feature | Estado (✓ presente / ✗ falta / · n/d) | Cómo
integrarlo (`/plugin-feature <x>`), basada en lo que devolvió el script.

## Parte B — Higiene de portabilidad y agnosticismo

Lo determinista lo hace un script bundled (principio `bundled-scripts`): no enumeres ni
busques patrones a mano. Corré el escáner sobre la cwd:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/features/portability-audit/files/audit-portability.py" .
```

Detecta, por severidad:

| Severidad | Tipo | Qué significa |
|---|---|---|
| CRITICAL | `absolute-path` | ruta absoluta atada a una máquina (`/home/x`, `/Users/x`, `C:\…`) → solo anda en la máquina del autor |
| CRITICAL | `possible-secret` | credencial/clave hardcodeada en el repo |
| WARNING | `unrooted-ref` | skill/command que referencia un dir del plugin (`features/`, `bin/`…) sin `${CLAUDE_PLUGIN_ROOT}` → resuelve contra la cwd del usuario, no contra el plugin |
| WARNING | `claude-only-path` | path `.claude/…` hardcodeado → acopla a Claude Code |
| WARNING | `model-inherit` | `model: inherit` en frontmatter → rompe OpenCode y otros CLIs |
| INFO | `portable-shebang` | `python`/`python2` en vez de `python3` |

Interpretá la salida (no la repitas cruda):
- **CRITICAL** = bloquea publicar. Rutas absolutas y secretos hay que sacarlos sí o sí.
- **WARNING** = deuda de agnosticismo. Priorizá según si el plugin apunta a multi-CLI.
- **INFO** = pulido.

Para cada hallazgo, mapeá al feature que lo resuelve cuando aplique:
`unrooted-ref` y `claude-only-path`/`model-inherit` → `multi-cli-compat`;
`absolute-path`/`possible-secret` → fix directo (usar `${CLAUDE_PLUGIN_ROOT}`/`$HOME`/env vars);
`portable-shebang` → `hook-python-bootstrap`.

> El script sale con exit 1 si hay algún CRITICAL — si el plugin tiene `git-hooks`,
> sugerí engancharlo en pre-commit/CI para que no vuelva a colarse.

## Parte C — Estructura de skills (modularización)

Lo determinista lo hace un script bundled (principio `bundled-scripts`): no enumeres
las skills ni leas cada `SKILL.md` a mano. Corré el escáner sobre la cwd:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/features/skill-structure-audit/files/audit-skill-structure.py"
```

La regla: `SKILL.md` contiene solo instrucciones. La lógica va en `scripts/`, las
plantillas de datos en `references/`. Detecta, por severidad:

| Severidad | Tipo | Qué significa |
|---|---|---|
| ERROR | `script suelto` | `.sh`/`.py`/`.js`… en la raíz de la skill → debe ir a `scripts/` |
| ERROR | `bloque embebido` | bloque de script de **>2 líneas** en `SKILL.md` → lógica a `scripts/`, plantilla a `references/` |
| ERROR | `falta SKILL.md` | el dir de la skill no tiene `SKILL.md` |
| WARNING | `archivo suelto` | `.md`/`.json`/`.yml`… en la raíz de la skill → a `references/` o `files/` |

Interpretá la salida (no la repitas cruda):
- **ERROR** = viola la modularización. Bloquea el orden del plugin; mapeá al fix de la tabla.
- **WARNING** = deuda de orden (archivos sueltos que conviene reubicar).

Para cada hallazgo, el fix es mover el contenido al subdir correcto y dejar en `SKILL.md`
solo la invocación (≤2 líneas). El feature que lo resuelve y lo hace cumplir en CI es
`skill-structure-audit`.

> El script soporta `--threshold ERROR` (sale 1 solo ante ERROR) — si el plugin tiene
> `git-hooks`, sugerí engancharlo en pre-commit para que no vuelva a colarse.

## Salida sugerida

```
Auditoría de <plugin>:

A) Gap de catálogo
  ✓ git-hooks
  ✗ versioning      → /plugin-feature versioning
  ✗ health-check    → /plugin-feature health-check
  ✓ docs-conventions

B) Portabilidad y agnosticismo  (CRITICAL: 1  WARNING: 2  INFO: 0)
  ✗ absolute-path   bin/sync.sh:12  /home/alice/...   → usar ${CLAUDE_PLUGIN_ROOT}
  ⚠ unrooted-ref    skills/x/SKILL.md:8  cat features/…  → prefijar ${CLAUDE_PLUGIN_ROOT}/
  ⚠ model-inherit   agents/y.md:3                       → omitir `model:`  (multi-cli-compat)

C) Estructura de skills  (ERROR: 1  WARNING: 0)
  ✗ bloque embebido  skills/x/SKILL.md:24  bash de 19 líneas  → mover a scripts/

Sugerencia: primero el CRITICAL (no es portable), después el bloque embebido (skill-structure-audit), después versioning.
```
