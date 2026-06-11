# Feature: claude-code-hooks

## Qué hace

Patrones para los hooks de Claude Code (`hooks/hooks.json` + scripts en `bin/hooks/`):
auto-setup en `SessionStart`, reacción a fallos en `PostToolUse`, y la convención de
exit codes que determina si Claude **debe** reaccionar o no.

## Por qué

Sin la convención correcta de exit codes, los mensajes de un hook "aparecen en el
transcript" pero Claude los ignora y sigue. El detalle que lo cambia todo:

| Exit | Salida | Efecto |
|---|---|---|
| `0` + stdout | informativo | Claude puede ignorarlo y continuar |
| `2` + stderr | **bloqueante** | Claude debe leer y reaccionar antes de seguir |

## Patrones

### 1. SessionStart — auto-setup idempotente

Detecta estado faltante e instala/avisa. Idempotente: si ya está, sale en silencio.

```bash
#!/bin/bash
set -euo pipefail
[ ! -d ".midata" ] && exit 0          # nada que hacer en este proyecto

# Auto-instalar git hook (ver gotcha CLAUDE_PLUGIN_ROOT abajo)
if [ -d ".git" ] && [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    dst=".git/hooks/pre-commit"
    src="${CLAUDE_PLUGIN_ROOT}/bin/hooks/pre-commit.sh"
    if [ ! -L "$dst" ] || [ "$(readlink "$dst")" != "$src" ]; then
        ln -sf "$src" "$dst"
        echo "SETUP: git hook instalado"     # exit 0 → informativo
    fi
fi

# Detectar config faltante → bloqueante
[ -f ".midata/config.json" ] && exit 0
echo "CONFIG-MISSING: falta config.json. Invocar Skill('mi-config')." >&2
exit 2
```

### 2. PostToolUse(Bash) — reaccionar a un comando fallido

```bash
#!/bin/bash
set -euo pipefail
TOOL_INFO=$(cat)        # el hook recibe JSON por stdin
IS_ERROR=$(echo "$TOOL_INFO" | python3 -c '
import json,sys
d=json.load(sys.stdin); tr=d.get("tool_response",{})
print("true" if (isinstance(tr,dict) and tr.get("is_error")) else "false")
' 2>/dev/null || echo false)
[ "$IS_ERROR" != "true" ] && exit 0
# ... evaluar si el fallo merece una acción, escribir a >&2 y exit 2 si sí
```

### 3. Gotcha: `CLAUDE_PLUGIN_ROOT`

`${CLAUDE_PLUGIN_ROOT}` **solo está set cuando el plugin se instaló via
`claude plugin install`**. Si se clonó manual, está vacío y un comando como
`bash ${CLAUDE_PLUGIN_ROOT}/bin/hooks/x.sh` se vuelve `bash /bin/hooks/x.sh` → falla
silenciosa. Reglas:

- Accedé siempre con default expansion: `${CLAUDE_PLUGIN_ROOT:-}`.
- Si está vacío, degradá con gracia (`exit 0`), no falles.
- Una skill de health check (ver feature `health-check`) detecta y reporta esta condición.

## Integración

1. Creá `hooks/hooks.json` declarando los eventos (estructura):
   ```json
   {
     "hooks": {
       "SessionStart": [{ "hooks": [{ "type": "command",
         "command": "bash ${CLAUDE_PLUGIN_ROOT}/bin/hooks/session-start.sh" }] }],
       "PostToolUse": [{ "matcher": "Bash", "hooks": [{ "type": "command",
         "command": "bash ${CLAUDE_PLUGIN_ROOT}/bin/hooks/error-checker.sh" }] }]
     }
   }
   ```
2. Escribí los scripts en `bin/hooks/` aplicando la convención exit 2/stderr.
3. Recordá: los hooks se cargan al iniciar sesión — reiniciá Claude Code para probarlos.

## Tests

Usá el arnés del feature `git-hooks` (tmpdir aislado) para verificar cada exit code:
```bash
# .midata/ sin config → exit 2 + CONFIG-MISSING
mkdir -p .midata && CLAUDE_PLUGIN_ROOT="" bash bin/hooks/session-start.sh; echo $?
```

## Changelog

- **1.0.0** — patrones extraídos de `todo-plugin` (session-start, error-checker).
