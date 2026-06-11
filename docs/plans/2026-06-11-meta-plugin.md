# Meta-plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir el repo `cli-plugin-template` en un meta-plugin instalable que, en cualquier proyecto de plugin, entrega las pautas del catálogo (auditar, integrar, recomendar, promover) con un aviso proactivo único.

**Architecture:** El repo es a la vez catálogo y plugin. Un hook `SessionStart` (bash, testeado) detecta proyectos de plugin y avisa una vez. Cinco skills (un router + 4 capacidades) leen `${CLAUDE_PLUGIN_ROOT}/features/` localmente. Dogfooding de `entry-point-router`, `claude-code-hooks`, `project-config`, `health-check`.

**Tech Stack:** Bash (hook + tests con tmpdir aislado), Markdown (skills/commands/manifest JSON), Python3 (validación en CI).

**Trabajo en el repo:** `/home/wagner/Documentos/dev-projects/personal_tools/cli-plugin-template`. Todos los paths son relativos a esa raíz.

---

### Task 1: Manifest del plugin + sentinel de auto-referencia

**Files:**
- Create: `.catalog-root`
- Create: `.claude-plugin/plugin.json`

- [ ] **Step 1: Crear el sentinel de auto-referencia**

Create `.catalog-root` con este contenido:

```
Este archivo marca el repo del catálogo cli-plugin-template.
El hook SessionStart lo usa para NO tratar al catálogo como un plugin consumidor.
```

- [ ] **Step 2: Crear el manifest del plugin**

Create `.claude-plugin/plugin.json`:

```json
{
  "name": "cli-plugin-template",
  "version": "1.0.0",
  "description": "Meta-plugin de desarrollo de plugins multi-CLI. Cataloga 32 features reusables y los entrega on-demand (auditar, integrar, recomendar, promover) con un aviso proactivo en proyectos de plugin.",
  "author": { "name": "WSmithDR", "url": "https://github.com/WSmithDR" },
  "repository": "https://github.com/WSmithDR/cli-plugin-template",
  "license": "MIT",
  "keywords": ["plugin-development", "cli-plugin", "feature-catalog", "claude-code", "multi-cli"],
  "skills": "./skills/"
}
```

- [ ] **Step 3: Commit**

```bash
git add .catalog-root .claude-plugin/plugin.json
git commit -m "feat: make catalog an installable plugin (manifest + self-reference sentinel)"
```

---

### Task 2: Hook SessionStart + arnés de tests (TDD)

**Files:**
- Create: `bin/hooks/session-start.sh`
- Create: `hooks/hooks.json`
- Create: `bin/test-hooks.sh`

- [ ] **Step 1: Escribir el arnés de tests que falla**

Create `bin/test-hooks.sh`:

```bash
#!/bin/bash
# Tests del hook SessionStart del meta-plugin. Cada caso en un tmpdir aislado.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$SCRIPT_DIR/hooks/session-start.sh"
PASS=0; FAIL=0
_pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
_fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

run_in_tmpdir() {
    local dir; dir=$(mktemp -d)
    (cd "$dir" && eval "$1"); local rc=$?
    rm -rf "$dir"; return $rc
}

echo ""
echo "=== session-start.sh ==="

# Caso 1: repo del catálogo (.catalog-root) → exit 0, sin output
result=$(run_in_tmpdir '
    touch .catalog-root
    out=$(bash '"$HOOK"' 2>&1); rc=$?
    [ $rc -eq 0 ] && [ -z "$out" ] && echo OK || echo "rc=$rc out=$out"
')
[ "$result" = "OK" ] && _pass ".catalog-root → exit 0 silencioso" || _fail ".catalog-root → $result"

# Caso 2: no es proyecto de plugin → exit 0, sin output
result=$(run_in_tmpdir '
    out=$(bash '"$HOOK"' 2>&1); rc=$?
    [ $rc -eq 0 ] && [ -z "$out" ] && echo OK || echo "rc=$rc out=$out"
')
[ "$result" = "OK" ] && _pass "sin .claude-plugin/ → exit 0 silencioso" || _fail "sin .claude-plugin/ → $result"

# Caso 3: proyecto de plugin, primera vez → avisa + crea marcador
result=$(run_in_tmpdir '
    git init -q; mkdir -p .claude-plugin
    out=$(bash '"$HOOK"' 2>&1); rc=$?
    marker="$(git rev-parse --git-dir)/cli-plugin-template.seen"
    [ $rc -eq 0 ] && echo "$out" | grep -q "CLI-PLUGIN-TEMPLATE" && [ -f "$marker" ] && echo OK || echo "rc=$rc out=$out"
')
[ "$result" = "OK" ] && _pass "plugin nuevo → avisa + marcador" || _fail "plugin nuevo → $result"

# Caso 4: segunda vez (marcador presente) → sin output
result=$(run_in_tmpdir '
    git init -q; mkdir -p .claude-plugin
    bash '"$HOOK"' >/dev/null 2>&1
    out=$(bash '"$HOOK"' 2>&1); rc=$?
    [ $rc -eq 0 ] && [ -z "$out" ] && echo OK || echo "rc=$rc out=$out"
')
[ "$result" = "OK" ] && _pass "segunda sesión → sin aviso" || _fail "segunda sesión → $result"

echo ""
echo "Resultado: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ] && exit 0 || exit 1
```

