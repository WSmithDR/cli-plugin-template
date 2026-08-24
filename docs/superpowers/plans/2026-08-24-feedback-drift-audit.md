# Feedback Drift Audit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detectar automáticamente feedbacks marcados `pending` cuyo arreglo ya aterrizaron en el repo del plugin, y avisarlo en tres capas: comando manual, Stop hook nativo del meta-plugin, y post-commit opt-in por repo.

**Architecture:** Nueva función pura `gateway.feedback_audit(plugin)` que cruza los feedbacks pendientes contra el historial git del repo registrado (dos señales baratas: marcador `RESUELTO ... commit <hash>` en el cuerpo, y slug en el subject de un commit). El CLI la expone como `cpt feedback audit`; el Stop hook existente (`detect-pending-feedback.py`) gana un cuarto mensaje `_drift_message()` con dedupe por stamp (mismo patrón que `_promote_message`); `cpt feedback watch <plugin>` instala/quita un post-commit opt-in que reporta cada hallazgo una sola vez.

**Tech Stack:** Python 3 stdlib (argparse, re, subprocess, zlib, pathlib) — cero dependencias nuevas. Bash para los tests (convención `bin/test-*.sh` del repo).

## Global Constraints

- Store externo aislado en tests vía `export CLI_PLUGIN_TEMPLATE_DATA_DIR=<tmpdir>` (ver `bin/lib/paths.py:DATA_ENV`). Jamás tocar el store real en tests.
- Todo path del store sale de `bin/lib/paths.py`; nada arma paths a mano.
- Los hooks emiten JSON `{"systemMessage": ...}` o nada (exit 0 siempre). Nunca bloquean.
- Estilo del repo: comentarios en español, subjects de commit en minúsculas estilo `feedback: ...`, `ponytail:` para simplificaciones deliberadas.
- NO commitear salvo indicación explícita del usuario al ejecutar el plan.
- Los slugs están truncados a 40 chars por `paths.slugify` — el matcheo por substring es aproximado por diseño; se documenta con `ponytail:`.

---

### Task 1: `gateway.feedback_audit()` — detección de drift

**Files:**
- Modify: `bin/lib/gateway.py` (agregar sección nueva al final, antes de nada; después del bloque growth dashboard)
- Test: `bin/test-cpt-feedback.sh` (append sección nueva al final)

**Interfaces:**
- Consumes: `registry_get(name)` → `{"name","local_path",...}`; `feedback_list(plugin, pending_only=True)` → `list[str]` formato `"<plugin>/<slug>"`; `feedback_load(plugin, slug)` → str; `paths.slugify(text)` → str.
- Produces: `feedback_audit(plugin: str) -> list[dict]` donde cada dict es `{"slug": str, "commits": list[str]}` (hashes abreviados a 7). Lista vacía si no hay hallazgos o el repo no existe.

- [ ] **Step 1: Escribir el test que falla**

Append al final de `bin/test-cpt-feedback.sh`:

```bash

echo ""
echo "=== cpt feedback audit / watch ==="

REPO=$(mktemp -d)
git -C "$REPO" init -q
git -C "$REPO" -c user.email=t@t -c user.name=t commit -q --allow-empty \
    -m "carga: primer commit del repo de pruebas"
HASH=$(git -C "$REPO" rev-parse HEAD)

mkdir -p "$REPO/.claude-plugin"
printf '{"name":"plugtest","version":"0.0.1"}' > "$REPO/.claude-plugin/plugin.json"
python3 "$CPT" registry register plugtest "$REPO" >/dev/null

# caso A: marker RESUELTO con hash real en el cuerpo
python3 "$CPT" feedback save plugtest normalizador-fantasma \
    "el gate inventó formas.

**RESUELTO 2026-08-24, commit \`$HASH\`.**" >/dev/null
# caso B: sin ninguna evidencia
python3 "$CPT" feedback save plugtest otra-cosa "no hay evidencia acá" >/dev/null
# caso C: slug en el subject de un commit posterior
git -C "$REPO" -c user.email=t@t -c user.name=t commit -q --allow-empty \
    -m "gate: cierra plugtest-buscar-sin-proyeccion de raíz"
python3 "$CPT" feedback save plugtest buscar-sin-proyeccion "sin proyección de campos" >/dev/null

out=$(python3 "$CPT" feedback audit plugtest)
echo "$out" | grep -q "plugtest/normalizador-fantasma" \
    && echo "$out" | grep -q "plugtest/buscar-sin-proyeccion" \
    && ! echo "$out" | grep -q "otra-cosa" \
    && echo "$out" | grep -q "$(git -C "$REPO" rev-parse --short HEAD)" \
    && _pass "audit: marker RESUELTO + slug-en-subject detectados; sin-evidencia excluido" \
    || _fail "audit salida inesperada: '$out'"

# audit sin plugin conocido no explota
python3 "$CPT" feedback audit plugtest-inexistente >/dev/null 2>&1 \
    && _pass "audit: plugin desconocido devuelve vacío sin error" \
    || _fail "audit falló con plugin desconocido"
rm -rf "$REPO"
```

