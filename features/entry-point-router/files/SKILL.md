---
name: <plugin>-context
description: "Punto de entrada único de <plugin>. Lee el contexto (git, archivos, mensaje del usuario, historial) y decide qué escenario aplicar. Activar para cualquier flujo del plugin; nunca invocar sub-skills privadas directamente."
---

# <plugin> — Context (router)

Punto de entrada único. Elegí el escenario DESPUÉS de recopilar señales, nunca antes.

### Step 0 — Sesión activa
Si hay estado de sesión (`<datadir>/session-state.json`), fast-path: reutilizá contexto.

### Step 1 — Recopilar señales
Estado de git (repo, branch, diffs), archivos relevantes, mensaje del usuario.

### Step 2 — Historial
Consultá historial relevante si aplica.

### Step 3 — Detectar escenario
Leé los triggers de cada archivo en `scenarios/` y evaluálos contra las señales.

### Step 4+ — Delegar
Ejecutá el escenario correspondiente.

## Escenarios
Definidos en `scenarios/*.md`, cada uno con su trigger y qué hacer.
Para agregar un caso nuevo: nuevo archivo en `scenarios/`, sin tocar los demás.
