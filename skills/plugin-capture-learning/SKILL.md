---
name: plugin-capture-learning
description: "Captura proactivamente un descubrimiento de compatibilidad multi-CLI detectado durante desarrollo de un plugin y lo guarda como feedback signal:discovery en el store de evolución. No requiere intervención del usuario — el agente lo invoca cuando identifica el aprendizaje."
---

# plugin-capture-learning — captura proactiva de descubrimientos multi-CLI

Detecta automáticamente cuando, durante desarrollo de un plugin downstream, aparece
información sobre diferencias de compatibilidad entre CLIs (hooks, tools, schemas,
limitaciones). Extrae la señal y la guarda como `signal: discovery` para que
`plugin-hotpatch` la procese o para migrarla al template.

No espera instrucción del usuario — el router `plugin-dev` la activa al detectar
aprendizaje multi-CLI en la conversación.

---

## Step 1: Extraer los campos del contexto

Del diálogo actual (sin preguntar al usuario), extraé:

| Campo | Fuente | Requerido |
|---|---|---|
| `plugin` | nombre del plugin que se está desarrollando | sí |
| `discovery` | qué se aprendió (1-2 líneas) | sí |
| `cli` | CLI(s) involucrado(s): claude-code, opencode, gemini-cli, codex, cursor, copilot | sí |
| `context` | en qué situación apareció (hook, tool, schema, limitación) | opcional |
| `recommendation` | qué hacer en el plugin para manejar la diferencia | opcional |
| `applies_to_template` | ¿esto debería documentarse en el template para futuros plugins? | sí (default: false) |

### Señales de que hay un descubrimiento

- Se mencionan diferencias entre CLIs: "en X no existe", "Y lo hace distinto", "Z no soporta"
- Se resuelve un problema de compatibilidad: "encontré que OpenCode usa tool.execute.after"
- Se documenta una limitación: "Gemini no tiene Stop hook"
- Se compara comportamiento: "en Claude Code funciona, en Copilot no"

### Si no hay suficiente información

Si el contexto no tiene todos los campos, invocá `plugin-feedback-log` como fallback
(con signal `friccion` o `escenario`) en vez de `plugin-capture-learning`. Mejor perder
un discovery que guardar uno incompleto.

---

## Step 2: Generar slug

```
slug = discovery → lowercase → no-alnum a '-' → truncar 40 → quitar '-' extremos
```

Verificar que no exista:
```bash
python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" feedback list --plugin "$PLUGIN" | grep "<slug>"
```

Si existe: sufijo `-2`, `-3`, etc.

---

## Step 3: Guardar como feedback (signal: discovery)

```bash
plugin=$(python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" registry resolve "<namespace>")
[ -z "$plugin" ] && echo "Plugin no registrado. Usá plugin-register primero." && exit 1

python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" feedback save "$plugin" "<slug>" - << 'LEARNING_EOF'
---
name: feedback-<slug>
description: "<discovery — una línea>"
plugin: <plugin>
applied: false
needs_patch: false
source: plugin-capture-learning
signal: discovery
cli: <cli(s) involucrados>
applies_to_template: <true|false>
---

## Descubrimiento
<discovery>

## Contexto
<context — en qué situación apareció>

## Recomendación
<recommendation — qué hacer en el plugin>

## CLI(s)
<cli>
LEARNING_EOF
```

---

## Step 4: Si aplica al template, sugerir migración

Si `applies_to_template: true`:

```bash
TOOL_MAPPING="$CLAUDE_PLUGIN_ROOT/features/multi-cli-compat/files/tool-mapping.md"
if [ -f "$TOOL_MAPPING" ]; then
    echo ""
    echo "→ Este descubrimiento aplica al template cli-plugin-template."
    echo "  Migración sugerida: agregar entrada a:"
    echo "    $TOOL_MAPPING"
    echo "  O crear un PR contra cli-plugin-template para que futuros plugins lo hereden."
fi
```

---

## Step 5: Confirmar

```
✓ Descubrimiento capturado
  Plugin:  <plugin>
  Slug:    <slug>
  CLI:     <cli>
  Signal:  discovery
  Store:   <data_dir>/<plugin>/feedbacks/feedback_<slug>.md
  Template: <applies_to_template — si true, sugerir migración>
```
