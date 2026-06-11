# Feature: context-batching

## Qué hace

Dos técnicas para escalar a entradas grandes:
1. **Batching** — partir el trabajo en lotes que entran en la ventana de contexto,
   agrupando ítems relacionados.
2. **Incremental** — reprocesar solo lo que cambió, usando fingerprints.

## Por qué

Procesar un codebase grande o muchos ítems de una vez revienta el contexto y es caro.
Lotear mantiene cada paso acotado; el reprocesado incremental hace que correr de nuevo
sea casi gratis. Vuelve escalable algo como `todo-audit` sobre repos grandes.

## Patrones

### Batching

- Agrupá ítems **relacionados** en el mismo lote (alta interdependencia juntos) para
  minimizar referencias cruzadas entre lotes.
- Pasá un "mapa de vecinos" mínimo entre lotes (qué existe en otros lotes: rutas,
  símbolos) para que cada lote razone sin conocimiento global.
- Procesá lote por lote; combiná al final (ver `agent-pipeline` para el merge).

### Incremental con fingerprints

```
fingerprints.json: { "<ruta>": { "hash": "<sha256 del contenido>", "struct": [...] } }
```

- Al re-correr, compará con `git diff` + el hash guardado.
- Reprocesá solo los ítems cuyo hash (o estructura) cambió; saltá el resto.
- Guardá el fingerprint actualizado tras procesar.

## Integración

1. Definí el criterio de agrupamiento de lotes (por carpeta, por grafo de imports, etc.).
2. Generá los lotes con un script (ver `bundled-scripts`), no a mano.
3. Mantené `fingerprints.json` en el datadir; consultalo antes de reprocesar.

## Tests

Corré dos veces sin cambios → la segunda no reprocesa nada. Cambiá un ítem → solo ese se
reprocesa.

## Changelog

- **1.0.0** — patrón de `understand-anything` (compute-batches, fingerprints, auto-update).
