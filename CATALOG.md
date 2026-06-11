# Catálogo de features

Índice de features reusables. Para integrar uno, abrí su `README.md`.
Para el flujo de uso completo ver [AGENTS.md](AGENTS.md).

| Feature | Versión | CLIs | Descripción |
|---|---|---|---|
| [`git-hooks`](features/git-hooks/README.md) | 1.0.0 | todos | Infraestructura de git hooks para desarrollo: instalación via symlink editor-agnóstica, pre-commit que corre tests, y arnés de testing de hooks |
| [`versioning`](features/versioning/README.md) | 1.0.0 | todos | Versionado semántico automático: `post-commit` bumpea la versión según el prefijo del commit (conventional commits) y amenda el commit |
| [`docs-conventions`](features/docs-conventions/README.md) | 1.0.0 | todos | Convenciones de documentación: secciones de install/update, verificación de versión, tabla de conventional commits |

## Planeados (aún sin código en el catálogo)

| Feature | Estado | Notas |
|---|---|---|
| `multi-cli-compat` | pendiente | Compatibilidad Claude Code / OpenCode / Gemini CLI. El código vive por ahora en otro repo; migrar acá cuando se estabilice |
