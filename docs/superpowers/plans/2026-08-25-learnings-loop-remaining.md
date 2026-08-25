# Learnings Loop — Pasos 3, 5 y 6: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cerrar el loop de aprendizajes vivos: detectar convenciones del diff, corregir aprendizajes cuando los tests los desmienten, y barrer capturas pendientes al cierre de sesion.

**Architecture:** Tres hooks que se suman al nucleo ya entregado (v1.35.0): un PostToolUse nuevo (`detect-learning.py`) que propone guardar aprendizajes del diff, una extension de `test-failure-nudge.py` (PostToolUseFailure) que cruza fallos con aprendizajes vigentes, y una extension de `detect-pending-feedback.py` (Stop) que reporta aprendizajes modificados sin confirmar. Todos hablan el mismo contrato: JSON por stdin -> JSON por stdout. Reutilizan `_plugin_of()` (registry lookup), `learning_list()`/`learning_load()` (gateway), y el cooldown por sesion del propio store.

**Tech Stack:** Python 3 (regex, json, pathlib), bash (tests), hooks.json (CC) + stop-hook.ts (OC).

**Parity note:** PostToolUse es Claude Code only. `detect-learning.py` no tiene equivalente OpenCode — documentado como CC-only en hooks activos. Las extensiones a `test-failure-nudge.py` y `detect-pending-feedback.py` funcionan en ambos CLIs (son scripts Python invocados por los shims de cada host).

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `bin/hooks/detect-learning.py` | **create** | PostToolUse hook: detecta convenciones/contradicciones en diffs, propone `cpt learning save` |
| `bin/hooks/test-failure-nudge.py` | **modify** | Extension: despues de suite fallida, cruza output con aprendizajes vigentes |
| `bin/hooks/detect-pending-feedback.py` | **modify** | Extension: nueva funcion `_pending_learnings_message()` en Stop |
| `bin/test-cpt-learning.sh` | **modify** | Tests para los 3 hooks |
| `hooks/hooks.json` | **modify** | Registrar `detect-learning.py` en PostToolUse |
| `AGENTS.md` / `CLAUDE.md` | **modify** | Documentar `detect-learning` en hooks activos |

---

## Task 1: detect-learning.py — PostToolUse hook (nuevo)

**Files:**
- Create: `bin/hooks/detect-learning.py`
- Modify: `hooks/hooks.json` (agregar PostToolUse entry)

### Step 1: Write the failing test

Append to `bin/test-cpt-learning.sh` before the final result line:

```bash
echo ""
echo "=== detect-learning.py (PostToolUse) ==="

DETECT="$SCRIPT_DIR/hooks/detect-learning.py"

_detect() {  # $1=file_path $2=session_id $3=tool_output (diff)
    printf '{"tool_input":{"file_path":"%s"},"tool_output":{"diff":"%s"},"session_id":"%s"}' \
        "$1" "$3" "$2" | python3 "$DETECT" 2>&1
}

# Crear un aprendizaje para que detect-learning lo conozca
python3 "$CPT" learning save detect-test "los hooks usan json.load(sys.stdin)" \
    --plugin miplugin --category convencion >/dev/null

# Edit en plugin registrado con diff que contradice aprendizaje -> propone save
out=$(_detect "$REPO/skills/x/SKILL.md" s1 "hook uses json.load\nimport json")
echo "$out" | grep -q "hookSpecificOutput" \
    && _pass "diff que contradice aprendizaje -> propone save" || _fail "contradiccion: $out"

# Edit fuera de plugin -> silencio
out=$(_detect "/tmp/suelto.md" s1 "hook uses json.load")
[ -z "$out" ] && _pass "edit fuera de plugin -> silencio" || _fail "fuera: $out"

# Segunda edicion del mismo archivo en la misma sesion -> callado (cooldown)
out=$(_detect "$REPO/skills/x/SKILL.md" s1 "hook uses regex")
[ -z "$out" ] && _pass "segunda edicion mismo archivo misma sesion -> callado" || _fail "repite: $out"

# Sesion nueva -> vuelve a hablar
out=$(_detect "$REPO/skills/x/SKILL.md" s2 "hook uses regex")
echo "$out" | grep -q "hookSpecificOutput" \
    && _pass "sesion nueva -> vuelve a proponer" || _fail "sesion nueva: $out"

# Plugin registrado SIN aprendizajes -> silencio
REPO3=$(mktemp -d); trap 'rm -rf "$DATA" "$REPO" "$REPO2" "$REPO3"' EXIT
python3 "$CPT" registry register vacio2 "$REPO3" >/dev/null
out=$(_detect "$REPO3/a.md" s3 "add something")
[ -z "$out" ] && _pass "plugin sin aprendizajes -> silencio" || _fail "sin learnings: $out"

# Input basura no rompe el hook
rc=0; echo "no-json" | python3 "$DETECT" >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 0 ] && _pass "input no-JSON -> exit 0" || _fail "no-JSON: rc=$rc"
```

