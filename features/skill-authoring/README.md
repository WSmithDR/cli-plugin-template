# Feature: skill-authoring

## Qué hace

Convenciones para escribir `SKILL.md` que el agente **encuentra y dispara** en el
momento correcto, y que lee de forma eficiente (progressive disclosure).

## Por qué

Una skill que no se dispara es inútil. El problema más común no es el contenido sino
el `description`: si describe *qué hace* en vez de *cuándo usarse*, el agente no la
matchea. (Este repo nació en parte de ese problema con triggers.)

## Convenciones

### Frontmatter (CSO — Claude Search Optimization)

```yaml
---
name: kebab-case-con-guiones        # solo letras, números, guiones
description: Use when <condiciones y síntomas concretos de activación>
---
```

- `description` **empieza con "Use when…"** y describe SOLO cuándo activar, no qué hace.
- Incluí síntomas, situaciones y sinónimos buscables (ej. "test, fail, error, bug").
- Malo: `"Ayuda con debugging"`. Bueno: `"Use when encountering any bug, test failure
  or unexpected behavior, before proposing a fix"`.

### Estructura del cuerpo (progressive disclosure)

```markdown
# Nombre

## Overview
Principio central en 1–2 frases.

## When to use
Bullets de síntomas + cuándo NO usar. Flowchart en Graphviz DOT si la decisión no es obvia.

## <Concepto central>
El proceso/contenido. Secciones escaneables.

## Red Flags — STOP
| Pensamiento | Realidad |
|---|---|
| Racionalización común | Lo que es verdad |
```

Poné lo más usado arriba; material extenso o reusable va a archivos aparte
(`references/`, `*-prompt.md`).

## Integración

1. Escribí el frontmatter con `description: Use when …`.
2. Estructurá el cuerpo de lo general a lo específico.
3. Si la skill aplica reglas/triggers de dominio, listá las frases de activación.
4. Verificá descubrimiento (abajo).

## Tests

Describí un escenario donde la skill debería dispararse y confirmá que el `description`
contiene las palabras que un usuario usaría. Si no matchea, ajustá el `description`.

## Changelog

- **1.0.0** — convenciones extraídas de `superpowers` (writing-skills + CSO).
