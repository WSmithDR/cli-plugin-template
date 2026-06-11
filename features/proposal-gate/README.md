# Feature: proposal-gate

## Qué hace

Interpone una **aprobación humana explícita** antes de cualquier acción irreversible
(crear registros, llamar una API que escribe, borrar en masa). La acción se materializa
primero como un archivo de propuesta `.md`; el usuario la aprueba, edita o descarta.

## Por qué

Una acción irreversible ejecutada por error (crear 50 registros, borrar datos) no tiene
vuelta atrás. El gate convierte la acción en un artefacto revisable:
- **Recuperación**: las propuestas rechazadas quedan como archivo para análisis.
- **Auditoría**: historial de decisiones.
- **Iteración**: editar la propuesta sin reiniciar el flujo.

## Integración

1. Definí un directorio `proposals/` y una skill `skills/<plugin>-propose/SKILL.md`.
2. La regla central (ponela en `AGENTS.md`/`CLAUDE.md` como prioridad alta):
   > NUNCA llamar la acción irreversible directamente. Todo flujo de creación pasa por
   > `<plugin>-propose` → aprobación explícita del usuario → ejecución.
3. La skill escribe un archivo con frontmatter de estado:
   ```markdown
   ---
   status: pending | approved | discarded
   <campos de la acción>
   ---
   # Propuesta
   ... contenido revisable ...
   ```
4. El flujo:
   1. Skill genera la propuesta → `proposals/<hash>/<slug>.md` (`status: pending`).
   2. Usuario revisa el archivo: aprueba / edita / descarta.
   3. Si aprueba → la skill parsea el archivo y ejecuta la acción real.
   4. Si descarta → el archivo queda como registro (`status: discarded`).
5. Los `status` válidos deben estar en el vocabulario (ver feature
   `vocabulary-guardian`).

## Tests

Verificá que la acción real **no** se dispara mientras el estado sea `pending`, y que
solo corre tras pasar a `approved`.

## Changelog

- **1.0.0** — patrón extraído de `ankify` (anki-propose + proposals/).