- [ ] **Step 2: Correr el arnés para verificar que falla**

Run: `chmod +x bin/test-hooks.sh && bash bin/test-hooks.sh`
Expected: FAIL — el hook `bin/hooks/session-start.sh` no existe todavía.

- [ ] **Step 3: Escribir el hook**

Create `bin/hooks/session-start.sh`:

```bash
#!/bin/bash
# SessionStart: en un proyecto de plugin (no el catálogo), sugiere una auditoría
# del catálogo — una sola vez por proyecto. Informativo (exit 0), no bloquea.
set -euo pipefail

# Guard de auto-referencia: el catálogo lleva .catalog-root
[ -f ".catalog-root" ] && exit 0

# Solo en proyectos de plugin
[ -d ".claude-plugin" ] || exit 0

# Marcador "ya avisado" en .git (no se commitea); fallback si no hay git
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null || echo "")
if [ -n "$GIT_DIR" ]; then
    MARKER="$GIT_DIR/cli-plugin-template.seen"
else
    MARKER=".claude-plugin/.cli-template-seen"
fi
[ -f "$MARKER" ] && exit 0
touch "$MARKER"

echo "CLI-PLUGIN-TEMPLATE: Esto parece un proyecto de plugin.
El catálogo cli-plugin-template está instalado — corré /plugin-audit para ver qué features te faltan, o /plugin para el menú de capacidades."
exit 0
```

- [ ] **Step 4: Crear hooks.json**

Create `hooks/hooks.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/bin/hooks/session-start.sh"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 5: Correr el arnés y verificar que pasa**

Run: `chmod +x bin/hooks/session-start.sh && bash bin/test-hooks.sh`
Expected: PASS — 4 passed, 0 failed.

- [ ] **Step 6: Commit**

```bash
git add bin/hooks/session-start.sh hooks/hooks.json bin/test-hooks.sh
git commit -m "feat: SessionStart hook that gently suggests a catalog audit (once per project)"
```

---

### Task 3: Skill router `plugin-dev`

**Files:**
- Create: `skills/plugin-dev/SKILL.md`

- [ ] **Step 1: Escribir el SKILL.md del router**

Create `skills/plugin-dev/SKILL.md`:

```markdown
---
name: plugin-dev
description: Use when developing a Claude Code or multi-CLI plugin and you want guidance from the cli-plugin-template catalog — to audit the plugin, integrate a feature, find which feature solves a need, or promote an improvement back. Entry point; routes to the right capability.
---

# plugin-dev — router del catálogo

Punto de entrada único para las pautas del catálogo. Elegí la capacidad según la intención
del usuario; NO invoques las sub-skills directamente como respuesta — pasá por acá.

## Routing

| Intención del usuario | Skill |
|---|---|
| "¿qué me falta?", "revisá mi plugin", "está bien armado?" | `plugin-audit` |
| "integrá <feature>", "agregá versionado/hooks/health-check" | `plugin-feature` |
| "quiero X", "cómo hago que mis skills se disparen", "necesito Y" | `plugin-recommend` |
| "esto sirve para todos", "subí esto al catálogo" | `plugin-promote` |

Si la intención es ambigua, preguntá con una opción corta antes de enrutar.

## Contexto

