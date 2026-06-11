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
