# Feature: multi-cli-compat

## Qué hace

Hace que el mismo plugin funcione en varios CLIs —Claude Code, Gemini CLI, OpenCode,
Codex, Cursor, GitHub Copilot— declarando el manifiesto que cada uno espera, traduciendo
los nombres de tools entre plataformas, y compartiendo una sola definición de skills/MCP.

## Por qué

Un plugin atado a un solo CLI se queda fuera del ecosistema. Pero cada CLI lee un
manifiesto distinto, **llama a las tools con nombres distintos** (`Read` en Claude Code es
`read_file` en Gemini, `view` en Copilot) y descubre skills de forma distinta. Sin
resolver esto, el plugin "funciona" solo en Claude Code aunque copies el `.mcp.json`.

## Las tres estrategias (elegí según tu plugin)

| Estrategia | Cuándo | Esfuerzo | Ejemplo real |
|---|---|---|---|
| **A. MCP wrapper** | El plugin ES un MCP server | Mínimo | context7 |
| **B. Skills agnósticas** | Skills que no nombran tools (usan bash/python) | Medio | understand-anything |
| **C. Skills con tool-mapping** | Skills que referencian tools específicas | Alto | superpowers |

## Cuál elegir

No compiten — se combinan por componente. La mayoría de los plugins reales mezclan **A + B**.

```
¿Tu funcionalidad es un MCP server?     → A  (y listo para esa parte)
¿Tenés skills?                          → B  por default
¿Una skill DEBE nombrar tools exactas?  → C  solo para esa skill
```

- **B es el mejor default** para plugins basados en skills: las skills se escriben en
  lenguaje neutral (instruís vía `bash`/`python`/`node`, no "usá el tool `Read`"), así que
  no hay tabla de mapeo que mantener. Disciplina: describí el *qué* ("editá `archivo.py`"),
  no el *cómo con qué tool* ("usá Edit").
- **A es imbatible en simplicidad** pero solo cubre la parte MCP. Un plugin con MCPs +
  skills usa A para los servers y B para las skills.
- **C es el más potente pero el de mayor mantenimiento** (tablas de mapeo + inyección por
  CLI). Reservalo para skills que no pueden evitar nombrar tools específicas.

> **Error a evitar**: saltar directo a C porque "es el más completo". Es el más caro de
> mantener y casi siempre lo evitás escribiendo las skills en lenguaje neutral (B).

### A. MCP wrapper — un solo archivo universal

El MCP protocol es agnóstico de CLI: **el mismo `.mcp.json` lo levanta cualquier CLI que
implemente MCP**. No hay manifiestos por CLI; la compatibilidad depende del CLI, no del plugin.

```json
{ "<srv>": { "command": "npx", "args": ["-y", "@scope/paquete-mcp"] } }
```
Ver feature `mcp-npx-wrapper`. Es el camino más simple si tu plugin expone un MCP.

### B. Skills agnósticas — sin mapeo, lenguaje universal

Si las skills están escritas en **lenguaje neutral** (instruyen vía `bash`, `python`,
`node` — no "usá el tool Read"), no necesitás traducir tools. Cada CLI las descubre por
su cuenta. Requiere:
- Manifiestos por CLI (ver matriz abajo).
- Un instalador que symlinkea las skills al dir de cada CLI (ver `install-skills.sh`).
- **Omitir el campo `model:`** en el frontmatter de agents — `inherit` es exclusivo de
  Claude Code y rompe OpenCode (`ProviderModelNotFoundError`). Sin `model:`, cada CLI usa
  su default.

### C. Skills con tool-mapping — traducción explícita

Si las skills **sí** nombran tools de Claude Code (`Read`, `Edit`, `Skill`, `Task`), tenés
que dar la tabla de equivalencias por CLI. Ver `files/tool-mapping.md`. Cada CLI la recibe
distinto (ver "Inyección" abajo).

## Matriz de manifiestos por CLI

| CLI | Manifiesto | ¿Skills path explícito? | Archivo de instrucciones |
|---|---|---|---|
| Claude Code | `.claude-plugin/plugin.json` | No (auto-discovery) | `CLAUDE.md` |
| Cursor | `.cursor-plugin/plugin.json` | Sí (`skills`/`agents`) | — |
| GitHub Copilot | `.copilot-plugin/plugin.json` | Sí | `AGENTS.md` |
| Codex | `.codex-plugin/plugin.json` | Sí (`skills`) | `AGENTS.md` |
| Gemini CLI | `gemini-extension.json` (`contextFileName`) | vía context file | `GEMINI.md` |
| OpenCode | `opencode.json` + `.opencode/plugins/<x>.js` | vía hook JS | `AGENTS.md` |
| Cualquiera (MCP) | `.mcp.json` | n/a | — |

