# cli-plugin-template

Catálogo vivo de features reusables para plugins multi-CLI (Claude Code, OpenCode,
Gemini CLI…). Versionado automático, git hooks, compatibilidad entre CLIs y
convenciones de documentación.

No es un scaffold de copia única: es un repo que los agentes **consultan** para
integrar mejoras en el plugin que están desarrollando, y al que **promueven** de
vuelta las mejoras que sirven para todos.

## Cómo se usa

- **Integrar un feature** en tu plugin → leé [`CATALOG.md`](CATALOG.md), abrí el
  `README.md` del feature, adaptá los archivos.
- **Promover una mejora** desde un plugin al catálogo → seguí
  [`CONTRIBUTING.md`](CONTRIBUTING.md).
- **Guía completa para agentes** → [`AGENTS.md`](AGENTS.md).

## Como plugin instalable

Además de consultarse como repo, el catálogo se instala como plugin de desarrollo.

### Instalación

**1. Registrar el marketplace (una sola vez, global):**
```bash
claude plugin marketplace add WSmithDR/cli-plugin-template
```

**2. Instalar en el proyecto de plugin:**
```bash
claude plugin install cli-plugin-template@cli-plugin-template --scope project
```

**Global (todos los proyectos):**
```bash
claude plugin install cli-plugin-template@cli-plugin-template
```

### Actualización

El CLI cachea una copia local del plugin: **refrescá el marketplace y reinstalá**. No
alcanza con que cambie el repo, y `claude plugin update` sin refrescar puede saltear el
update por "misma versión":

**Scope project:**
```bash
/plugin marketplace update cli-plugin-template
/plugin install cli-plugin-template@cli-plugin-template --scope project
```

**Global (todos los proyectos):**
```bash
/plugin marketplace update cli-plugin-template
/plugin install cli-plugin-template@cli-plugin-template
```

En una sesión activa, aplicá sin reiniciar con `/reload-plugins`. Para verificar la versión
instalada, corré `/cli-plugin-template-health`.

### Capacidades

Una vez instalado en un proyecto de plugin:
- **`/plugin-dev`** — menú de capacidades (router `plugin-dev`). Se llama `/plugin-dev` y no `/plugin` para no chocar con el comando nativo `/plugin` de Claude Code.
- **`/plugin-audit`** — qué features del catálogo te faltan.
- **`/plugin-feature <nombre>`** — integrar un feature.
- **`/plugin-recommend`** — sugerir features desde una necesidad.
- **`/plugin-promote`** — subir una mejora al catálogo.
- **`/plugin-register`** — dar de alta el plugin para que el meta-plugin administre su evolución.
- **`/plugin-feedback-log`** — capturar una fricción/feedback de una skill de un plugin propio.

Al abrir un proyecto de plugin por primera vez, un aviso sugiere correr `/plugin-audit`.

## Categorías

Ver el índice completo en [`CATALOG.md`](CATALOG.md).

| Categoría | Features | Qué cubre |
|---|---|---|
| **Desarrollo y publicación** | 3 | git hooks de dev, versionado automático, convenciones de docs |
| **Integración con el CLI** | 7 | compatibilidad multi-CLI, transportes MCP, hooks (básicos y avanzados), health check |
| **Estado y configuración** | 4 | config por proyecto, reglas externalizadas, persistencia, memoria entre sesiones |
| **Flujo de trabajo y crecimiento** | 5 | entry-point router, proposal gate, vocabulario, auto-mejora, planificación |
| **Autoría de skills y agents** | 4 | escribir skills descubribles y agentes, discipline-skills, agente autónomo |
| **Orquestación multi-agente** | 2 | subagentes en paralelo, pipeline con contratos de artefactos |
| **Escala y eficiencia** | 3 | batching, scripts deterministas, worktree redirect |
| **Calidad y verificación** | 5 | strict-TDD, doble review adversarial, sizing de cambios, evals de skills, auditoría de portabilidad |

## Estructura

```
AGENTS.md / CLAUDE.md   punto de entrada para cualquier CLI
CATALOG.md              índice de features
CONTRIBUTING.md         loop inverso (promover mejoras)
features/<nombre>/
  README.md             qué · por qué · cómo integrarlo
  files/                archivos reusables
  meta.yml              version, cli_compat, depends_on
```
