# Feature: externalized-config

## Qué hace

Saca las reglas, umbrales y patrones de comportamiento del plugin del código y los pone
en archivos JSON en `config/`, leídos en tiempo real.

## Por qué

Un umbral hardcodeado (`if lines > 150`) obliga a editar código y redeployar para
ajustarlo, y esconde el porqué de una decisión. Externalizarlo hace el comportamiento
ajustable sin tocar código y deja las reglas a la vista para auditar: "¿por qué hizo
split en 150 líneas?" → `config/thresholds.json`.

## Diferencia con `project-config`

- `project-config` → preferencias **del usuario por proyecto** (config.json en el datadir).
- `externalized-config` → reglas de **comportamiento del plugin**, versionadas con el repo.

## Integración

1. Creá archivos en `config/` por tipo de regla:
   ```
   config/
     thresholds.json          { "diff_split_lines": 150, "min_chars": 100 }
     <dominio>-rules.json      reglas de clasificación/validación
     keywords.json             mapeos keyword → categoría
   ```
2. Cargálos desde un módulo central (`bin/lib/config.py` si usás el feature
   `data-gateway`), nunca leyendo el JSON disperso en cada skill.
3. Opcional: agregá metadata `_hotpatch` a cada config (ver feature `growth-engine`)
   para que el motor sepa quién la consume.

## Tests

Cambiá un umbral en el JSON y verificá que el comportamiento cambia sin tocar código.

## Changelog

- **1.0.0** — patrón extraído de `ankify` (config/thresholds.json, signal-detection-rules.json, etc.).
