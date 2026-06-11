# Feature: entry-point-router

## Qué hace

Define un **único skill de entrada** que lee el contexto disponible (estado de git,
archivos, mensaje del usuario, historial) y decide qué escenario aplicar, delegando a
sub-skills privadas. El usuario invoca uno solo y el router resuelve el resto.

## Por qué

Si el usuario tiene que conocer 5–10 skills distintas y cuál usar cuándo, la fricción
es alta y los errores frecuentes. Centralizar el routing en un skill:
- Da un solo punto de entrada memorable.
- Hace la decisión de routing auditable y depurable en un solo lugar.
- Permite agregar escenarios sin romper los existentes.

## Integración

1. Creá el skill router `skills/<plugin>-context/SKILL.md` con pasos:
   - **Step 0**: revisá si hay sesión/estado activo (fast-path: reutilizá contexto).
   - **Step 1**: recopilá señales (git repo, branch, diffs, archivos, mensaje).
   - **Step 2**: consultá historial relevante si aplica.
   - **Step 3**: **detectá el escenario** leyendo los triggers de cada archivo en
     `scenarios/` y evaluándolos contra las señales.
   - **Step 4+**: delegá al escenario correspondiente.
2. Definí los escenarios como archivos en `skills/<plugin>-context/scenarios/`:
   ```
   scenarios/
     01-<caso-a>.md   ← trigger + qué hacer
     02-<caso-b>.md
   ```
3. Regla para el agente (en `AGENTS.md`/`CLAUDE.md`):
   > El escenario se elige DESPUÉS de recopilar señales, nunca antes. Nunca invocar
   > una sub-skill privada directamente como respuesta al usuario: el entry point es
   > el router.
4. Persistí estado de sesión (ej. `<datadir>/session-state.json`) para el fast-path.

## Tests

Simulá distintos contextos (repo con diffs, mensaje "enseñame X", rama existente) y
verificá que el router selecciona el escenario correcto.

## Changelog

- **1.0.0** — patrón extraído de `ankify` (anki-context + scenarios/).