## Patrón de archivos de instrucciones

`AGENTS.md` es el **estándar de facto** que varios CLIs leen. El resto enlaza a él:

```bash
ln -sf AGENTS.md CLAUDE.md     # Claude Code
# GEMINI.md NO es symlink: usa @-includes y se declara en gemini-extension.json
```

`GEMINI.md` apunta a recursos que Gemini inyecta automáticamente al inicio:
```
@./skills/<entry>/SKILL.md
@./skills/<entry>/references/tool-mapping.md
```
y se activa porque `gemini-extension.json` declara `"contextFileName": "GEMINI.md"`.

## Inyección del bootstrap / mapeo por CLI

Cómo llega el contenido inicial (regla de "usar skills", tabla de tools) a cada CLI:

- **Gemini CLI**: `contextFileName` en `gemini-extension.json` → carga `GEMINI.md` (y sus
  `@`-includes) en cada sesión, automático.
- **OpenCode**: un plugin JS en `.opencode/plugins/<x>.js` con el hook
  `experimental.chat.messages.transform` prepende el bootstrap al primer mensaje.
- **Codex**: un script de sync copia `skills/` + `.codex-plugin/` al fork de plugins de Codex.
- **Claude Code / Cursor / Copilot**: leen `CLAUDE.md`/`AGENTS.md` y auto-descubren skills.

### ⚠️ OpenCode plugin = `.js` (no `.ts`)

OpenCode carga plugins con `import()` de Node.js. No tiene TypeScript nativo y no siempre
hay `tsc` disponible. **El plugin debe ser `.js`** (ES module con `export default`).

Si preferís escribir en TypeScript, agregá un paso de build al `setup.sh`:

```bash
npx tsc .opencode/plugins/example.ts --outDir .opencode/plugins/ --module esnext
```

Pero el default recomendado es `.js` directo — menos herramientas, menos fricción.

Además, el `package.json` del directorio `.opencode/` debe tener `"type": "module"`:

```json
{
  "type": "module",
  "dependencies": { "@opencode-ai/plugin": "^1.4.3" }
}
```

Sin esto, Node.js emite un warning en cada importación del plugin.

### ⚠️ Schema de `opencode.json`: `skills` es objeto, no array

OpenCode valida el schema en startup y **falla** si el formato es incorrecto.
El campo `skills` debe ser un **objeto** con un array `paths`, no un array plano:

```json
// ✓ CORRECTO
"skills": { "paths": ["./skills/"] }

// ✗ INCORRECTO — causa "ConfigInvalidError"
"skills": ["./skills/"]
```

Esto aplica tanto al `opencode.json` del repo como al global
`~/.config/opencode/opencode.json`.

Si usás `generate-cli-configs.py`, el generador produce el formato correcto automáticamente
(ver sección "Fuente única de verdad"). El template de ejemplo en `files/opencode.json` ya
está en el formato correcto.

### Dos estrategias de integración: per-repo vs global

OpenCode carga configs en cascada: primero el global `~/.config/opencode/opencode.json`,
y luego el `opencode.json` del proyecto actual (si existe). Los `plugins` y `skills` se
acumulan, no se reemplazan.

| Estrategia | Cómo | Cuándo usarla |
|---|---|---|
| **Per-repo** (como ankify) | Poné `opencode.json` en la raíz del repo con paths relativos | Skills que solo tienen sentido dentro del proyecto. El plugin se activa solo cuando `opencode` corre en ese repo. |
| **Global** (como meta-plugin) | Registrá en `~/.config/opencode/opencode.json` via `install-opencode.sh` | Skills que querés disponibles en **cualquier proyecto**. El meta-plugin de desarrollo es el caso típico — lo consultás mientras desarrollás otros plugins. |

**Recomendación para plugins de skills:**
1. Empezá con **per-repo** — es más simple, paths relativos, sin instalador global.
2. Si el plugin es una herramienta de desarrollo (como este catálogo), ofrecé además
   el **global** como opción avanzada vía `install-opencode.sh`.

Cuando usás paths relativos en el `opencode.json` del repo, OpenCode los resuelve
contra el directorio del proyecto. No necesitás `{env:HOME}` ni paths absolutos.

