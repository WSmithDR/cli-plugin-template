# Feature: agent-pipeline

## Qué hace

Encadena agentes especializados que se pasan **artefactos estructurados** (no prosa),
cada uno con un rol y un contrato de salida definido. Incluye dos patrones clave: la
fase de dos etapas (determinista + semántica) y el agente revisor/QA.

## Por qué

Un análisis complejo (scanear → analizar → ensamblar → revisar) es más fiable si cada
etapa tiene un contrato claro y la salida de una alimenta la siguiente vía un schema, no
texto libre. Permite procesar en partes sin perder coherencia y validar la calidad por agente.

## Patrones

### 1. Contrato de artefacto por agente

Cada agente declara el **schema JSON** exacto que produce (campos requeridos, tipos). El
siguiente agente (o un script) lo consume sin ambigüedad.

```
scanner → inventory.json → analyzer → graph.partial.json → merger → graph.json → reviewer
```

### 2. Dos fases: determinista + semántica

- **Fase 1 (script)**: lo mecánico y fiable — enumerar archivos, contar, extraer
  estructura, aplicar reglas. (Ver feature `bundled-scripts`.)
- **Fase 2 (LLM)**: lo que requiere juicio — resúmenes, clasificación, relaciones
  semánticas. No dupliques en el LLM lo que el script ya resolvió.

### 3. Agente revisor / QA

Un agente cuyo único trabajo es **validar la salida de otro** antes de aceptarla: corre
checks (schema, integridad, completitud), produce `issues[]`/`warnings[]`, y aprueba o
rechaza. Un merge automático maneja lo común; el revisor recupera los casos borde.

## Integración

1. Dividí el trabajo en etapas con un rol por agente (ver `agent-authoring`).
2. Definí el contrato JSON de salida de cada etapa.
3. Separá fase determinista (script) de fase semántica (LLM).
4. Agregá un agente revisor que valide el artefacto final contra su schema.

## Tests

Corré el pipeline sobre una entrada de ejemplo y verificá que cada artefacto intermedio
respeta su schema, y que el revisor detecta un artefacto corrupto inyectado a propósito.

## Changelog

- **1.0.0** — patrón de `understand-anything` (pipeline de agentes, two-phase,
  graph-reviewer / assemble-reviewer).
