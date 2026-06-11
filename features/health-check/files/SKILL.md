---
name: <plugin>-health
description: "Verifica que <plugin> está bien integrado: versión, skills, hooks, MCPs y estado del proyecto. Correr tras instalar/actualizar o para diagnosticar."
---

# <plugin> — Health Check

Reportá cada chequeo con ✓/✗.

### 1. Versión
```bash
cat "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(f"<plugin> v{d[\"version\"]}")'
```
Si `CLAUDE_PLUGIN_ROOT` está vacío → el plugin no se instaló via `claude plugin install`.
Reportar y dar el comando correcto.

### 2. Skills
```bash
ls "${CLAUDE_PLUGIN_ROOT}/skills/" 2>/dev/null
```

### 3. Hooks
```bash
cat "${CLAUDE_PLUGIN_ROOT}/hooks/hooks.json" 2>/dev/null \
  | python3 -c '
import json,sys
d=json.load(sys.stdin).get("hooks",{})
for ev, entries in d.items():
    for e in entries:
        for h in e.get("hooks",[]):
            print(f"{ev}({e.get(\"matcher\",\"*\")})")
'
```

### 4. MCPs (si aplica)
Verificá que cada MCP requerido responda; reportá ✗ con qué arreglar si está caído.

### 5. Estado del proyecto
Conteos/archivos del datadir, config presente o no.

## Salida
```
✓ <plugin> v1.2.3
✓ Skills: N disponibles
✓ Hooks: SessionStart, PostToolUse
✗ MCP <srv> — no responde (cómo arreglarlo)
✓ datadir: N items
```
