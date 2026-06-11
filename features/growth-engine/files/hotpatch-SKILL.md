---
name: <plugin>-hotpatch
description: "Motor de crecimiento del plugin: procesa feedback pendiente, articula el gap, mapea el archivo correcto, aplica el parche y commitea. Invocar cuando convenga procesar lo acumulado o ante una corrección directa."
---

# <plugin> — Hotpatch

Procesa el feedback capturado y mejora el plugin.

## Proceso
- **Step 0** — detectá feedbacks pendientes (`applied: false`) en `<datadir>/memory/`.
- **Step 1** — articulá el gap concreto.
- **Step 2** — mapeá el archivo correcto a tocar. Usá la metadata `_hotpatch` de los
  archivos de control (`owner`, `consumers`) para ubicarlo.
- **Step 3** — proponé el fix.
- **Step 4** — aplicá el parche.
- **Step 5** — marcá `applied: true` y commiteá.

## Metadata `_hotpatch`
Cada archivo de control lleva:
```json
"_hotpatch": {
  "purpose": "qué hace",
  "owner": "hotpatch directo | skill-específico",
  "consumers": ["skills/...", "config/..."]
}
```

## Loop con el catálogo
Si el fix resulta reusable para cualquier plugin, promovélo al catálogo
`cli-plugin-template` siguiendo su `CONTRIBUTING.md`.
