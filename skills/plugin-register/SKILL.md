---
name: plugin-register
description: "Da de alta el plugin del repo actual en el registry de evolución de cli-plugin-template (allowlist). Sin alta, el meta-plugin no captura fricción ni parchea ese plugin."
when_to_use: "Invocar cuando el usuario dice 'registrá este plugin', 'que cli-plugin-template administre su evolución', 'dar de alta el plugin', o cuando el aviso de SessionStart sugiere el alta."
---

# plugin-register — alta en el registry de evolución

El registry es el **allowlist** (baranda 1): el meta-plugin solo administra y parchea
plugins que el usuario dio de alta explícitamente. Cada entrada mapea un plugin a su repo
local (`local_path`) — eso habilita el parcheo cross-repo de P2.

---

## Step 1: Confirmar que es un plugin

El cwd debe tener `.claude-plugin/plugin.json`. Si no existe, avisar que no parece un
plugin y terminar. **No** registrar el propio catálogo (lleva `.catalog-root`).

## Step 2: Reunir los datos del repo actual

```bash
NAME=$(python3 -c "import json;print(json.load(open('.claude-plugin/plugin.json'))['name'])")
LOCAL_PATH=$(pwd)
REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
```

`skill_namespaces` por defecto es `[NAME]`. Si el plugin expone skills bajo un prefijo
distinto al nombre, pasar uno o más `--namespace`.

## Step 3: Confirmar con el usuario

Mostrar lo que se va a registrar y pedir confirmación:
```
Voy a registrar:
  name:        <NAME>
  local_path:  <LOCAL_PATH>
  remote:      <REMOTE>
  namespaces:  <NAME>
¿Confirmás?
```

## Step 4: Registrar (idempotente)

```bash
python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" registry register "$NAME" "$LOCAL_PATH" \
    --remote "$REMOTE" [--namespace <ns> ...]
```

Re-registrar el mismo `name` actualiza `local_path`/`remote`/`namespaces` (p.ej. si moviste
el repo) sin duplicar.

## Step 5: Confirmar

```
Plugin registrado ✓ — <NAME>
A partir de ahora podés capturar fricción con plugin-feedback-log y el meta-plugin la
agrupará en su store de evolución.
```
