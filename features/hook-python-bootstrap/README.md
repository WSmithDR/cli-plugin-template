# Feature: hook-python-bootstrap

## Qué hace

Un shim de shell que localiza un intérprete Python 3 funcional y ejecuta tu hook Python con
él, manejando las diferencias entre sistemas: `python3` vs `python` vs `py -3`, versión
mínima, encoding UTF-8 y conversión de rutas en Windows/Git-Bash.

## Por qué

Un hook que llama `python3` directo falla en máquinas donde el binario se llama distinto
(Windows, algunos macOS con el stub de la App Store), o donde la versión es muy vieja para
tu código. El shim hace que el hook "simplemente funcione" sin que cada usuario configure su
entorno.

## Integración

1. Copiá `files/py-hook.sh` a `hooks/py-hook.sh` y hacelo ejecutable.
2. En `hooks.json`, invocá tus hooks Python **a través** del shim:
   ```json
   { "type": "command",
     "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/py-hook.sh ${CLAUDE_PLUGIN_ROOT}/hooks/mi_hook.py" }
   ```
3. Ajustá la versión mínima si tu hook la requiere (por defecto 3.8).

## Tests

Corré el shim apuntando a un hook trivial y verificá que ejecuta con el Python disponible y
sale 0.

## Changelog

- **1.0.0** — patrón de `security-guidance` (sg-python.sh).