### ⚠️ Peligro: el hook OpenCode es GLOBAL

A diferencia de `CLAUDE.md` o `GEMINI.md` (que se cargan solo cuando trabajás en el repo que
los contiene), el plugin JS de OpenCode se ejecuta en **toda sesión** donde esté registrado en
`opencode.json`. Si inyectás el bootstrap sin guard, contaminás sesiones de proyectos ajenos.

**Solución: sentinel guard.** El plugin debe verificar que la sesión actual corresponde a su
propio proyecto antes de inyectar:

```js
// Ej: el template usa .catalog-root como sentinel
const SENTINEL = join(REPO_ROOT, ".catalog-root");

function isInOwnRepo() {
  try {
    return existsSync(SENTINEL) && process.cwd().startsWith(REPO_ROOT);
  } catch {
    return false;
  }
}

export default async () => {
  if (!isInOwnRepo()) return {};  // no-op en proyectos ajenos
  // ... resto del plugin
};
```

**Regla:** todo plugin OpenCode con `messages.transform` necesita un sentinel file que
identifique el proyecto dueño. El sentinel debe ser un archivo committed (no `.gitignore`) —
un empty marker, un `package.json` con `name` específico, o un archivo `.xxxx-root` único.

### Mapa de hooks: Claude Code → OpenCode

OpenCode expone un subset de hooks. Algunos no tienen equivalente directo:

| Claude Code Hook | OpenCode Hook | Limitaciones |
|---|---|---|
| `SessionStart` | `config` + `messages.transform` | `config` solo registra paths; el bootstrap va en el **primer mensaje** vía `messages.transform` |
| `PreToolUse` | **NO EXISTE** | No hay bloqueo preventivo. El comando se ejecuta antes de que el plugin se entere. Solución: gate informativo post-ejecución en `tool.execute.after` |
| `PostToolUse` | `tool.execute.after` | Idéntico en propósito. Recibe `(tool, input, output)`. Solo se dispara para `bash`/`Bash` |
| `Stop` / `SubagentStop` / `PreCompact` | **NO EXISTEN** | No hay notificación de fin de sesión. Solución: detectores periódicos en `messages.transform` con flag de módulo (`_checked`) para ejecutarlos una vez |

**Implicaciones prácticas:**

- **PreToolUse**: si dependés de bloquear comandos peligrosos antes de que se ejecuten,
  OpenCode no lo permite. El gate post-ejecución puede informar pero no prevenir.
- **Stop**: no podés hacer cleanup al final de sesión. En ankify se resolvió moviendo los
  detectores "de fin de sesión" (hotpatch, feedback) a `messages.transform` en el **primer
  mensaje de la sesión**, con flag de módulo para que corran una sola vez.
- **`messages.transform` es el swiss army knife** — suple la falta de SessionStart y Stop,
  pero con retraso de un mensaje: el bootstrap se inyecta en el mensaje del usuario, y el
  cleanup corre al primer mensaje, no al inicio real.

**Patrón de una-sola-vez (suple Stop):**

```js
let _hotpatchChecked = false;

function runOnce() {
  if (_hotpatchChecked) return;
  _hotpatchChecked = true;
  // detectores que iban en Stop hook
}

export default async () => ({
  'experimental.chat.messages.transform': async (_input, output) => {
    if (!output.messages?.length) return;
    runOnce();  // solo la primera vez que se transforman mensajes
    return { messages: output.messages };
  },
});
```

## Cómo se invoca una skill en cada CLI

| CLI | Tool de skill |
|---|---|
| Claude Code | `Skill` |
| Copilot CLI | `skill` (auto-discovery) |
| Gemini CLI | `activate_skill` (metadata cargada al inicio) |
| Codex | se cargan nativamente (lee SKILL.md) |
| OpenCode | `skill` (hook inyecta el path) |

## Integración

