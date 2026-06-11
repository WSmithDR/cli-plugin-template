# Feature: agent-authoring

## Qué hace

Convenciones para definir subagentes (`agents/<name>.md`): cuándo se invocan, qué tools
pueden usar, y cómo estructurar sus instrucciones para que produzcan una salida predecible.

## Por qué

Un subagente mal definido produce resultados inconsistentes o usa tools que no debería.
Un frontmatter claro con "when to use" hace que el orquestador lo elija bien, y el
scoping de tools acota lo que puede hacer (menos riesgo, más foco).

## Convenciones

### Frontmatter

```yaml
---
name: <agent-name-kebab>
description: <cuándo usar este agente — qué tarea resuelve, en qué situación>
tools: [Read, Grep, Glob]      # opcional: acotá a lo que el agente necesita
---
```

- `description` describe **cuándo** despacharlo, no solo qué hace.
- Acotá `tools` al mínimo necesario (un analizador read-only no necesita Write).

### Cuerpo (de lo general a lo específico)

```markdown
## Overview        — rol del agente en una frase
## Task            — qué debe lograr (resultado observable)
## Phases          — pasos ordenados, si el trabajo es multi-fase
## Output contract — el schema/forma exacta de lo que devuelve
## Constraints     — qué NO hacer, límites
```

### Contrato de salida

Si el agente alimenta a otro (pipeline) o a un script, definí el **schema exacto** de
su salida (campos requeridos, tipos). Ver feature `agent-pipeline`.

## Integración

1. Creá `agents/<name>.md` con frontmatter + cuerpo estructurado.
2. Acotá `tools`.
3. Si es parte de un pipeline, definí el contrato de salida explícito.

## Tests

Despachá el agente con una entrada de ejemplo y verificá que la salida respeta el
contrato declarado.

## Changelog

- **1.0.0** — convenciones de `understand-anything` (agents/) y `superpowers`.
