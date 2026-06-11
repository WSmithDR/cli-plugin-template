# Feature: vocabulary-guardian

## Qué hace

Mantiene un archivo `config/vocabulary.json` como **fuente única de verdad** de los
términos, estados y constantes del dominio del plugin. Una skill guardián valida
cualquier término nuevo antes de usarlo; un escáner audita los archivos en busca de
valores no registrados.

## Por qué

Sin control, los términos divergen: `status_pending` vs `pending` vs `PENDING`. Un
vocabulario centralizado evita inconsistencias y obliga a registrar un término **una
sola vez** para que todas las skills lo lean igual.

## Integración

1. Creá `config/vocabulary.json`:
   ```json
   {
     "statuses": { "<entidad>": ["pending", "approved", "discarded"] },
     "patterns": { "<grupo>": ["valor-a", "valor-b"] },
     "_scans": {
       "statuses": [
         { "glob": "proposals/**/*.md", "type": "frontmatter", "field": "status" },
         { "glob": "data/*.json", "type": "json", "field": "status" }
       ]
     }
   }
   ```
2. Creá la skill guardián `skills/<plugin>-vocab/SKILL.md` con la regla:
   > Antes de escribir cualquier status/señal/constante de dominio en archivos de
   > control, verificá que exista en `vocabulary.json`. Si no existe → registralo
   > primero. NUNCA inventes términos nuevos.
3. Implementá el escáner que usa `_scans` para recorrer los archivos declarados y
   alertar si encuentra un valor fuera del vocabulario.
4. Referenciá la regla desde el archivo de instrucciones del plugin (`AGENTS.md`/
   `CLAUDE.md`) para que el agente la respete siempre.

## Tests

Insertá un status inválido en un archivo cubierto por `_scans` y verificá que el
escáner lo detecta.

## Changelog

- **1.0.0** — patrón extraído de `ankify` (anki-vocab + config/vocabulary.json).