1. Elegí la estrategia (A/B/C) según tu plugin.
2. Copiá los manifiestos que apliquen de `files/` y completá los paths.
3. Escribí `AGENTS.md` con las instrucciones; enlazá `CLAUDE.md` y configurá `GEMINI.md`.
4. Si tus skills nombran tools, copiá y mantené `files/tool-mapping.md`.
5. Omití `model:` en el frontmatter de agents.
6. Para CLIs sin marketplace, distribuí con `files/install-skills.sh` (symlinks).
7. Para **OpenCode**, hay dos caminos:
   - **Per-repo**: poné `opencode.json` en la raíz con paths relativos (skills + plugin).
     OpenCode lo descubre automáticamente al abrir el proyecto.
   - **Global** (opcional): ofrecé un `install-opencode.sh` que agregue el plugin JS y
     skills paths en `~/.config/opencode/opencode.json`. Usalo solo cuando el plugin
     sirva como herramienta de desarrollo en cualquier proyecto.
   Ambos casos usan el mismo schema: `skills: {paths: [...]}`, no `skills: [...]`.

## Evolución: fuente única de verdad (cli-config.yaml + generador)

Mantener N manifiestos a mano escala mal. La evolución natural es un archivo canónico
YAML y un generador que produce todos los formatos nativos.

### Arquitectura

```
cli-config.yaml              # fuente única de verdad
  ↓
generate-cli-configs.py      # generador (Python stdlib + PyYAML)
  ├── .claude-plugin/plugin.json       # Claude Code
  ├── .claude-plugin/marketplace.json   # Marketplace
  ├── .codex-plugin/plugin.json         # Codex CLI
  ├── .copilot-plugin/plugin.json       # GitHub Copilot
  ├── .cursor-plugin/plugin.json        # Cursor
  ├── opencode.json                     # OpenCode
  └── gemini-extension.json             # Gemini CLI
```

### cli-config.yaml

Agrupa MCP servers, opciones de OpenCode (skills paths, plugins), metadata de Gemini, y
versión del plugin. Las rutas con `~/` se expanden según el target:

```yaml
mcp_servers:
  anki:
    command: bash
    args: ["~/.claude/mcp-scripts/start-anki-mcp.sh"]
    env:
      ANKI_CONNECT_URL: "http://localhost:8765"

opencode:
  skills:
    paths: [".opencode/skills"]
  plugins:
    - "./.opencode/plugins/example.js"

gemini_extension:
  name: "my-plugin"
  description: "Descripción del plugin"
  contextFileName: "GEMINI.md"

plugin:
  name: "my-plugin"
  version: "1.4.0"
```

### El generador

Cada target formatea distinto:

| Target | Expansión de `~` | Formato `command` |
|---|---|---|
| `.mcp.json` | `os.path.expanduser` → `/home/user/...` | `command` + `args` |
| `opencode.json` | `{env:HOME}/...` | array inline |
| `gemini-extension.json` | no aplica | n/a |

### Cuándo adoptarlo

| Situación | Recomendación |
|---|---|
| Plugin con 1-2 CLIs | Manifiestos manuales (más simple) |
| Plugin con 3+ CLIs | Generador (un solo punto de cambio) |
| Agregás/quítás MCP servers seguido | Generador (editar 1 archivo, no N) |
| El plugin es un template para otros | Generador + YAML (hereda por copia) |

### Integración

1. Copiá `files/cli-config.yaml` a la raíz de tu proyecto y personalizalo.
2. Copiá `files/generate-cli-configs.py` a `bin/dev/`.
3. Copiá `files/bump-version.py` a `bin/` (sincroniza versión en todos los
   manifests + YAML).
4. Copiá `files/post-commit` y `files/pre-commit` a `.githooks/` e instalalos:
   ```bash
   git config core.hooksPath .githooks
   for hook in post-commit pre-commit; do
     cp "features/multi-cli-compat/files/$hook" ".githooks/$hook"
     chmod +x ".githooks/$hook"
   done
   ```
5. Copiá `files/sync-manifests.yml` a `.github/workflows/` (GitHub Action que
   regenera y bumpea en cada push a main).
6. Ejecutá el generador y verificá que los manifests se creen:
   ```bash
   mkdir -p .claude-plugin .codex-plugin .cursor-plugin .copilot-plugin
   python3 bin/dev/generate-cli-configs.py
   python3 bin/bump-version.py --check
   ```
7. Cada vez que cambiés MCP servers o metadatos, editás solo `cli-config.yaml`
   y regenerás con el mismo comando. El post-commit + Action se encargan del resto.
8. `.gitignore` puede ignorar los outputs generados si preferís no versionarlos
   (o versionarlos para que el diff sea visible en PRs).

### Gotcha: hooks y plugins por CLI