(El bloque `watch` de este test va en el Task 2; dejar el resto igual.)

- [ ] **Step 2: Correrlo y verificar que falla**

Run: `bash bin/test-cpt-feedback.sh 2>&1 | tail -20`
Expected: FAIL en "audit: marker RESUELTO..." porque `feedback audit` aún no existe (argparse error, salida vacía).

- [ ] **Step 3: Implementar en `bin/lib/gateway.py`**

Append al final del archivo:

```python

# ── drift audit (pendientes ya resueltos en el repo del plugin) ──

_RESUELTO_RE = re.compile(r"RESUELTO[^\n]*?commit [`']?([0-9a-f]{7,40})", re.IGNORECASE)


def _repo_commits(local_path: str) -> dict:
    """hash completo → subject, de todo el historial. UNA llamada git por auditoría."""
    import subprocess
    out = subprocess.run(["git", "-C", local_path, "log", "--format=%H%x00%s"],
                         capture_output=True, text=True, timeout=30)
    commits = {}
    for line in out.stdout.splitlines():
        h, sep, subj = line.partition("\x00")
        if sep:
            commits[h] = subj
    return commits


def feedback_audit(plugin: str) -> list:
    """Feedbacks PENDIENTES con evidencia de que ya fueron arreglados en su repo.

    Dos señales, ambas mecánicas (el juicio final lo tiene quien cierra):
      - marker: el cuerpo trae 'RESUELTO ..., commit <hash>' y ese hash existe en el repo.
      - subject: el slug aparece textual en el subject de algún commit.
    Devuelve [{"slug": str, "commits": [hash7]}]; [] si no hay hallazgos/repo."""
    entry = registry_get(plugin)
    if not entry or not entry.get("local_path"):
        return []
    repo = Path(entry["local_path"])
    if not repo.exists():
        return []
    commits = _repo_commits(str(repo))
    findings = []
    for item in feedback_list(plugin=entry["name"], pending_only=True):
        slug = item.split("/", 1)[1]
        body = feedback_load(entry["name"], slug)
        hits = []
        for short in _RESUELTO_RE.findall(body):
            full = next((h for h in commits if h.startswith(short)), None)
            if full:
                hits.append(full)
        # ponytail: substring literal del slug (truncado a 40 por slugify) contra subjects;
        # si algún día miente, subir a intersección de palabras del slug.
        for h, subj in commits.items():
            if slug.lower() in subj.lower() and h not in hits:
                hits.append(h)
        if hits:
            findings.append({"slug": slug, "commits": sorted({h[:7] for h in hits})})
    return findings
```

- [ ] **Step 4: Exponer en el CLI `bin/cpt`**

En `main()`, junto a los demás parsers de feedback (después de `f_disc`):

```python
    f_audit = fb_sub.add_parser("audit",
                                help="pendientes con evidencia de ya-aplicados en su repo")
    f_audit.add_argument("plugin", nargs="?", default=None)
    f_audit.add_argument("--json", action="store_true")
```

En el dispatch de `feedback`, después de la rama `discard`:

```python
        elif ns.op == "audit":
            names = [ns.plugin] if ns.plugin else \
                    [e["name"] for e in gateway.registry_list()]
            found = [{"plugin": n, **f}
                     for n in names for f in gateway.feedback_audit(n)]
            if ns.json:
                print(json.dumps(found, ensure_ascii=False))
            elif found:
                print(f"DRIFT: {len(found)} feedback(s) pendientes con evidencia "
                      f"de aplicación:")
                for f in found:
                    print(f"  {f['plugin']}/{f['slug']} | commits: "
                          f"{', '.join(f['commits'])}")
                print("Revisá cada uno y cerrá con: cpt feedback apply <plugin> <slug>")
