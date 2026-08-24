# Detección de datos embebidos desacoplables — Design

**Fecha:** 2026-08-24 · **Estado:** aprobado en sesión

## Problema

Los plugins propios acumulan datos hardcodeados dentro de su código (tuplas de
keywords, umbrales, allowlists) que evolucionan peor que si vivieran en un store:
cambiarlos exige editar código, no hay historial de uso, y otros procesos no los
pueden alimentar. El caso resuelto a mano: `FRICTION_KEYWORDS` en
`detect-pending-feedback.py` → `friction-lexicon.json` + `cpt feedback learn`.

## Objetivo

Que `audit-catalog-gaps.py` detecte candidatos a desacoplar y los liste, para que
el usuario decida cuáles externalizar siguiendo el patrón ya existente
(store + verbo CLI + consumidor).

## Alcance

- Solo **datos embebidos**: tuplas/listas de strings literales (≥4 ítems) y
  constantes numéricas con nombre de umbral.
- Archivos escaneados: `.py` bajo `bin/`+`hooks/`, `.ts` bajo el árbol,
  excluyendo rutas con `test` en cualquier parte. Respeta `SKIP_DIRS`.
- Fuera de alcance: lógica extraíble, skills/docs, sugerencias automáticas de
  migración, cambios al modo `--json` existente.

## Diseño

1. `find_embedded_data(root) -> list[dict]` en `audit-catalog-gaps.py`:
   escanea asignaciones a constantes MAYÚSCULAS (`NAME = [|( ... ]|)`) contando
   strings literales en el cuerpo hasta el cierre; reporta si ≥4. Aparte,
   nombres que matcheen `MAX_*`, `*_THRESHOLD`, `*_LIMIT`, `*UMBRAL*`
   asignados a un número. Devuelve `{file, line, name, detail}` ordenado.
2. Sección nueva al final de la salida texto del audit (después de la tabla):
   ```
   DATOS EMBEBIDOS DESACOPLABLES — N candidato(s)
      archivo:línea · NOMBRE (n ítems)
      → patrón de referencia: friction-lexicon.json + cpt feedback learn
   ```
   Cap de 8 filas visibles. No altera la tabla ni los exit codes; `--json` queda
   como está (v1).

## Trade-offs aceptados

- Heurística con falsos positivos posibles (strings con paréntesis/corchetes
  dentro, constantes en comentarios): el costo es una fila de más en un reporte
  informativo, no una acción automática — se filtra a ojo.
- El juicio de "vale la pena desacoplar" sigue siendo humano/agente; esto solo
  encuentra candidatos. La interpretación por LLM queda como extensión futura
  (skill plugin-audit).
