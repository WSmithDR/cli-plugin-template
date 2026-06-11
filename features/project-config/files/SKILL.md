---
name: <plugin>-config
description: "Configura <plugin> para el proyecto actual. Pregunta preferencias de forma interactiva y las guarda en <datadir>/config.json. Correr en el primer uso o para cambiar un setting."
---

# <plugin> — Config

Gestiona settings por proyecto. Archivo: `<datadir>/config.json`.

## Schema

```json
{
  "<setting>": false,
  "configured_at": "YYYY-MM-DD",
  "configured_by": "GitName"
}
```

## Proceso

### 1. Leer config existente
```bash
mkdir -p <datadir>
cat <datadir>/config.json 2>/dev/null
```

### 2. Modo
- **Sin config** → first-run: preguntar todos los settings.
- **Con config** → mostrar valores actuales y preguntar qué cambiar.

### 3. Preguntar (AskUserQuestion)
Usá opciones claras; poné la recomendada primera.

### 4. Persistir atómico
```bash
CREATOR=$(git config user.name); TODAY=$(date +%Y-%m-%d)
CREATOR="$CREATOR" TODAY="$TODAY" python3 -c '
import json, os
cfg = {"<setting>": False,
       "configured_at": os.environ["TODAY"],
       "configured_by": os.environ["CREATOR"]}
with open("<datadir>/config.json", "w") as f:
    json.dump(cfg, f, indent=2)
'
```

### 5. Confirmar
```
✓ Config guardada
  <setting>: <valor>
  configured_by: <nombre> · <fecha>
```
