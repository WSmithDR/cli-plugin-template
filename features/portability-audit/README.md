# Feature: portability-audit

## Qué hace

Escanea un plugin y reporta lo que lo ata a **una máquina** o a **un solo CLI** —
los dos enemigos de la escalabilidad y el agnosticismo. Es un script determinista
(`files/audit-portability.py`): mismo árbol de archivos → mismo reporte. El LLM solo
interpreta y prioriza.

## Por qué

Un plugin "anda en mi máquina" y "anda en Claude Code" hasta que alguien lo instala
en otro lado. Los dos quiebres más comunes son silenciosos:

- **Rutas no portables.** En *scripts y configs*, una ruta **absoluta** (`/home/alice/…`,
  `/Users/bob/…`, `C:\…`) solo existe en la máquina del autor. En *skills y commands*
  pasa lo inverso: una ruta **relativa** a un dir del plugin (`cat features/x.md`)
  resuelve contra la **cwd del usuario**, no contra el plugin instalado — hay que
  prefijar con `${CLAUDE_PLUGIN_ROOT}`. El audit detecta ambos.
- **Acople a un CLI.** Paths `.claude/…` hardcodeados, `model: inherit` en frontmatter
  (que rompe OpenCode y otros), etc. — el plugin "funciona" solo en Claude Code.

Y de paso atrapa dos clásicos que no son de portabilidad pero sí de higiene:
secretos hardcodeados e intérpretes no portables (`python` en vez de `python3`).

## Qué chequea

| Severidad | Tipo | Qué detecta | Cómo se arregla |
|---|---|---|---|
| CRITICAL | `absolute-path` | `/home/x`, `/Users/x`, `/root/x`, `/mnt/c/…`, `C:\…` | `${CLAUDE_PLUGIN_ROOT}`, ruta relativa, o `$HOME` |
| CRITICAL | `possible-secret` | API keys, tokens (AWS/GitHub/Slack/OpenAI), claves privadas | leer de env var, nunca commitear |
| WARNING | `unrooted-ref` | skill/command que toca `features/`, `bin/`, `config/`… sin rootear | prefijar con `${CLAUDE_PLUGIN_ROOT}/` |
| WARNING | `claude-only-path` | `.claude/…` hardcodeado | ver `multi-cli-compat` |
| WARNING | `model-inherit` | `model: inherit` en frontmatter | omitir el campo `model:` |
| INFO | `portable-shebang` | `python`/`python2`, shebang absoluto a python | `python3` o `hook-python-bootstrap` |

Filtros para bajar falsos positivos: ignora shebangs `#!/usr/bin/env …`, descarta
placeholders de secretos (`your_token`, `${VAR}`, `process.env`, `<...>`), no marca
`${CLAUDE_PLUGIN_ROOT}/...` ni rutas relativas resueltas desde el script, y solo
evalúa `unrooted-ref` en líneas que parecen comando dentro de `skills/`/`commands/`.

## Excluir falsos positivos legítimos

Todo repo real tiene rutas de ejemplo en docs y `/home/...` en fixtures. Dos escapes,
al estilo `.gitignore` + `# noqa`:

- **`.portabilityignore`** en la raíz escaneada: un glob por línea (`#` comenta).
  Ej.: `docs/**`, `tests/fixtures/**`, `examples/**`.
- **Marcador inline `audit-ignore`**: cualquier línea que contenga ese literal se
  omite. Ej.: `DATA="/home/ci/cache"  # audit-ignore` en un fixture.

Usá la exclusión con criterio: excluir prosa/fixtures está bien; silenciar un secreto
o una ruta absoluta real con `audit-ignore` solo difiere el problema.

## Integración

1. Copiá `files/audit-portability.py` a `bin/` (o `scripts/`) de tu plugin —
   centralizá scripts como dice `bundled-scripts`. No tiene dependencias (stdlib).
2. Corrélo sobre la raíz del plugin:
   ```bash
   python3 bin/audit-portability.py .
   ```
3. Resolvé los `CRITICAL` (rutas absolutas, secretos) antes de publicar; tratá
   `WARNING` como deuda de agnosticismo y `INFO` como pulido.
4. **CI / pre-commit (recomendado):** el script sale con exit 1 si hay algún `CRITICAL`,
   así que enganchalo igual que los tests (ver `git-hooks`). Con `--quiet` no imprime
   nada cuando está todo bien, ideal para un hook:
   ```bash
   python3 bin/audit-portability.py . --quiet || exit 1
   ```
   Este mismo repo lo dogfoodea: `bin/dev/git-hooks/pre-commit` corre el audit en cada
   commit (instalalo con `bash bin/dev/setup.sh`).
5. **Salida JSON** (`--json`) si querés que otro paso la consuma:
   ```bash
   python3 bin/audit-portability.py . --json
   ```

> En este meta-plugin no hace falta copiar nada: la skill `plugin-audit` ya corre el
> script desde `${CLAUDE_PLUGIN_ROOT}/features/portability-audit/files/` sobre la cwd.

## Tests

Corré el script dos veces sobre el mismo árbol → salida idéntica (es determinista).
Verificá que una ruta `${CLAUDE_PLUGIN_ROOT}/...` y un `#!/usr/bin/env python3` **no**
generan hallazgos, y que un `/home/...` y un `model: inherit` **sí**.

## Changelog

- **1.0.0** — escáner inicial: rutas absolutas, refs sin rootear, paths `.claude/`,
  `model: inherit`, secretos, intérpretes no portables. Reporte por severidad + `--json`,
  exit 1 en CRITICAL.