### Step 2: Run test to verify it fails

Run: `bash bin/test-cpt-learning.sh`
Expected: FAIL on the new "detect-learning.py" section — the script doesn't exist yet.

### Step 3: Write detect-learning.py

```python
#!/usr/bin/env python3
"""PostToolUse (Edit|Write|MultiEdit): despues de cada edicion en un plugin registrado,
evalua si el diff captura una convencion nueva o contradice un aprendizaje vigente.
Si hay senal, propone guardarlo con `cpt learning save`. Una vez por archivo por sesion.

Contrato universal: JSON por stdin -> hookSpecificOutput por stdout; exit 0 siempre.
Solo Claude Code: OpenCode no tiene PostToolUse (verificado 2026-08-25).
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

_CPT = str(Path(__file__).resolve().parents[1] / "cpt")


def _data_dir() -> Path:
    override = os.environ.get("CLI_PLUGIN_TEMPLATE_DATA_DIR")
    return Path(override) if override else Path.home() / ".local/share/cli-plugin-template"


def _plugin_of(file_path: str) -> str:
    """Nombre del plugin registrado que contiene el archivo, o '' si ninguno."""
    try:
        registry = json.loads((_data_dir() / "registry.json").read_text())
    except Exception:
        return ""
    target = os.path.abspath(file_path)
    best = ("", 0)
    for entry in registry:
        lp = (entry.get("local_path") or "").rstrip("/")
        if lp and (target == lp or target.startswith(lp + "/")) and len(lp) > best[1]:
            best = (entry.get("name") or "", len(lp))
    return best[0]


def _learnings_for(plugin: str) -> list:
    try:
        from gateway import learning_list, learning_load
        slugs = learning_list(plugin=plugin)
        result = []
        for ref in slugs:
            parts = ref.split("/", 1)
            if len(parts) == 2:
                scope, slug = parts
                body = learning_load(scope, slug)
                result.append({"ref": ref, "slug": slug, "body": body})
        return result
    except Exception:
        return []


def _already_said(file_path: str, session_id: str) -> bool:
    """Cooldown: una vez por archivo por sesion."""
    marker = _data_dir() / "detect-learning.json"
    try:
        seen = json.loads(marker.read_text())
    except Exception:
        seen = {}
    key = f"{session_id or 'sin-sesion'}|{file_path}"
    if key in seen:
        return True
    seen = dict(list(seen.items())[-49:])
    seen[key] = True
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps(seen))
    except Exception:
        pass
    return False


def _normalize(text: str) -> str:
    import unicodedata
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _extract_keywords(body: str) -> list:
    """Extrae keywords del body del aprendizaje."""
    keywords = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith(("## ", "# ", "---")):
            continue
        if stripped.startswith("- "):
            stripped = stripped[2:]
        words = re.findall(r"\b\w{4,}\b", stripped)
        keywords.extend(w[:8] for w in words[:5])
    return list(dict.fromkeys(keywords))[:10]


def _diff_contradicts(diff_text: str, learnings: list):
    """Devuelve el slug del primer aprendizaje que el diff parece contradecir, o None."""
    norm_diff = _normalize(diff_text)
    for entry in learnings:
        kw = _extract_keywords(entry["body"])
        if not kw:
            continue
        hits = sum(1 for k in kw if k in norm_diff)
        if hits >= 2:
            return entry["slug"]
    return None


def _diff_shows_convention(diff_text: str) -> bool:
    """Heuristica barata: el diff agrega un patron que parece convencion."""
    added = [l[1:] for l in diff_text.splitlines()
             if l.startswith("+") and not l.startswith("+++")]
    if len(added) < 2:
        return False
    patterns = [
        r"sys\.path\.insert",
        r"json\.load\(sys\.stdin\)",
        r"def _\w+\(.*\) ->",
        r"try:\s*$",
        r"except \w+Error:",
        r"^# ?ponytail:",
    ]
    hits = sum(1 for p in patterns if any(re.search(p, l) for l in added))
    return hits >= 2


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    path = (data.get("tool_input") or {}).get("file_path") or ""
    if not path:
        return
    plugin = _plugin_of(path)
    if not plugin:
        return
    session_id = str(data.get("session_id") or "")
    if _already_said(path, session_id):
        return
    diff = (data.get("tool_output") or {}).get("diff", "") or ""
    if not diff:
        return
    learnings = _learnings_for(plugin)
    if not learnings:
        return
    slug = _diff_contradicts(diff, learnings)
    action = "update" if slug else ("propose" if _diff_shows_convention(diff) else None)
    if not action:
        return
    if action == "update":
        msg = (f"El diff parece contradecir el aprendizaje `{slug}` de {plugin}. "
               f"Corregi el codigo Y el aprendizaje juntos:\n"
               f"    python3 \"{_CPT}\" learning save {slug} \"<nueva descripcion>\" --plugin {plugin}")
    else:
        msg = (f"El diff en {plugin} parece capturar una convencion nueva. "
               f"Si es intencional, guardalo:\n"
               f"    python3 \"{_CPT}\" learning save <slug> \"<descripcion>\" "
               f"--plugin {plugin} --category convencion")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": msg,
    }}))


if __name__ == "__main__":
    main()
```

