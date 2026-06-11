---
name: <plugin>-vocab
description: "Guardián del vocabulario del plugin. Valida que todo término/estado/constante de dominio exista en config/vocabulary.json antes de usarlo. NUNCA inventar términos nuevos."
---

# <plugin> — Vocab

Fuente única de verdad: `config/vocabulary.json`.

## Regla
Antes de escribir cualquier status/señal/constante de dominio en archivos de control:
verificá que exista en `vocabulary.json`. Si no existe → registralo primero acá.
**NUNCA** inventes términos nuevos ni uses variantes (`pending` ≠ `PENDING`).

## Registrar un término
1. Abrí `config/vocabulary.json`.
2. Agregá el término en la sección correcta (`statuses`, `patterns`, `scenarios`…).
3. Si el término aparece en archivos auditables, asegurate de que `_scans` los cubra.

## Auditar (detección de valores no registrados)
Recorré los archivos declarados en `_scans` y reportá cualquier valor que no esté en
el vocabulario, indicando archivo y campo.
