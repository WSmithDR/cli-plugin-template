# Feature: data-gateway

## Qué hace

Centraliza **toda** la persistencia en un único punto de contacto. Las skills nunca
escriben a disco directamente: invocan un CLI unificado (`bin/<plugin> data <entidad>
<operación>`) respaldado por módulos Python en `bin/lib/`.

## Por qué

Si 50 skills escriben archivos a mano, cambiar el backend (FS → SQLite → API remota)
significa editar 50 skills. Con un gateway, cambiás **un** archivo y el contrato de
datos queda en un solo lugar — más fácil de auditar, loguear y validar.

## Integración

1. Creá un CLI unificado `bin/<plugin>` (Python con argparse) con subcomandos:
   `data`, y los que necesites (`workflow`, `git`, `dev`…).
2. En `bin/lib/` separá responsabilidades:
   - `gateway.py` — operaciones CRUD por entidad (save/load/list/delete).
   - `paths.py` — resolución de rutas (datadir, hashes de proyecto). Centralizá acá
     dónde viven los datos (ej. `~/.local/share/<plugin>/`).
   - `config.py` — carga de configs JSON.
3. Las skills invocan así (nunca `echo > archivo`):
   ```bash
   python3 "$PLUGIN_ROOT/bin/<plugin>" data proposals save "<hash>" "<slug>" "<content>"
   ```
4. Resolvé `PLUGIN_ROOT` con un helper (ver gotcha `CLAUDE_PLUGIN_ROOT` en el feature
   `claude-code-hooks`).

## Regla de oro

> Ninguna skill conoce rutas de disco. Si una skill arma un path, ese path debería
> vivir en `paths.py`.

## Tests

Mockeá `bin/<plugin>` y verificá que las skills funcionan sin tocar disco real.
Cambiá la implementación de `gateway.py` (ej. de FS a SQLite) y confirmá que ninguna
skill necesita cambios.

## Changelog

- **1.0.0** — patrón extraído de `ankify` (bin/ankify + bin/lib/).
