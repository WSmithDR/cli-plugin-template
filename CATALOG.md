# Catálogo de features

Índice de features reusables. Para integrar uno, abrí su `README.md`.
Para el flujo de uso completo ver [AGENTS.md](AGENTS.md).

## Desarrollo y publicación

| Feature | Versión | CLIs | Descripción |
|---|---|---|---|
| [`git-hooks`](features/git-hooks/README.md) | 1.0.0 | todos | Git hooks de desarrollo: instalación via symlink editor-agnóstica, pre-commit que corre tests, y arnés de testing con tmpdir aislado |
| [`versioning`](features/versioning/README.md) | 1.2.0 | todos | Versionado semántico automático: `post-commit` bumpea según el prefijo del commit (conventional commits), sincroniza `marketplace.json`, y amenda el commit (con guard de recursión via sentinel) |
| [`docs-conventions`](features/docs-conventions/README.md) | 1.1.1 | todos | Secciones estándar de README: install, update, verificación de versión, tabla de conventional commits |

## Integración con el CLI

| Feature | Versión | CLIs | Descripción |
|---|---|---|---|
| [`multi-cli-compat`](features/multi-cli-compat/README.md) | 2.1.0 | todos | Compatibilidad real con Claude Code / Gemini / OpenCode / Codex / Cursor / Copilot: 3 estrategias + guía de cuál elegir, manifiestos por CLI, AGENTS.md/GEMINI.md, y **traducción de nombres de tools** entre CLIs |
| [`mcp-npx-wrapper`](features/mcp-npx-wrapper/README.md) | 1.0.0 | claude-code | Plugin fino que envuelve un MCP externo de npm (`npx -y <paquete>`), sin código local |
| [`mcp-server-types`](features/mcp-server-types/README.md) | 1.0.0 | todos | Todos los transportes MCP: stdio (npx/bun/docker/uvx/php), HTTP, HTTP+auth Bearer, SSE; auth sin hardcodear secrets |
| [`claude-code-hooks`](features/claude-code-hooks/README.md) | 1.0.0 | claude-code | Patrones de hooks: SessionStart auto-setup, PostToolUse reacción a fallos, convención exit 2/stderr, gotcha CLAUDE_PLUGIN_ROOT |
| [`advanced-hooks`](features/advanced-hooks/README.md) | 1.0.0 | claude-code | asyncRewake (revisión en background que re-despierta al agente), filtrado por patrón de comando (`if: Bash(...)`), agente LLM dentro de un hook |
| [`hook-python-bootstrap`](features/hook-python-bootstrap/README.md) | 1.0.0 | claude-code | Shim que encuentra un Python 3 válido y ejecuta el hook con él (cross-platform, UTF-8, Windows) |
| [`health-check`](features/health-check/README.md) | 1.0.0 | todos | Skill de diagnóstico: versión, skills, hooks, MCPs vivos, detección de instalación incompleta |

## Estado y configuración