El generador solo cubre **config de MCP servers + skills paths + metadata de plugin**.
Los hooks y plugins específicos de cada CLI (ej. `hooks/hooks.json` en Claude Code,
`.opencode/plugins/<name>.js` en OpenCode) siguen siendo **por CLI** porque su mecanismo
es fundamentalmente distinto y no se puede unificar en YAML.

### Referencia real

- **cli-plugin-template** (este repo): `cli-config.yaml` + `bin/dev/generate-cli-configs.py`
  — implementación canónica, se come su propio dogfood.
- [ankify](https://github.com/WSmithDR/ankify): implementación con MCP servers de anki, github
  y obsidian para 3 CLIs.

## Pipeline de sincronización (evita version drift)

Los 7 manifiestos + `cli-config.yaml` comparten la misma versión. Si se desincronizan,
`/plugin install` saltea updates por "misma versión". El pipeline de dos niveles mantiene
todo sincronizado:

### Nivel 1 — Post-commit hook (local)

El hook `post-commit` (ver feature `versioning`) determina el bump type por conventional
commit (`feat:` → minor, `fix:` → patch, `BREAKING` → major) y delega en
`bump-version.py`, que toca **todos** los manifiestos + YAML antes de amendar el commit.

```
commit "feat: add widget"
  → post-commit detecta "minor"
  → bump-version.py minor
    → plugin.json: 1.0.0 → 1.1.0
    → marketplace.json: 1.0.0 → 1.1.0
    → opencode.json: 1.0.0 → 1.1.0
    → gemini-extension.json: 1.0.0 → 1.1.0
    → codex/cursor/copilot: 1.0.0 → 1.1.0
    → cli-config.yaml: 1.0.0 → 1.1.0
  → amenda el commit (bump incluido en el mismo commit)
```

### Nivel 2 — GitHub Action `sync-manifests.yml` (remoto)

Al pushear a `main`, la Action regenera los manifiestos desde `cli-config.yaml`
(garantizando que reflejen el YAML actual) y luego bumpea versión por el mismo
conventional commit, commitendo todo con `[skip ci]` para evitar loops.

```
push a main
  → generate-cli-configs.py  (sincroniza manifests con YAML)
  → bump-version.py <type>   (avanza versión en todos + YAML)
  → commit "chore: auto-sync manifests [skip ci]"
```

### Beneficios

| Problema anterior | Solución |
|---|---|
| Post-commit solo tocaba plugin.json + marketplace.json; los otros 5 manifests se atrasaban | `bump-version.py` toca TODOS los manifests + YAML |
| Editar YAML y commit → la version del YAML se escribía en manifests viejos, post-commit bump re-escribía plugin.json con la nueva, pero el YAML quedaba atrasado | `bump-version.py` escribe el nuevo version también en `cli-config.yaml` |
| Post-commit y Action podían desincronizarse | Ambos usan `bump-version.py` como única fuente de version sync |
| Si editás YAML localmente y pusheás, los manifests locales tienen version vieja | La Action regenera desde YAML + bumpea, todo en un commit |

### Cómo adoptar el pipeline en tu plugin

Los archivos template están en `features/multi-cli-compat/files/`:

| Archivo | Copiar a | Propósito |
|---|---|---|---|
| `bump-version.py` | `bin/bump-version.py` | Sincroniza version en 7 manifests + YAML |
| `capture-learning.sh` | `bin/capture-learning.sh` | Captura un descubrimiento multi-CLI como feedback `signal: discovery` |
| `post-commit` | `.githooks/post-commit` | Bumpea local + amenda el commit |
| `pre-commit` | `.githooks/pre-commit` | **Bloquea** el commit si tocaste configs multi-CLI sin docs. Escape: `[skip-docs]` en el mensaje. |
| `sync-manifests.yml` | `.github/workflows/sync-manifests.yml` | Regenera + bumpea en push a main |

**Pre-commit strict:** si el staged incluye `cli-config.yaml`, manifests, o la feature
`multi-cli-compat/` y no incluye ningún archivo de documentación, el commit se rechaza.
Para cambios triviales que no ameritan docs, agregá `[skip-docs]` al mensaje:
```
git commit -m "fix: typo en opencode.json [skip-docs]"
```

## Capturar descubrimientos de compatibilidad

Cuando desarrollás un plugin downstream y descubrís que un CLI maneja algo distinto
(una tool no existe, un hook tiene firma diferente, un schema es incompatible), usá
`capture-learning.sh` para formalizarlo:

```bash
bash bin/capture-learning.sh mi-plugin gemini-no-posttooluse <<'EOF'
## Descubrimiento
Gemini CLI no expone PostToolUse — solo PreToolUse.
## CLI(s) involucrado(s)
gemini
## Contexto
Al implementar el hook de logging en mi-plugin, Gemini rechazó
PostToolUse porque no existe en su schema.
## Recomendación
Usar tool.execute.after de OpenCode como alternativa, que sí existe en ambos.
## ¿Aplica al template?
true
EOF
```

Guarda el descubrimiento en `$DATA_DIR/<plugin>/feedbacks/` con `signal: discovery` y
`applied: false`. Si aplica al template (`¿Aplica al template? true`), sugiere migrar
la entrada a `tool-mapping.md` para que futuros plugins la hereden.

El pipeline `plugin-hotpatch` puede procesar estos descubrimientos igual que cualquier
feedback, parcheando skills o documentación cuando corresponda.

Requisitos: PyYAML (`pip3 install pyyaml`), Python 3.10+, y que tu proyecto tenga
`cli-config.yaml` + `generate-cli-configs.py` (ver "Integración" arriba).

## Tests

Abrí el proyecto en al menos dos CLIs (ej. Claude Code y OpenCode) y confirmá que las
skills/MCP aparecen y que las instrucciones se cargan en ambos.

## Gotchas

- **`model: inherit`** rompe OpenCode/otros → omitir el campo.
- **`hooks/hooks.json`** lo honra solo Claude Code; no asumas hooks en otros CLIs.
- **Stop hook** → Claude Code usa `hooks/hooks.json:Stop`; OpenCode equivalente via
  `event("global.disposed")` en el JS plugin. Ver `features/multi-cli-compat/files/opencode-plugin.js`.
- **OpenCode global install** → el catálogo incluye `bin/install-opencode.sh` que registra
  plugin JS + skills paths en `~/.config/opencode/opencode.json`.
- Copiar solo `.mcp.json` NO te da multi-CLI si tus skills nombran tools — necesitás el mapping.

## Changelog

- **2.7.0** — `capture-learning.sh`: formaliza descubrimientos multi-CLI como feedback con
  `signal: discovery`. Nuevo signal type en `plugin-feedback-log` y `growth-engine`.
  Pre-commit bloquea (exit 1) si tocás configs sin docs, escape `[skip-docs]`.
- **2.6.0** — pipeline de sincronización: `bump-version.py` ahora toca `cli-config.yaml`
  y todos los 7 manifests (no solo plugin.json + marketplace.json). Post-commit hook
  delega en `bump-version.py`. Nueva GitHub Action `sync-manifests.yml` que regenera
  desde YAML + bumpea en cada push a main. Pre-commit hook que recuerda documentar
  aprendizajes multi-CLI. Templates para downstream en `files/`:
  `bump-version.py`, `post-commit`, `pre-commit`, `sync-manifests.yml`.
- **2.5.0** — schema `opencode.json`: skills como objeto `{paths: [...]}`, no array.
  Dos estrategias de integración OpenCode (per-repo vs global). Template corregido en
  `files/opencode.json`. Gotcha: `.ts` → `.js` en plugins OpenCode.
- **2.4.0** — generador expandido a 7 manifests (todos los CLIs + marketplace). Stop hook
  OpenCode via `event("global.disposed")`. OpenCode global install: `bin/install-opencode.sh`.
- **2.3.0** — mapa detallado de hooks Claude Code ↔ OpenCode (limitaciones: PreToolUse y Stop
  no existen en OpenCode; soluciones documentadas con `tool.execute.after` + `messages.transform`).
  Documentado que OpenCode plugin debe ser `.js` (no `.ts`) y requiere `"type": "module"` en
  `package.json` para evitar warnings de Node.js.
- **2.2.0** — nueva estrategia multi-CLI: fuente única de verdad vía `cli-config.yaml` + generador `generate-cli-configs.py` (reduce N manifiestos a 1 archivo YAML)
- **2.1.0** — agregada la guía "Cuál elegir" (regla de decisión A/B/C y por qué B es el
  mejor default).
- **2.0.0** — reescritura completa: tres estrategias, matriz de manifiestos por CLI,
  patrón de archivos de instrucciones (AGENTS.md/GEMINI.md), tabla de mapeo de tools,
  inyección por CLI, gotcha de `model:`. (Antes solo cubría Claude Code + OpenCode.)
- **1.0.0** — versión inicial (Claude Code + OpenCode + LSP).
