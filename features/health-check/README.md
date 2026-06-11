# Feature: health-check

## Qué hace

Una skill `<plugin>-health` que diagnostica si el plugin está bien integrado:
versión instalada, skills disponibles, hooks registrados, MCPs requeridos vivos, y
si `CLAUDE_PLUGIN_ROOT` está set.

## Por qué

Tras un `install`/`update`, el usuario necesita confirmar que tomó efecto y que nada
está roto. Sin un comando de diagnóstico, los fallos son silenciosos y difíciles de
rastrear (ej. la versión cacheada no se actualizó, o un MCP no responde).

## Integración

Creá `skills/<plugin>-health/SKILL.md` que ejecute y reporte:

1. **Identidad y versión** — la versión mostrada debe coincidir con la última publicada:
   ```bash
   cat "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null \
     | python3 -c 'import json,sys; d=json.load(sys.stdin); print(f"v{d[\"version\"]}")'
   ```
2. **Skills disponibles** — `ls "${CLAUDE_PLUGIN_ROOT}/skills/"`
3. **Hooks registrados** — parsear `hooks/hooks.json` y listar evento → comando.
4. **MCPs requeridos** (si aplica) — verificar que respondan (ver más abajo).
5. **Estado del proyecto** — conteos/archivos del datadir, config presente o no.
6. **Gotcha CLAUDE_PLUGIN_ROOT** — si está vacío, reportar que el plugin no se
   instaló via `claude plugin install` y dar el comando correcto.

### Verificación de MCPs

Si el plugin depende de MCPs (ej. AnkiConnect, GitHub), verificá que estén vivos al
inicio y fallá rápido con un mensaje accionable, en vez de un error críptico más tarde.
Para AnkiConnect, por ejemplo: un `curl` a `http://localhost:8765`. Reportá cada MCP
como ✓/✗ con qué arreglar si está caído.

## Salida sugerida

```
✓ <plugin> v1.2.3
✓ Skills: 10 disponibles
✓ Hooks: SessionStart, PostToolUse
✗ MCP anki — AnkiConnect no responde (abrí Anki con el addon AnkiConnect)
✓ datadir: 10 items
```

## Tests

Corré la skill en un proyecto con el plugin instalado y otro sin instalar; debe
distinguir ambos casos (especialmente `CLAUDE_PLUGIN_ROOT` vacío).

## Changelog

- **1.0.0** — combina `todo-health` (todo-plugin) y `anki-mcp-health` (ankify).