| Feature | Versión | CLIs | Descripción |
|---|---|---|---|
| [`project-config`](features/project-config/README.md) | 1.0.0 | todos | Config por proyecto: detección de config faltante, setup interactivo, persistencia atómica |
| [`externalized-config`](features/externalized-config/README.md) | 1.0.0 | todos | Reglas/umbrales de comportamiento en config/*.json leídos en tiempo real, no hardcodeados |
| [`data-gateway`](features/data-gateway/README.md) | 1.0.0 | todos | Abstracción única de persistencia: las skills nunca tocan disco, pasan por un CLI unificado + bin/lib/ |
| [`session-memory`](features/session-memory/README.md) | 1.0.0 | claude-code | Memoria persistente entre sesiones: MCP durable + hooks que inyectan contexto (SessionStart/UserPromptSubmit) + lock distribuido |

## Flujo de trabajo y crecimiento

| Feature | Versión | CLIs | Descripción |
|---|---|---|---|
| [`entry-point-router`](features/entry-point-router/README.md) | 1.0.0 | todos | Un único skill de entrada que lee contexto y enruta al escenario correcto |
| [`proposal-gate`](features/proposal-gate/README.md) | 1.0.0 | todos | Aprobación humana explícita antes de acciones irreversibles, vía archivo de propuesta revisable |
| [`vocabulary-guardian`](features/vocabulary-guardian/README.md) | 1.0.0 | todos | Fuente única de verdad para términos/estados de dominio; escáner que detecta valores no registrados |
| [`growth-engine`](features/growth-engine/README.md) | 1.0.0 | todos | Auto-mejora: captura feedback/fricción y un motor de hotpatch lo procesa, parchea y commitea |
| [`planning-workflow`](features/planning-workflow/README.md) | 1.0.0 | todos | Planear tareas multi-paso con tasks de criterios concretos, self-review y ejecución con checkpoints |

## Autoría de skills y agents

| Feature | Versión | CLIs | Descripción |
|---|---|---|---|
| [`skill-authoring`](features/skill-authoring/README.md) | 1.0.0 | todos | Convenciones para SKILL.md descubribles: frontmatter `Use when…` (CSO), progressive disclosure, Red Flags |
| [`agent-authoring`](features/agent-authoring/README.md) | 1.0.0 | todos | Convenciones para definir subagentes: frontmatter when-to-use, scoping de tools, contrato de salida |
| [`autonomous-agent`](features/autonomous-agent/README.md) | 1.0.0 | claude-code | Agente proactivo que actúa solo sobre lo recién modificado, acotado a la sesión actual |
| [`discipline-skills`](features/discipline-skills/README.md) | 1.0.0 | todos | Patrón de skill que hace cumplir una regla: Iron Law + tabla Red Flags + proceso obligatorio |

## Orquestación multi-agente

| Feature | Versión | CLIs | Descripción |
|---|---|---|---|
| [`parallel-agents`](features/parallel-agents/README.md) | 1.0.0 | claude-code | Abanicar trabajo independiente a subagentes en paralelo e integrar, sin inundar el contexto principal |
| [`agent-pipeline`](features/agent-pipeline/README.md) | 1.0.0 | claude-code | Pipeline secuencial con contratos de artefactos JSON, fase determinista+semántica, y agente revisor/QA |

## Escala y eficiencia

| Feature | Versión | CLIs | Descripción |
|---|---|---|---|
| [`context-batching`](features/context-batching/README.md) | 1.0.0 | todos | Lotear trabajo grande para no saturar el contexto; reprocesar solo lo cambiado vía fingerprints (SHA256 + git diff) |
| [`bundled-scripts`](features/bundled-scripts/README.md) | 1.0.0 | todos | Delegar lo determinista (enumerar, contar, parsear) a scripts incluidos; el LLM solo para juicio |
| [`worktree-redirect`](features/worktree-redirect/README.md) | 1.0.0 | claude-code | Detectar git worktrees y redirigir el output de datos al repo principal para no perderlo |

## Calidad y verificación

| Feature | Versión | CLIs | Descripción |
|---|---|---|---|
| [`strict-tdd`](features/strict-tdd/README.md) | 1.0.0 | todos | TDD con evidencia verificable: tabla RED/GREEN/TRIANGULATE/SAFETY-NET + auditoría de assertions (sin tautologías ni mocks vacíos) |
| [`portability-audit`](features/portability-audit/README.md) | 1.0.0 | todos | Escáner determinista de portabilidad/agnosticismo: rutas absolutas, refs a dirs del plugin sin `${CLAUDE_PLUGIN_ROOT}`, paths `.claude/`, `model: inherit`, secretos e intérpretes no portables. Por severidad, usable en CI |
| [`skill-structure-audit`](features/skill-structure-audit/README.md) | 1.0.0 | todos | Escáner determinista de estructura de skills: scripts sueltos en la raíz de la skill y bloques de script (>2 líneas) embebidos en SKILL.md. Fuerza modularización (lógica→`scripts/`, plantillas→`references/`). Por severidad, usable en CI |
| [`dual-review`](features/dual-review/README.md) | 1.0.0 | claude-code | Revisión adversarial con dos jueces ciegos en paralelo, cruce confirmado/sospechoso, fix y re-juicio |
| [`change-sizing`](features/change-sizing/README.md) | 1.0.0 | todos | Commits atómicos + presupuesto de líneas + PRs en cadena (stacked / feature-branch) para mantener todo revisable |
| [`skill-evals`](features/skill-evals/README.md) | 1.0.0 | claude-code | Testear skills con evals + análisis de varianza, y optimizar el `description` para mejorar el triggering |
