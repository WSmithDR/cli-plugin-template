# Feature: dual-review

## Qué hace

Revisión adversarial con **dos jueces ciegos en paralelo**: ambos buscan solo problemas en
el mismo target, se cruzan sus veredictos para separar lo **confirmado** (ambos lo marcan)
de lo **sospechoso** (se contradicen), se corrigen los confirmados, y se re-juzga.

## Por qué

Un solo reviewer pierde bugs y produce falsos positivos. Dos jueces independientes que no
ven el resultado del otro elevan la cobertura, y el cruce distingue lo real (coinciden) de
lo dudoso (discrepan), evitando arreglar ruido.

## Diferencia con `agent-pipeline`

El revisor de `agent-pipeline` valida un artefacto contra su **schema** (¿está bien
formado?). `dual-review` es revisión **adversarial de calidad/correctitud** del cambio (¿hay
bugs?), con dos jueces y re-juicio.

## El patrón

1. **Dos jueces en paralelo** (ver `parallel-agents`): cada uno recibe el mismo target con el
   prompt "sos un revisor adversarial, encontrá SOLO problemas". Severidad: CRITICAL /
   WARNING (real) / WARNING (teórico) / SUGGESTION.
2. **Tabla de veredicto**: Juez A | Juez B | Severidad | Estado.
   - **Confirmado**: ambos lo marcan.
   - **Sospechoso**: se contradicen.
3. **Fix**: un agente corrige los **confirmados** (CRITICAL y WARNING real).
4. **Re-juicio**: corré la revisión otra vez. Aprobado si: cero CRITICAL confirmados y cero
   WARNING reales confirmados. Teóricos y sugerencias no bloquean.

## Integración

1. Definí el prompt del juez (adversarial, solo problemas, con escala de severidad).
2. Despachá dos jueces en paralelo sobre el mismo target.
3. Armá la tabla de veredicto y separá confirmado/sospechoso.
4. Corregí confirmados y re-juzgá hasta aprobar o escalar.

## Tests

Pasá un cambio con un bug obvio y verificá que ambos jueces lo marcan (confirmado) y que el
re-juicio aprueba recién tras el fix.

## Changelog

- **1.0.0** — patrón de `gentle-pi` (judgment-day).