```

(sin `else`: silencio = sin drift.)

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `bash bin/test-cpt-feedback.sh 2>&1 | tail -20`
Expected: PASS en las dos aserciones nuevas; las previas siguen en PASS.

- [ ] **Step 6: Commit**

```bash
git add bin/lib/gateway.py bin/cpt bin/test-cpt-feedback.sh
git commit -m "feedback: audit cruza pendientes contra el git log del repo"
```

---

### Task 2: `cpt feedback watch` — post-commit opt-in por repo

**Files:**
- Modify: `bin/lib/gateway.py` (función `feedback_watch_install`)
- Modify: `bin/cpt` (parser `watch` + dispatch)
- Test: `bin/test-cpt-feedback.sh` (append dentro de la sección del Task 1, antes del `rm -rf "$REPO"`)

**Interfaces:**
- Consumes: `registry_get(name)`.
- Produces: `feedback_watch_install(plugin: str, remove: bool = False) -> str` (mensaje para imprimir; `""` si no aplica). Archivo instalado: `<git-dir>/hooks/post-commit` ejecutable; estado de "ya reportado": `<git-dir>/cli-plugin-template.drift-seen`.

- [ ] **Step 1: Agregar el test (falla primero)**

Insertar antes del `rm -rf "$REPO"` del Task 1:

```bash
python3 "$CPT" feedback watch plugtest
[ -x "$REPO/.git/hooks/post-commit" ] \
    && _pass "watch: instala post-commit ejecutable" \
    || _fail "watch: no instaló el hook"

python3 "$CPT" feedback watch plugtest --remove
[ ! -e "$REPO/.git/hooks/post-commit" ] \
    && _pass "watch --remove: quita el hook" \
    || _fail "watch --remove: el hook sigue ahí"
```

- [ ] **Step 2: Correr y verificar fallo**

Run: `bash bin/test-cpt-feedback.sh 2>&1 | tail -8`
Expected: FAIL en ambas aserciones de watch (subcomando inexistente).

- [ ] **Step 3: Implementar `feedback_watch_install` en `gateway.py`**

Append después de `feedback_audit`:

```python

_WATCH_BODY = """#!/bin/bash
# cli-plugin-template feedback watch — avisa si este commit cierra un feedback pendiente.
# ponytail: cada slug se reporta UNA vez (estado en cli-plugin-template.drift-seen);
# si el ruido molesta, migrar el estado al store del meta-plugin.
CPT="__CPT__"
PLUGIN="__PLUGIN__"
OUT=$(python3 "$CPT" feedback audit "$PLUGIN" 2>/dev/null | grep '^  ' || true)
[ -z "$OUT" ] && exit 0
SEEN="$(git rev-parse --git-dir)/cli-plugin-template.drift-seen"
while IFS= read -r line; do
  slug=$(printf '%s' "$line" | sed 's/^ *//;s/ .*//')
  grep -qx "$slug" "$SEEN" 2>/dev/null && continue
  echo "$slug" >> "$SEEN"
  echo "$line"
done <<< "$OUT"
echo "feedback watch: revisá arriba y cerrá con 'cpt feedback apply $PLUGIN <slug>'"
"""


def feedback_watch_install(plugin: str, remove: bool = False) -> str:
    """Gancho post-commit OPT-IN en el repo del plugin registrado: tras cada commit,
    corre audit y reporta hallazgos nuevos (una vez por slug). El usuario decide
    por repo — nunca se instala solo."""
    import subprocess
    entry = registry_get(plugin)
    if not entry or not entry.get("local_path"):
        return ""
    r = subprocess.run(["git", "-C", entry["local_path"],
                        "rev-parse", "--absolute-git-dir"],
                       capture_output=True, text=True, timeout=10)
    gitdir = Path(r.stdout.strip())
    if not gitdir.is_dir():
        return ""
    hook = gitdir / "hooks" / "post-commit"
    if remove:
        if hook.exists():
            hook.unlink()
            return f"removido: {hook}"
        return ""
    cpt = Path(__file__).resolve().parents[1] / "cpt"
    body = _WATCH_BODY.replace("__CPT__", str(cpt)).replace("__PLUGIN__", entry["name"])
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(body, encoding="utf-8")
    hook.chmod(0o755)
    return f"instalado: {hook}"
