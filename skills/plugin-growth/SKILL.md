---
name: plugin-growth
description: "Dashboard de evolución de tus plugins: muestra registrados, feedbacks pendientes/aplicados y propuestas por status, todo de un vistazo. Punto de partida para procesar pendientes."
when_to_use: "Invocar cuando el usuario pide ver el estado de evolución: 'qué hay pendiente en mis plugins', 'mostrame el dashboard', 'cómo viene la evolución', 'qué feedbacks tengo sin aplicar'."
---

# plugin-growth — dashboard de evolución

Vista consolidada del store de evolución (registry + feedbacks + propuestas) across todos
tus plugins. La agregación es determinista (la hace `bin/cpt status`); esta skill la presenta
y ofrece el siguiente paso.

---

## Step 1: Reporte

```bash
python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" status
```

Para un solo plugin: `--plugin <name>`. Para consumir en código: `--json`.

Mostrar la tabla tal cual. Si el store está vacío → sugerir registrar un plugin
(`plugin-register`).

---

## Step 2: Drill-down (a pedido)

Según lo que el usuario quiera ver:

- **Feedbacks pendientes de un plugin:**
  ```bash
  python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" feedback list --plugin <name> --pending
  python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" feedback show <name> <slug>
  ```
- **Propuestas por status:**
  ```bash
  python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" proposal list --plugin <name> --status pending
  python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" proposal show <name> <slug>
  ```

---

## Step 3: Siguiente acción

- Si hay **feedbacks pendientes** → ofrecer procesarlos: invocar `Skill("plugin-hotpatch")`.
- Si hay **propuestas `approved` sin aplicar** (caso raro: aprobada pero no aplicada) →
  retomar con `plugin-hotpatch` desde Step 5.
- Si todo está en cero → "Nada pendiente. Todos tus plugins al día."

Esta skill **no modifica** nada: solo lee y enruta. El parcheo lo hace `plugin-hotpatch`
(con su gate).
