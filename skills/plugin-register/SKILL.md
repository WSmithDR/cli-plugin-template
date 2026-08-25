---
name: plugin-register
description: "Da de alta un plugin personal en el registry de evolución de cli-plugin-template (allowlist), desde su repo o desde cualquier otro cwd. Sin alta, el meta-plugin no captura fricción ni parchea ese plugin."
when_to_use: "Invocar cuando el usuario dice 'registrá este plugin', 'registrá <nombre>', 'que cli-plugin-template administre su evolución', 'dar de alta el plugin', cuando el aviso de SessionStart sugiere el alta, o cuando plugin-feedback-log no pudo resolver un plugin contra el registry."
---

# plugin-register — alta en el registry de evolución

El registry es el **allowlist** (baranda 1): el meta-plugin solo administra y parchea
plugins que el usuario dio de alta explícitamente. Cada entrada mapea un plugin a su repo
local (`local_path`) — eso habilita el parcheo cross-repo de P2.

---

## Step 1: Resolver QUÉ plugin se registra

El alta no exige estar parado en el repo del plugin: la fricción con un plugin casi nunca
aparece adentro de su repo — aparece usándolo en otro proyecto, que es justo donde antes
no se podía registrar. Resolvé la ruta del repo en cascada, parando en el primer paso que
dé resultado:

1. **Ruta explícita** — el usuario la dio, o la sabés del contexto (`registrá el plugin
   de ~/dev/bitacora`).
2. **Nombre del plugin** — buscá su `installPath` en
   `~/.claude/plugins/installed_plugins.json` (`plugins["<name>@<marketplace>"][].installPath`).
   Ojo: si cae bajo `~/.claude/plugins/cache/`, **no sirve** — es la copia instalada, no
   el repo donde se edita. El script lo rechaza. Usala solo si apunta a un repo real
   (instalación local vía `--plugin-dir` o marketplace local).
3. **cwd** — si no hay argumento ni nombre, el repo actual (comportamiento histórico).
4. **Preguntar** — si nada de lo anterior da un repo, pedí la ruta. Una sola pregunta,
   con lo que ya averiguaste: *"No encontré el repo de `<nombre>`. ¿Cuál es la ruta?"*

**No** registrar el propio catálogo (lleva `.catalog-root` en la raíz).

## Step 2: Reunir los datos del repo

```bash
source <(bash "$CLAUDE_PLUGIN_ROOT/skills/plugin-register/scripts/gather-plugin-metadata.sh" "<ruta>")
```

Sin argumento usa el cwd. El script valida que la ruta exista, que tenga manifiesto de
plugin y que no sea una copia del cache; si falla, imprime el motivo en stderr y sale 1 —
no inventes los datos, resolvé lo que dice el error.

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
