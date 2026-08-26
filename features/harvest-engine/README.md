# Feature: harvest-engine

## Qué hace

Escaneo y cosecha **autónoma** de plugins de terceros. Cada 24h el scheduler
dispara harvest scan + harvest run: scan descubre qué plugins tiene el usuario
instalados en otros CLIs (Claude Code, Gemini CLI, Kiro), los normaliza a un
IR canónico, y run ejecuta un panel LLM que analiza cada plugin para extraer
aprendizajes. Los resultados se comparan con la scorecard para priorizar
modelos gratuitos por agreement rate.

## Por qué

El usuario instala plugins en múltiples CLIs pero solo desarrolla activamente
en cli-plugin-template. Los otros plugins acumulan conocimiento que acá no
llega. Harvest lo cosecha automáticamente, sin que el usuario tenga que
reportar nada.

## Flujo

```
harvest scan → pending.json (plugins nuevos o cambiados)
     ↓
harvest run  → dossier por plugin → panel LLM → consensus → learnings.json
                                    ↓
                         scorecard.json (modelo, agreed, latency)
```

## IR canónico (v1)

Normaliza la estructura de un plugin a un formato único:

```json
{
  "ir_version": 1,
  "cli": "claude-code",
  "plugin_name": "shannon",
  "plugin_version": "0.3.0",
  "hash": "abc123...",
  "features": {
    "has_skills": true, "has_hooks": true, "has_mcp": false, ...
  },
  "skills": [{"name": "...", "trigger": "...", "path": "..."}],
  "scripts": ["..."]
}
```

El hash es determinista sobre los campos que importan (sin paths absolutos).

## Comandos

```bash
# Descubrir plugins, encolar pendientes
cpt harvest scan --json

# Ejecutar análisis con panel LLM (3 modelos gratuitos, majority vote)
cpt harvest run --panel-size 3 --threshold majority --json

# Ver estado: cola + scorecard + homologías
cpt harvest status --json

# Modelos gratuitos detectados en opencode.json
cpt harvest models --json
```

## Scheduler

```bash
# Instalar systemd timer (una vez al día a las 9:00)
bash bin/harvest-install.sh

# Dry-run: qué haría
bash bin/harvest-install.sh --dry-run

# Desinstalar
bash bin/harvest-install.sh --uninstall
```

También instala path triggers en `~/.claude`, `~/.config/opencode`,
`~/.gemini`, `~/.kiro` para disparar al instalar un plugin.

## Scorecard

`scorecard.json` registra por modelo: agreement rate, latencia, fallos.
`pick_models(n)` devuelve los n mejores (anti-laggard). Decae con `decay=0.9`.

## Anti-payment

Si tras filtrar por `providers[].free` + excluded_models no queda ningún
modelo gratuito, harvest run aborta con warning. Nunca usa modelos de pago.

## Fallback

Si `cpt harvest run` se pierde (laptop cerrada, systemd no disponible),
al detectar `pending.json` con antigüedad >12h se ejecuta catch-up antes
de scan normal.

## Integración

Requiere `learning-system` y `growth-engine` (reusa registry + store).

Los archivos clave están en `bin/lib/harvest/`:
- `ir.py` — IR canónico v1 + hash
- `scan.py` — autodetección multi-CLI + cola
- `dossier.py` — resumen de archivos
- `runner.py` — panel LLM + scoring
- `consensus.py` — agregación majority/strict
- `scorecard.py` — preferencia por agreement rate

CLI: `cpt harvest scan|run|status|models` (agregado a `bin/cpt`).
Scheduler: `bin/harvest-install.sh` (systemd timer + path triggers).

## Tests

```bash
bash bin/test-harvest.sh
```

Cubre: paths, IR canónico, hash determinista, consenso majority/strict,
scorecard degradación, harvest scan con dedup, dossier anti-ruido,
runner dry-run, CLI harvest, harvest-install dry-run.