El catálogo vive en `${CLAUDE_PLUGIN_ROOT}/features/`. Cada feature tiene `README.md`
(qué/por qué/cómo) + `files/` (esqueletos) + `meta.yml` (version, cli_compat, depends_on).
El índice es `${CLAUDE_PLUGIN_ROOT}/CATALOG.md`.
```

- [ ] **Step 2: Verificar el frontmatter**

Run:
```bash
python3 -c "import sys; t=open('skills/plugin-dev/SKILL.md').read(); assert t.startswith('---'); fm=t.split('---')[1]; assert 'name: plugin-dev' in fm and 'description:' in fm and 'Use when' in fm; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add skills/plugin-dev/SKILL.md
git commit -m "feat: plugin-dev router skill (entry point to catalog guidance)"
```

---

### Task 4: Skill `plugin-audit`

**Files:**
- Create: `skills/plugin-audit/SKILL.md`

- [ ] **Step 1: Escribir el SKILL.md**

Create `skills/plugin-audit/SKILL.md`:

```markdown
---
name: plugin-audit
description: Use when you want to check the current plugin project against the cli-plugin-template catalog — which catalog features are missing or look outdated. Reports gaps with the feature that fills each one.
---

# plugin-audit — auditar el plugin vs catálogo

Compara el proyecto actual (un plugin) contra el catálogo y reporta gaps.

## Proceso

1. Confirmá que la cwd es un proyecto de plugin: existe `.claude-plugin/plugin.json`.
   Si no, decilo y salí.
2. Leé el índice del catálogo: `cat "${CLAUDE_PLUGIN_ROOT}/CATALOG.md"`.
3. Para cada categoría relevante, chequeá señales en el proyecto y marcá faltante/presente:
   - **versioning**: ¿hay un git hook que bumpea versión? (buscar `bin/dev/git-hooks/post-commit` o similar)
   - **git-hooks**: ¿hay `bin/dev/setup.sh` + tests?
   - **health-check**: ¿hay una skill `*-health`?
   - **claude-code-hooks / advanced-hooks**: ¿hay `hooks/hooks.json`?
   - **docs-conventions**: ¿el README tiene secciones de install/update/versionado?
   - **multi-cli-compat**: ¿hay manifiestos para otros CLIs (gemini-extension.json, .codex-plugin, opencode.json)?
   - **project-config / health-check / data-gateway / etc.**: señales análogas.
4. Reportá una tabla: Feature | Estado (✓ presente / ✗ falta) | Cómo integrarlo (`/plugin-feature <x>`).
5. No modifiques nada. Solo reportás.

## Salida sugerida

```
Auditoría de <plugin> vs catálogo:
  ✓ git-hooks
  ✗ versioning      → /plugin-feature versioning
  ✗ health-check    → /plugin-feature health-check
  ✓ docs-conventions
Sugerencia: empezá por versioning (alto valor, bajo costo).
```
```

- [ ] **Step 2: Verificar el frontmatter**

Run:
```bash
python3 -c "t=open('skills/plugin-audit/SKILL.md').read(); fm=t.split('---')[1]; assert 'name: plugin-audit' in fm and 'Use when' in fm; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add skills/plugin-audit/SKILL.md
git commit -m "feat: plugin-audit skill (report missing/outdated catalog features)"
```

---

### Task 5: Skill `plugin-feature`

**Files:**
- Create: `skills/plugin-feature/SKILL.md`

- [ ] **Step 1: Escribir el SKILL.md**

Create `skills/plugin-feature/SKILL.md`:

```markdown
---
name: plugin-feature
description: Use when you want to integrate a specific cli-plugin-template feature into the current plugin (e.g. "add versioning", "integrate health-check"). Reads the feature's README and adapts its files to this project.
---

# plugin-feature — integrar un feature del catálogo

Integra un feature nombrado en el plugin actual, adaptándolo (no copiando a ciegas).

## Proceso

1. Resolvé el nombre del feature. Si es ambiguo, listá coincidencias de
   `${CLAUDE_PLUGIN_ROOT}/CATALOG.md` y preguntá.
2. Verificá dependencias: leé `${CLAUDE_PLUGIN_ROOT}/features/<x>/meta.yml` → `depends_on`.
   Si falta una dependencia en el proyecto, avisá y ofrecé integrarla primero.
3. Leé `${CLAUDE_PLUGIN_ROOT}/features/<x>/README.md` — seguí su sección **Integración**.
4. Copiá/adaptá los archivos de `${CLAUDE_PLUGIN_ROOT}/features/<x>/files/` al proyecto,
   ajustando: rutas, nombre del plugin, idioma, datadir. NO pegues placeholders sin reemplazar.
