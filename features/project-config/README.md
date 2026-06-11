# Feature: project-config

## Qué hace

Una skill `<plugin>-config` que gestiona configuración **por proyecto** (no global):
detecta si falta `config.json`, pregunta preferencias de forma interactiva, y las
persiste de forma atómica.

## Por qué

Cada proyecto puede querer ajustes distintos (ej. ¿ignorar el datadir en git?). Una
config por proyecto, detectada automáticamente en `SessionStart` (ver feature
`claude-code-hooks`), evita que el usuario tenga que recordar configurarla.

## Integración

1. Definí el schema del `config.json` (datadir local al proyecto):
   ```json
   {
     "<setting>": false,
     "configured_at": "YYYY-MM-DD",
     "configured_by": "GitName"
   }
   ```
2. Creá la skill `skills/<plugin>-config/SKILL.md` con este flujo:
   - **Leer**: `cat <datadir>/config.json 2>/dev/null`
   - **Modo**: sin config → first-run (preguntar todo); con config → mostrar y
     preguntar qué cambiar.
   - **Preguntar**: usá `AskUserQuestion` con opciones claras (incluí la recomendada
     primera).
   - **Persistir atómico** con Python (no `echo >`, que puede corromper):
     ```bash
     CREATOR=$(git config user.name); TODAY=$(date +%Y-%m-%d)
     CREATOR="$CREATOR" TODAY="$TODAY" python3 -c '
     import json, os
     cfg = {"<setting>": False,
            "configured_at": os.environ["TODAY"],
            "configured_by": os.environ["CREATOR"]}
     with open("<datadir>/config.json", "w") as f:
         json.dump(cfg, f, indent=2)
     '
     ```
3. Conectá la detección de config faltante al hook `SessionStart`
   (feature `claude-code-hooks`).

> **Seguridad**: nunca interpoles variables de shell dentro de `python3 -c "..."`.
> Pasalas por entorno con el `-c` en comillas simples.

## Tests

```bash
# sin config → la skill debe entrar en modo first-run
rm -f <datadir>/config.json
# con config → debe mostrar valores y ofrecer cambiar
```

## Changelog

- **1.0.0** — patrón extraído de `todo-config` en `todo-plugin`.