```

En `bin/cpt`, parser (junto a `f_audit`):

```python
    f_watch = fb_sub.add_parser("watch",
                                help="instala/quita el aviso post-commit en el repo")
    f_watch.add_argument("plugin")
    f_watch.add_argument("--remove", action="store_true")
```

Dispatch (después de la rama `audit`):

```python
        elif ns.op == "watch":
            msg = gateway.feedback_watch_install(ns.plugin, remove=ns.remove)
            if msg:
                print(msg)
```

- [ ] **Step 4: Correr tests y verificar pase**

Run: `bash bin/test-cpt-feedback.sh 2>&1 | tail -12`
Expected: PASS en watch install/remove; suite completa sin FAIL.

- [ ] **Step 5: Commit**

```bash
git add bin/lib/gateway.py bin/cpt bin/test-cpt-feedback.sh
git commit -m "feedback: watch instala post-commit opt-in que reporta drift por commit"
```

---

### Task 3: Stop hook — `_drift_message()` con dedupe por stamp

**Files:**
- Modify: `bin/hooks/detect-pending-feedback.py` (nueva función + llamada en `main()`)
- Test: `bin/test-cpt-feedback.sh` (append al final de la sección, usando el mismo `$REPO` antes de borrarlo)

**Interfaces:**
- Consumes: `gateway.feedback_audit(name)`; `harvest_offset_get/set` (store clave→valor genérico); patrón stamp de `_promote_message`.
- Produces: `_drift_message() -> str` (`""` = silencio). Clave de dedupe: `"drift:<plugin>"`, stamp = `zlib.crc32` de los slugs ordenados.

- [ ] **Step 1: Test que falla** — insertar antes del `rm -rf "$REPO"`:

```bash
HOOKS="$SCRIPT_DIR/hooks"
drift=$(cd "$REPO" && HOOKS="$HOOKS" python3 - <<'PYEOF'
import importlib.util, os, sys
spec = importlib.util.spec_from_file_location(
    "dpf", os.environ["HOOKS"] + "/detect-pending-feedback.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print(m._drift_message())
PYEOF
)
echo "$drift" | grep -q "normalizador-fantasma" \
    && _pass "stop-hook: _drift_message lista el hallazgo" \
    || _fail "stop-hook drift vacío: '$drift'"
```

- [ ] **Step 2: Verificar fallo**

Run: `bash bin/test-cpt-feedback.sh 2>&1 | tail -6`
Expected: FAIL (`AttributeError: _drift_message` → línea vacía).

- [ ] **Step 3: Implementar** en `detect-pending-feedback.py`, antes de `main()`:

```python
def _drift_message() -> str:
    """Feedbacks pendientes que commits del repo ya resolvieron: el store quedó atrás.
    Mismo mecanismo de dedupe que _promote_message: un stamp por conjunto de hallazgos,
    así no repite mientras sea el mismo set."""
    try:
        from gateway import feedback_audit, harvest_offset_get, harvest_offset_set, registry_list
        cwd = Path.cwd().resolve()
        plugin = next((r for r in registry_list()
                       if r.get("local_path")
                       and cwd.is_relative_to(Path(r["local_path"]).resolve())), None)
        if not plugin:
            return ""
        found = feedback_audit(plugin["name"])
        if not found:
            return ""
        import zlib
        stamp = zlib.crc32(",".join(sorted(f["slug"] for f in found)).encode())
        key = f"drift:{plugin['name']}"
        if harvest_offset_get(key) == stamp:
            return ""
        harvest_offset_set(key, stamp)
    except Exception:
        return ""
    items = "; ".join(f"{f['slug']} ({','.join(f['commits'])})" for f in found[:3])
    suffix = "..." if len(found) > 3 else ""
    return (f"FEEDBACK DRIFT in {plugin['name']}: {len(found)} feedback(s) still marked "
            f"pending look ALREADY FIXED by commits: [{items}{suffix}]. Run "
            f"'python3 $CLAUDE_PLUGIN_ROOT/bin/cpt feedback audit {plugin['name']}', "
            f"verify each, close with 'cpt feedback apply' (or discard if obsolete).")
```

Y en `main()`, entre `promote` y el `if msgs`:

```python
    drift = _drift_message()
    if drift:
        msgs.append(drift)
```

Actualizar el docstring del módulo: agregar "(4) drift: pendientes que commits ya resolvieron".

- [ ] **Step 4: Verificar pase + dedupe**

Run: `bash bin/test-cpt-feedback.sh 2>&1 | tail -6`
Expected: PASS. Además verificar a mano el dedupe:

Run: `cd <repo-de-pruebas-del-test>` ya borrado — en su lugar, verificación inline agregando al mismo heredoc una segunda llamada y afirmando que devuelve vacío. Extender el Step 1 con:

```bash
drift2=$(cd "$REPO" && HOOKS="$HOOKS" python3 - <<'PYEOF'
import importlib.util, os
spec = importlib.util.spec_from_file_location(
    "dpf", os.environ["HOOKS"] + "/detect-pending-feedback.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print(m._drift_message())
PYEOF
)
[ -z "$drift2" ] && _pass "stop-hook: segunda pasada callada (dedupe por stamp)" \
    || _fail "stop-hook repite mensaje: '$drift2'"
```

- [ ] **Step 5: Commit**

```bash
git add bin/hooks/detect-pending-feedback.py bin/test-cpt-feedback.sh
git commit -m "hooks: stop detecta drift de feedbacks ya resueltos en el repo"
```

---

### Task 4: Docs + suite completa

**Files:**
- Modify: `skills/plugin-growth/SKILL.md` (Step 3)
- Modify: `AGENTS.md` y `CLAUDE.md` (línea de hooks activos)

**Interfaces:**
- Consumes: nada nuevo. Documenta `cpt feedback audit|watch` y el mensaje FEEDBACK DRIFT.

- [ ] **Step 1: `skills/plugin-growth/SKILL.md`** — en "## Step 3: Siguiente acción", insertar como primera viñeta:

```markdown
- Si hay **feedbacks pendientes** → ANTES de parchear, descartar drift:
  ```bash
  python3 "$CLAUDE_PLUGIN_ROOT/bin/cpt" feedback audit <name>
  ```
  Cada hallazgo lista commits que ya parecen resolverlo: verificar contra el código
  (APLICADO / PARCIAL / OBSOLETO / NO_APLICADO) y cerrar con `feedback apply` /
  `feedback discard`. Solo los genuinamente pendientes van a `plugin-hotpatch`.
  Opcional por repo: `cpt feedback watch <name>` instala un post-commit que avisa
  cuando un commit nuevo cierra un pendiente — preguntarle al usuario antes.
```

- [ ] **Step 2: `AGENTS.md` y `CLAUDE.md`** — en la línea "Hooks activos:", extender la entrada de Stop:

```
`Stop` (cosecha fricción pendiente + detecta drift de feedbacks ya resueltos en el repo)
```

- [ ] **Step 3: Suite completa**

Run: `for t in bin/test-cpt-*.sh bin/test-detect-feedback.sh bin/test-hooks.sh; do bash "$t" >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"; done`
Expected: todos PASS.

- [ ] **Step 4: Smoke real contra ankify**

Run: `python3 bin/cpt feedback audit ankify`
Expected: probablemente lista vacía (los 12 drift ya se cerraron a mano) o los PARCIALES con commits citados — nunca crash.

- [ ] **Step 5: Commit**

```bash
git add skills/plugin-growth/SKILL.md AGENTS.md CLAUDE.md
git commit -m "docs: plugin-growth descarta drift con audit antes de parchear"
```

---

## Self-review

- Cobertura: comando audit (Task 1), hook nativo Stop (Task 3), post-commit opt-in preguntando al usuario (Task 2 + doc en Task 4), recomendación en skill (Task 4). SessionStart explícitamente descartado con el usuario.
- Placeholders: ninguno; todos los pasos tienen código/comandos completos.
- Consistencia de nombres: `feedback_audit`, `feedback_watch_install`, `_drift_message`, ops `audit`/`watch`, clave `drift:<name>`, archivo `cli-plugin-template.drift-seen` — usados igual en todas las tareas.
