# Feature: autonomous-agent

## Qué hace

Define un agente que actúa **proactivamente** sobre lo recién modificado, sin esperar que el
usuario lo invoque — y acotado a los cambios de la sesión actual para no barrer todo el repo.

## Por qué

Algunas tareas (simplificar código apenas se escribe, revisar un cambio) tienen más valor si
ocurren solas, en el momento, sin fricción de "¿querés que lo haga?". El acotamiento a lo
reciente evita que el agente se desboque sobre código que nadie tocó.

## Diferencia con un agente normal

`agent-authoring` cubre cómo definir un agente que el orquestador **invoca**. Este es para
agentes de comportamiento **proactivo y continuo**, disparados por la actividad, no por un pedido.

## Patrón

```yaml
---
name: <agent-name>
description: <tarea> — operate autonomously and proactively, acting immediately after code is written
model: opus          # ojo: model explícito rompe multi-CLI (ver gotcha)
---

## Scope
Solo actuá sobre código modificado/tocado en la SESIÓN actual. No barras el codebase entero.

## Behavior
<qué transformación/revisión aplicar, de forma autónoma>
```

## Gotchas

- **Acotá el scope** a lo reciente, siempre. Un agente proactivo sin límite es peligroso.
- **`model:` explícito** (ej. `opus`) ata el agente a Claude Code → rompe otros CLIs. Si
  querés multi-CLI, omitilo (ver `multi-cli-compat`). Es un trade-off consciente: potencia vs portabilidad.
- Combinable con `advanced-hooks` (PostToolUse) para disparar el comportamiento tras edits.

## Integración

1. Definí el agente con instrucción proactiva + scope acotado a la sesión.
2. Decidí: ¿`model:` fijo (potencia, solo Claude Code) u omitido (portable)?
3. Opcional: conectá un hook PostToolUse(Edit|Write) para activarlo tras cambios.

## Tests

Modificá un archivo y verificá que el agente actúa solo, y que NO toca archivos que no se
modificaron en la sesión.

## Changelog

- **1.0.0** — patrón de `code-simplifier`.
