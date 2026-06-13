# Feature: skill-structure-audit

## Qué hace

Escanea `skills/` de un plugin y reporta lo que viola la **modularización**: un
`SKILL.md` debe tener solo **instrucciones**, no código ni archivos sueltos. Es un
script determinista (`files/audit-skill-structure.py`): mismo árbol de archivos →
mismo reporte. El LLM solo interpreta y prioriza.

## Por qué

Un `SKILL.md` que crece con scripts embebidos y configs sueltas se vuelve caro: el
agente carga 200 líneas de bash para leer 3 de instrucciones, y la lógica deja de ser
testeable o reusable. La estructura sana separa responsabilidades:

```
skills/<name>/
  SKILL.md            # instrucciones (qué y por qué, no el código)
  scripts/            # bash, python, node — lógica reusable, invocada por ruta
  references/         # tablas de mapeo, schemas, plantillas de datos
  files/              # templates que el plugin copia al proyecto downstream
```

La regla operativa: **ningún bloque de script de más de 2 líneas vive en SKILL.md**.
Una invocación corta (`bash "$CLAUDE_PLUGIN_ROOT/skills/x/scripts/foo.sh"`) se tolera;
la lógica multilínea va a `scripts/` y las plantillas de datos (heredocs de frontmatter
que el agente rellena) a `references/`.

## Qué chequea

| Severidad | Qué detecta | Cómo se arregla |
|---|---|---|
| ERROR | `.sh`/`.py`/`.js`/`.ts`/`.rb` suelto en la raíz de la skill | mover a `scripts/` |
| ERROR | bloque de script (` ```bash `, ` ```python `, …) de **>2 líneas** en SKILL.md | mover lógica a `scripts/`, plantillas a `references/`; dejar solo la invocación ≤2 líneas |
| ERROR | falta `SKILL.md` en el dir de la skill | crear el SKILL.md |
| WARNING | `.md` suelto en la raíz de la skill | mover a `references/` |
| WARNING | `.json`/`.yml`/`.toml`/`.cfg` suelto en la raíz | mover a `references/` o `files/` |
| WARNING | `files/` con contenido que SKILL.md nunca menciona | referenciarlo o quitarlo |

Un bloque cercado **sin lenguaje** (un árbol de directorios en ` ``` ` sin etiqueta) no
cuenta como script y no se marca. El umbral de 2 líneas es la constante
`MAX_INLINE_LINES` del script.

## Integración

1. Copiá `files/audit-skill-structure.py` a `bin/` (o `scripts/`) de tu plugin —
   centralizá scripts como dice `bundled-scripts`. No tiene dependencias (stdlib).
2. Corrélo desde la raíz del plugin:
   ```bash
   python3 bin/audit-skill-structure.py
   ```
3. Resolvé los `ERROR` (scripts sueltos, bloques embebidos) antes de publicar; tratá
   los `WARNING` como deuda de orden.
4. **CI / pre-commit (recomendado):** con `--threshold ERROR` el script sale con exit 1
   solo ante violaciones estructurales (los WARNING no bloquean), ideal para un hook
   (ver `git-hooks`):
   ```bash
   python3 bin/audit-skill-structure.py --threshold ERROR || exit 1
   ```
   Este mismo repo lo dogfoodea: `bin/dev/git-hooks/pre-commit` corre el audit en cada
   commit (instalalo con `bash bin/dev/setup.sh`).
5. **Salida JSON** (`--json`) si querés que otro paso la consuma; `--quiet` para solo
   el exit code.

> En este meta-plugin no hace falta copiar nada: la skill `plugin-audit` ya corre el
> script desde `${CLAUDE_PLUGIN_ROOT}/features/skill-structure-audit/files/` sobre la cwd.

## Tests

Corré el script dos veces sobre el mismo árbol → salida idéntica (es determinista).
Verificá que un bloque de ≤2 líneas y un bloque sin lenguaje **no** generan hallazgos,
y que un bloque de >2 líneas y un `.sh` suelto en la raíz **sí**. El repo trae una suite
de casos aislados en `bin/test-skill-structure.sh`.

## Changelog

- **1.0.0** — escáner inicial: scripts sueltos en la raíz (ERROR), bloques de script
  >2 líneas en SKILL.md (ERROR), configs/markdown sueltos (WARNING), `files/` huérfano
  (WARNING). Modos `--json` / `--quiet` / `--threshold WARN|ERROR`, exit code por severidad.