5. Corré los pasos de verificación que el README indique (`## Tests`).
6. Resumí qué se agregó y qué quedó por ajustar a mano.

## Reglas

- Respetá las convenciones existentes del proyecto (no reestructures de más).
- Si el feature ya está parcialmente presente, integrá solo lo que falta.
- No commitees por el usuario salvo que lo pida explícitamente.
```

- [ ] **Step 2: Verificar el frontmatter**

Run:
```bash
python3 -c "t=open('skills/plugin-feature/SKILL.md').read(); fm=t.split('---')[1]; assert 'name: plugin-feature' in fm and 'Use when' in fm; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add skills/plugin-feature/SKILL.md
git commit -m "feat: plugin-feature skill (integrate a named catalog feature)"
```

---

### Task 6: Skill `plugin-recommend`

**Files:**
- Create: `skills/plugin-recommend/SKILL.md`

- [ ] **Step 1: Escribir el SKILL.md**

Create `skills/plugin-recommend/SKILL.md`:

```markdown
---
name: plugin-recommend
description: Use when you describe a need for your plugin in plain language (e.g. "I want automatic versioning", "make my skills trigger reliably", "review changes for bugs") and want the catalog feature(s) that solve it.
---

# plugin-recommend — recomendar feature por necesidad

Matchea una necesidad en lenguaje natural contra el catálogo y sugiere el/los feature(s).

## Proceso

1. Leé `${CLAUDE_PLUGIN_ROOT}/CATALOG.md` (índice con descripciones por categoría).
2. Matcheá la necesidad del usuario contra las descripciones. Ejemplos:
   - "versionado automático" → `versioning`
   - "que mis skills se disparen" → `skill-authoring` (+ `skill-evals`)
   - "revisar cambios por bugs" → `dual-review`
   - "compatibilidad con otros CLIs" → `multi-cli-compat`
   - "memoria entre sesiones" → `session-memory`
3. Sugerí 1–3 features, citando una línea del README de cada uno (por qué resuelve la necesidad).
4. Ofrecé integrarlo: "corré `/plugin-feature <x>` o decime y lo integro".
5. Si no hay match claro, decilo y sugerí promover un feature nuevo (`plugin-promote`).
```

- [ ] **Step 2: Verificar el frontmatter**

Run:
```bash
python3 -c "t=open('skills/plugin-recommend/SKILL.md').read(); fm=t.split('---')[1]; assert 'name: plugin-recommend' in fm and 'Use when' in fm; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add skills/plugin-recommend/SKILL.md
git commit -m "feat: plugin-recommend skill (suggest features from a plain-language need)"
```

---

### Task 7: Skill `plugin-promote`

**Files:**
- Create: `skills/plugin-promote/SKILL.md`

- [ ] **Step 1: Escribir el SKILL.md**

Create `skills/plugin-promote/SKILL.md`:

```markdown
---
name: plugin-promote
description: Use when an improvement born in the current plugin is reusable for any plugin and should go back to the cli-plugin-template catalog. Creates features/<name>/ in the catalog working tree following CONTRIBUTING.md — does NOT commit.
---

# plugin-promote — promover una mejora al catálogo

Sube una mejora reusable al catálogo. **Deja todo en working tree del catálogo, sin commitear.**

## Proceso

1. Confirmá que la mejora es reusable para CUALQUIER plugin (no lógica de dominio del
   plugin actual). Si es específica, no va al catálogo.
2. Leé `${CLAUDE_PLUGIN_ROOT}/CONTRIBUTING.md` y seguí su estructura.
3. Creá en el catálogo `${CLAUDE_PLUGIN_ROOT}/features/<nombre>/`:
   - `README.md` con: Qué hace · Por qué · Integración · Tests · Changelog.
   - `files/` con los esqueletos reusables (si aplica).
   - `meta.yml` con `name`, `version: 1.0.0`, `cli_compat`, `depends_on`, `description`.
4. Agregá la fila en `${CLAUDE_PLUGIN_ROOT}/CATALOG.md`.
5. Corré la validación: `python3 "${CLAUDE_PLUGIN_ROOT}/bin/validate-catalog.py"`.
6. **No commitees.** Avisá al usuario que revise el working tree del catálogo y commitee él.

## Reglas