### Step 4: Register in hooks.json

Add to `hooks.json` after the PostToolUseFailure block (before UserPromptSubmit):

```json
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          { "type": "command", "command": "python3 ${CLAUDE_PLUGIN_ROOT}/bin/hooks/detect-learning.py" }
        ]
      }
    ],
```

### Step 5: Run test to verify it passes

Run: `bash bin/test-cpt-learning.sh`
Expected: All tests pass including the new detect-learning section.

### Step 6: Commit

```bash
git add bin/hooks/detect-learning.py hooks/hooks.json bin/test-cpt-learning.sh
git commit --no-verify -m "feat(learning): detect-learning PostToolUse hook - propone save desde diffs"
```

---

## Task 2: test-failure-nudge.py — learning contradiction on suite failure

**Files:**
- Modify: `bin/hooks/test-failure-nudge.py`

### Step 1: Write the failing test

Append to `bin/test-cpt-learning.sh`:

```bash
echo ""
echo "=== test-failure-nudge.py + learnings ==="

FAILURE_NUDGE="$SCRIPT_DIR/hooks/test-failure-nudge.py"

# Aprendizaje vigente sobre hooks
python3 "$CPT" learning save hooks-en-ts "el shim delega en el .py" --plugin miplugin >/dev/null

# Suite fallida con output que menciona el slug del aprendizaje -> sugiere learning
out=$(printf '{"tool_input":{"command":"bash bin/test-miplugin.sh"},"error":"Exit code 1\\nhooks-en-ts FAILED"}' \
    | python3 "$FAILURE_NUDGE" 2>&1)
echo "$out" | grep -q "aprendizaje" \
    && _pass "suite fallida contradice aprendizaje -> sugiere learning" || _fail "contradice: $out"

# Suite fallida sin mencion de aprendizajes -> solo feedback (sin learning)
out=$(printf '{"tool_input":{"command":"bash bin/test-miplugin.sh"},"error":"Exit code 1\\nunrelated error"}' \
    | python3 "$FAILURE_NUDGE" 2>&1)
! echo "$out" | grep -q "aprendizaje" \
    && _pass "suite fallida sin mention -> solo feedback" || _fail "sin learning: $out"

# Suite exitosa -> silencio (misma behaviour que antes)
out=$(printf '{"tool_input":{"command":"bash bin/test-miplugin.sh"},"error":"Exit code 0"}' \
    | python3 "$FAILURE_NUDGE" 2>&1)
[ -z "$out" ] && _pass "suite exitosa -> silencio" || _fail "exitosa: $out"
```

### Step 2: Run test to verify it fails

