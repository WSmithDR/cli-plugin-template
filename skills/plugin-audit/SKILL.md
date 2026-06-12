---
name: plugin-audit
description: Use when you want to check the current plugin project against the cli-plugin-template catalog — which catalog features are missing or look outdated, AND whether the plugin has portability/agnosticism problems (absolute paths, unrooted refs, CLI coupling, hardcoded secrets). Reports gaps and hygiene findings with how to fix each.
---

# plugin-audit — auditar el plugin

Auditá el proyecto actual (un plugin) en **dos dimensiones** y reportá. No modifiques
nada: solo reportás.

1. **Gap de catálogo** — qué features del catálogo faltan o están atrasados.
2. **Higiene de portabilidad y agnosticismo** — qué ata el plugin a una máquina o a un
   solo CLI (escalabilidad).

Empezá confirmando que la cwd es un proyecto de plugin: existe `.claude-plugin/plugin.json`.
Si no, decilo y salí.

## Parte A — Gap de catálogo

1. Leé el índice del catálogo: `cat "${CLAUDE_PLUGIN_ROOT}/CATALOG.md"`.
2. Para cada categoría relevante, chequeá señales en el proyecto y marcá faltante/presente:
   - **versioning**: ¿hay un git hook que bumpea versión? (buscar `bin/dev/git-hooks/post-commit` o similar)
   - **git-hooks**: ¿hay `bin/dev/setup.sh` + tests?
   - **health-check**: ¿hay una skill `*-health`?
   - **claude-code-hooks / advanced-hooks**: ¿hay `hooks/hooks.json`?
   - **docs-conventions**: ¿el README tiene secciones de install/update/versionado?
   - **multi-cli-compat**: ¿hay manifiestos para otros CLIs (gemini-extension.json, .codex-plugin, opencode.json)?
   - **project-config / health-check / data-gateway / etc.**: señales análogas.
3. Reportá una tabla: Feature | Estado (✓ presente / ✗ falta) | Cómo integrarlo (`/plugin-feature <x>`).

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

Sugerencia: primero el CRITICAL (no es portable), después versioning (alto valor, bajo costo).
```
