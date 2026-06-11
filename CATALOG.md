# Catálogo de features

Índice de features reusables. Para integrar uno, abrí su `README.md`.
Para el flujo de uso completo ver [AGENTS.md](AGENTS.md).

## Desarrollo y publicación

| Feature | Versión | CLIs | Descripción |
|---|---|---|---|
| [`git-hooks`](features/git-hooks/README.md) | 1.0.0 | todos | Git hooks de desarrollo: instalación via symlink editor-agnóstica, pre-commit que corre tests, y arnés de testing con tmpdir aislado |
| [`versioning`](features/versioning/README.md) | 1.0.0 | todos | Versionado semántico automático: `post-commit` bumpea según el prefijo del commit (conventional commits) y amenda el commit |
| [`docs-conventions`](features/docs-conventions/README.md) | 1.0.0 | todos | Secciones estándar de README: install, update, verificación de versión, tabla de conventional commits |

## Integración con el CLI

| Feature | Versión | CLIs | Descripción |
|---|---|---|---|
| [`multi-cli-compat`](features/multi-cli-compat/README.md) | 1.0.0 | todos | Manifiestos para Claude Code / OpenCode / Gemini / LSP compartiendo una sola config MCP; instrucciones agnósticas en AGENTS.md |
| [`claude-code-hooks`](features/claude-code-hooks/README.md) | 1.0.0 | claude-code | Patrones de hooks: SessionStart auto-setup, PostToolUse reacción a fallos, convención exit 2/stderr, gotcha CLAUDE_PLUGIN_ROOT |
| [`health-check`](features/health-check/README.md) | 1.0.0 | todos | Skill de diagnóstico: versión, skills, hooks, MCPs vivos, detección de instalación incompleta |

## Estado y configuración

| Feature | Versión | CLIs | Descripción |
|---|---|---|---|
| [`project-config`](features/project-config/README.md) | 1.0.0 | todos | Config por proyecto: detección de config faltante, setup interactivo, persistencia atómica |
| [`externalized-config`](features/externalized-config/README.md) | 1.0.0 | todos | Reglas/umbrales de comportamiento en config/*.json leídos en tiempo real, no hardcodeados |
| [`data-gateway`](features/data-gateway/README.md) | 1.0.0 | todos | Abstracción única de persistencia: las skills nunca tocan disco, pasan por un CLI unificado + bin/lib/ |

## Flujo de trabajo y crecimiento

| Feature | Versión | CLIs | Descripción |
|---|---|---|---|
| [`entry-point-router`](features/entry-point-router/README.md) | 1.0.0 | todos | Un único skill de entrada que lee contexto y enruta al escenario correcto |
| [`proposal-gate`](features/proposal-gate/README.md) | 1.0.0 | todos | Aprobación humana explícita antes de acciones irreversibles, vía archivo de propuesta revisable |
| [`vocabulary-guardian`](features/vocabulary-guardian/README.md) | 1.0.0 | todos | Fuente única de verdad para términos/estados de dominio; escáner que detecta valores no registrados |
| [`growth-engine`](features/growth-engine/README.md) | 1.0.0 | todos | Auto-mejora: captura feedback/fricción y un motor de hotpatch lo procesa, parchea y commitea |