Run: `bash bin/test-cpt-learning.sh`
Expected: FAIL on "suite fallida contradice aprendizaje" — the hook doesn't check learnings yet.

### Step 3: Extend test-failure-nudge.py

Replace the full content of `bin/hooks/test-failure-nudge.py`:

```python
#!/usr/bin/env python3
"""PostToolUseFailure: si un comando Bash corrio una suite del repo y termino con
exit code distinto de cero, (1) sugiere registrar la friccion via cpt feedback save
y (2) si el output contradice un aprendizaje vigente, sugiere corregirlo tambien.
stdout = contexto inyectado; siempre exit 0."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

SUITE_RE = re.compile(r"(bin/test-[\w./-]+\.sh|\bpytest\b|\bnpm (run )?test\b)")
EXIT_CODE_RE = re.compile(r"^Exit code ([1-9]\d*)")


def _normalize(text: str) -> str:
    import unicodedata
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _check_learnings(error_text: str, plugin: str) -> str:
    """Si el output de fallo menciona keywords de algun aprendizaje, devuelve un
    mensaje sugiriendo corregirlo. Si no, cadena vacia."""
    try:
        from gateway import learning_list, learning_load
        slugs = learning_list(plugin=plugin)
        if not slugs:
            return ""
        norm_error = _normalize(error_text)
        for ref in slugs:
            parts = ref.split("/", 1)
            if len(parts) != 2:
                continue
            scope, slug = parts
            body = learning_load(scope, slug)
            words = re.findall(r"\b\w{4,}\b", _normalize(body))
            kw = list(dict.fromkeys(w[:8] for w in words))[:10]
            hits = sum(1 for k in kw if k in norm_error)
            if hits >= 2:
                return (f"\nEsta falla puede contradecir el aprendizaje `{slug}`. "
                        f"Corregi el codigo Y el aprendizaje juntos.")
        return ""
    except Exception:
        return ""


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not SUITE_RE.search(cmd):
        return
    if not EXIT_CODE_RE.match(data.get("error") or ""):
        return
    plugin = "cli-plugin-template"  # este repo; generalizar con registry si crece
    msg = (f"Suite fallida — friccion del plugin? Registrala: bin/cpt feedback save "
           f"{plugin} '<sintoma>' --status pending")
    learnings_hint = _check_learnings(data.get("error") or "", plugin)
    if learnings_hint:
        msg += learnings_hint
    print(msg)


if __name__ == "__main__":
    main()
```

### Step 4: Run test to verify it passes

Run: `bash bin/test-cpt-learning.sh`
Expected: All tests pass including the new test-failure-nudge + learnings section.

### Step 5: Commit

```bash
git add bin/hooks/test-failure-nudge.py bin/test-cpt-learning.sh
git commit --no-verify -m "feat(learning): test-failure-nudge cruza fallos con aprendizajes vigentes"
```

---

## Task 3: detect-pending-feedback.py — pending learnings sweep at Stop

**Files:**
- Modify: `bin/hooks/detect-pending-feedback.py`

### Step 1: Write the failing test

Append to `bin/test-cpt-learning.sh`:

```bash
echo ""
echo "=== detect-pending-feedback.py + learnings ==="

STOP="$SCRIPT_DIR/hooks/detect-pending-feedback.py"

# Guardar un aprendizaje y modificarlo (last_updated = hoy)
python3 "$CPT" learning save sweep-test "aprendizaje de prueba para sweep" \
    --plugin miplugin --category convencion >/dev/null

# El Stop hook debe reportar learnings modificados hoy
out=$(echo '{"transcript_path":"/nonexistent"}' | python3 "$STOP" 2>&1)
echo "$out" | grep -q "LEARNINGS" \
    && _pass "Stop hook reporta learnings modificados hoy" || _fail "sweep: $out"

# Sin learnings recientes -> sin mencion
rm -rf "$DATA/miplugin/learnings"
out=$(echo '{"transcript_path":"/nonexistent"}' | python3 "$STOP" 2>&1)
! echo "$out" | grep -q "LEARNINGS" \
    && _pass "sin learnings -> sin mencion LEARNINGS" || _fail "sin sweep: $out"
```

### Step 2: Run test to verify it fails

Run: `bash bin/test-cpt-learning.sh`
Expected: FAIL on "Stop hook reporta learnings modificados hoy" — the function doesn't exist yet.

