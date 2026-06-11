---
name: plugin-feature
description: Use when you want to integrate a specific cli-plugin-template feature into the current plugin (e.g. "add versioning", "integrate health-check"). Reads the feature's README and adapts its files to this project.
---

# plugin-feature — integrar un feature del catálogo

Integra un feature nombrado en el plugin actual, adaptándolo (no copiando a ciegas).

## Proceso

1. Resolvé el nombre del feature. Si es ambiguo, listá coincidencias de
   `${CLAUDE_PLUGIN_ROOT}/CATALOG.md` y preguntá.
2. Verificá dependencias: leé `${CLAUDE_PLUGIN_ROOT}/features/<x>/meta.yml` → `depends_on`.
   Si falta una dependencia en el proyecto, avisá y ofrecé integrarla primero.
3. Leé `${CLAUDE_PLUGIN_ROOT}/features/<x>/README.md` — seguí su sección **Integración**.
4. Copiá/adaptá los archivos de `${CLAUDE_PLUGIN_ROOT}/features/<x>/files/` al proyecto,
   ajustando: rutas, nombre del plugin, idioma, datadir. NO pegues placeholders sin reemplazar.
5. Corré los pasos de verificación que el README indique (`## Tests`).
6. Resumí qué se agregó y qué quedó por ajustar a mano.

## Reglas

- Respetá las convenciones existentes del proyecto (no reestructures de más).
- Si el feature ya está parcialmente presente, integrá solo lo que falta.
- No commitees por el usuario salvo que lo pida explícitamente.