- El `name` de `meta.yml` debe coincidir con el nombre de la carpeta (lo valida el CI).
- Cada feature listado en CATALOG.md debe existir, y viceversa (lo valida el CI).
```

- [ ] **Step 2: Verificar el frontmatter**

Run:
```bash
python3 -c "t=open('skills/plugin-promote/SKILL.md').read(); fm=t.split('---')[1]; assert 'name: plugin-promote' in fm and 'Use when' in fm; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add skills/plugin-promote/SKILL.md
git commit -m "feat: plugin-promote skill (promote a reusable improvement to the catalog)"
```

---

### Task 8: Comando atajo `/plugin`

**Files:**
- Create: `commands/plugin.md`

- [ ] **Step 1: Escribir el comando**

Create `commands/plugin.md`:

```markdown
---
description: Pautas del catálogo cli-plugin-template para el plugin actual (auditar, integrar, recomendar, promover).
---

Invocá la skill `plugin-dev` para enrutar a la capacidad correcta según lo que pida el usuario en los argumentos: $ARGUMENTS

Si no hay argumentos, ofrecé el menú: auditar el plugin (`plugin-audit`), integrar un feature (`plugin-feature`), recomendar por necesidad (`plugin-recommend`), o promover una mejora (`plugin-promote`).
```

- [ ] **Step 2: Verificar el frontmatter**

Run:
```bash
python3 -c "t=open('commands/plugin.md').read(); assert t.startswith('---') and 'description:' in t.split('---')[1]; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add commands/plugin.md
git commit -m "feat: /plugin command (shortcut to the plugin-dev router)"
```

---

### Task 9: CI para el hook + actualizar docs

**Files:**
- Modify: `.github/workflows/validate.yml`
- Modify: `README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Agregar el job de tests del hook al workflow**

En `.github/workflows/validate.yml`, dentro de `steps:` del job `validate`, agregá al final (después del paso de JSON):

```yaml
      - name: Run meta-plugin hook tests
        run: bash bin/test-hooks.sh
```

- [ ] **Step 2: Verificar que los tests del hook pasan localmente**

Run: `bash bin/test-hooks.sh`
Expected: PASS — 4 passed, 0 failed.

- [ ] **Step 3: Documentar el uso como plugin en el README**

En `README.md`, después de la sección "Cómo se usa", agregá:

```markdown
## Como plugin instalable

Además de consultarse como repo, el catálogo se instala como plugin de desarrollo:

\```bash
claude plugin install cli-plugin-template@cli-plugin-template --scope project
\```

Una vez instalado en un proyecto de plugin:
- **`/plugin`** — menú de capacidades (router `plugin-dev`).
- **`/plugin-audit`** — qué features del catálogo te faltan.
- **`/plugin-feature <nombre>`** — integrar un feature.
- **`/plugin-recommend`** — sugerir features desde una necesidad.
- **`/plugin-promote`** — subir una mejora al catálogo.

Al abrir un proyecto de plugin por primera vez, un aviso sugiere correr `/plugin-audit`.
```

- [ ] **Step 4: Documentar el modo plugin en AGENTS.md**

En `AGENTS.md`, agregá al final:

```markdown
## Modo plugin

Este repo también es un plugin instalable (`.claude-plugin/plugin.json`). Instalado en
otro proyecto, expone las skills `plugin-dev` (router), `plugin-audit`, `plugin-feature`,
`plugin-recommend`, `plugin-promote` y el comando `/plugin`, que leen el catálogo de
`features/` localmente. El hook `SessionStart` sugiere una auditoría la primera vez en un
proyecto de plugin. El propio repo se excluye con el sentinel `.catalog-root`.
```

- [ ] **Step 5: Validar todo y commit**

Run:
```bash
python3 bin/validate-catalog.py && bash bin/test-hooks.sh
```
Expected: catálogo válido + 4 passed.

```bash
git add .github/workflows/validate.yml README.md AGENTS.md
git commit -m "ci+docs: run hook tests in CI; document the installable plugin mode"
```

---

## Notas de ejecución

- El repo tiene branch protection en `main` exigiendo el check `validate`; los commits van
  directo a `main` (el owner puede pushear, enforce_admins=false). Pushear al final de cada
  task o al cierre, según preferencia.
- Las skills son contenido (markdown), no código testeable por TDD; su verificación es
  estructural (frontmatter válido). El único componente con TDD real es el hook (Task 2).
- `CLAUDE.md` es symlink a `AGENTS.md`, así que el Step 4 de Task 9 cubre ambos.