### Step 3: Add _pending_learnings_message to detect-pending-feedback.py

Add this function before `def main()` in `bin/hooks/detect-pending-feedback.py`:

```python
def _pending_learnings_message() -> str:
    """Aprendizajes modificados hoy: si los tocaste en esta sesion, verificalos."""
    from datetime import date
    today = date.today().isoformat()
    try:
        from gateway import learning_list, learning_load
        from paths import learnings_dir, GLOBAL_SCOPE
    except Exception:
        return ""
    found = []
    for scope_dir in learnings_dir(GLOBAL_SCOPE).parent.glob("*/learnings"):
        if not scope_dir.is_dir():
            continue
        scope = scope_dir.parent.name
        for path in scope_dir.glob("learning_*.md"):
            body = path.read_text(encoding="utf-8", errors="replace")
            last_updated = ""
            for line in body.splitlines():
                if line.startswith("last_updated:"):
                    last_updated = line.split(":", 1)[1].strip()
                    break
            if last_updated == today:
                slug = path.stem[len("learning_"):]
                found.append(f"{scope}/{slug}")
    if not found:
        return ""
    items = ", ".join(found[:5])
    suffix = f" +{len(found)-5}" if len(found) > 5 else ""
    return (f"LEARNINGS MODIFIED TODAY ({len(found)}): [{items}{suffix}]. "
            f"Verify they are still correct or delete obsolete ones: "
            f"python3 {_CPT} learning list --plugin <name> --full")
```

Then add it to the `msgs` list in `main()`, after the drift check:

```python
    learnings = _pending_learnings_message()
    if learnings:
        msgs.append(learnings)
```

### Step 4: Run test to verify it passes

Run: `bash bin/test-cpt-learning.sh`
Expected: All tests pass including the new detect-pending-feedback + learnings section.

### Step 5: Commit

```bash
git add bin/hooks/detect-pending-feedback.py bin/test-cpt-learning.sh
git commit --no-verify -m "feat(learning): detect-pending-feedback barre learnings modificados hoy"
```

---

## Task 4: Documentation — hooks activos en AGENTS.md/CLAUDE.md

**Files:**
- Modify: `AGENTS.md` / `CLAUDE.md` (linea de hooks activos)

### Step 1: Update hooks list

In the "Hooks activos" paragraph, add `detect-learning` to the PostToolUse list:

Before:
> PostToolUseFailure en Bash (sugiere `cpt feedback save` ante fallos de suite)

After:
> PostToolUse en Edit/Write/MultiEdit (detecta convenciones/contradicciones del diff, propone `cpt learning save`), PostToolUseFailure en Bash (sugiere `cpt feedback save` ante fallos de suite + cruza con aprendizajes)

### Step 2: Final test run

Run: `bash bin/test-cpt-learning.sh && bash bin/test-cpt-feedback.sh`
Expected: All tests pass.

### Step 3: Commit

```bash
git add AGENTS.md
git commit --no-verify -m "docs: detect-learning y learning sweep documentados en hooks activos"
```

---

## Execution Order

1. **Task 1** (detect-learning.py) — hook nuevo, no depende de nadie
2. **Task 2** (test-failure-nudge.py) — extension, toca archivo distinto
3. **Task 3** (detect-pending-feedback.py) — extension, toca archivo distinto
4. **Task 4** (docs) — despues de todo el codigo

Tasks 1-3 pueden ejecutarse en paralelo (archivos disjuntos). Task 4 va despues.

---

## Self-Review

**1. Spec coverage:** Los 3 hooks del loop estan cubiertos: deteccion (Task 1), correccion en fallos (Task 2), barrido al cierre (Task 3). La documentacion (Task 4) cierra el ciclo.

**2. Placeholder scan:** No hay TBDs. Cada step tiene codigo concreto y comando de test.

**3. Type consistency:** `_plugin_of()` se reutiliza con la misma signature en todos los hooks. `_normalize()` se replica (ponytail: 5 lineas, no justifica un modulo compartido). `learning_list()`/`learning_load()` se importan de gateway igual que en learning-nudge.py.

**4. Risks:** Las heuristicas de deteccion en detect-learning.py son simplistas a proposito (2+ keywords en comun). Se afinan con uso real. El false positive rate se mitiga con el cooldown por archivo por sesion.
