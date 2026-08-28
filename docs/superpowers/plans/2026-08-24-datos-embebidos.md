# Datos Embebidos Desacoplables — Implementation Plan

> **Estado: ejecutado** (verificado 2026-08-27) — evidencia: entrada propia en `DONE.md` del store.
> Los checkboxes de abajo quedaron sin tildar: en este repo el estado real de una
> tarea vive en `DONE.md` del store central, no en el plan. No los leas como pendientes.


> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el audit de catálogo detecte y liste datos hardcodeados desacoplables (tuplas/listas de strings ≥4, umbrales numéricos) en los plugins auditados.

**Architecture:** Nueva función `find_embedded_data(root)` en `audit-catalog-gaps.py` con dos detectores mecánicos (colecciones de strings por acumulación hasta el cierre; umbrales por nombre), impresa como sección informativa al final del reporte texto.

**Tech Stack:** Python stdlib (re, pathlib) — sin dependencias.

## Global Constraints

- No cambiar la tabla de features existente ni sus exit codes; `--json` intacto.
- Excluir rutas con `test` en cualquier parte; respetar `SKIP_DIRS`.
- Estilo del repo: español, `ponytail:` para simplificaciones deliberadas.
- NO commitear salvo indicación expresa al ejecutar; commits con `--no-verify` solo si el TODO-precommit no aplica.

---

### Task 1: `find_embedded_data()` — detector

**Files:**
- Modify: `bin/audit-catalog-gaps.py` (sección nueva antes de `build_report`)
- Test: `bin/test-catalog-gaps.sh` (casos nuevos al final)

**Interfaces:**
- Consumes: `_read(path)`; `Path.rglob`.
- Produces: `find_embedded_data(root: Path) -> list[dict]` con dicts `{file: str(relpath), line: int, name: str, detail: str}` ordenado por (file, line).

- [ ] **Step 1: Test rojo** — append a `bin/test-catalog-gaps.sh` (antes del resumen final):

```bash
# Caso N: datos embebidos → sección de candidatos
FIX=$(mktemp -d)
mkdir -p "$FIX/.claude-plugin" "$FIX/bin" "$FIX/tests"
printf '{"name":"fx","version":"0.0.1"}' > "$FIX/.claude-plugin/plugin.json"
cat > "$FIX/bin/hooks.py" <<'PYX'
KEYWORDS = (
    "uno", "dos", "tres", "cuatro", "cinco",
)
MAX_RETRIES = 100
SMALL = ("a", "b")
PYX
printf 'export const PHRASES = ["aa", "bb", "cc", "dd"];\n' > "$FIX/lib.ts"
printf 'BIG = ("x", "y", "z", "w")\n' > "$FIX/tests/fixture.py"

out=$(python3 "$SCRIPT_DIR/audit-catalog-gaps.py" "$FIX")
echo "$out" | grep -q "DATOS EMBEBIDOS DESACOPLABLES — 3 candidato" \
    && echo "$out" | grep -q "bin/hooks.py:1 · KEYWORDS (5 ítems)" \
    && echo "$out" | grep -q "lib.ts:1 · PHRASES (4 ítems)" \
    && echo "$out" | grep -q "MAX_RETRIES" \
    && ! echo "$out" | grep -q "tests/fixture.py" \
    && echo "$out" | ! grep -q "SMALL" \
    && _pass "embedded-data: tupla py + array ts + umbral; excluye tests y <4 ítems" \
    || _fail "embedded-data: '$out'"
rm -rf "$FIX"
```

(Nota: `echo "$out" | ! grep -q SMALL` no es válido en bash — usar `! echo "$out" | grep -q "SMALL"`.)

- [ ] **Step 2: Correr y verificar fallo**

Run: `bash bin/test-catalog-gaps.sh 2>&1 | tail -3`
Expected: FAIL en el caso nuevo (la sección no existe).

- [ ] **Step 3: Implementar** — append antes de `def build_report`:

```python

# --- Datos embebidos desacoplables -------------------------------------------

_MIN_ITEMS = 4

_ASSIGN_RE = re.compile(
    r"^\s*(?:export\s+)?(?:const\s+)?([A-Z][A-Z0-9_]{2,})\s*"
    r"(?::\s*[\w\[\]<>, ]+)?\s*=\s*([\[\(])",
    re.MULTILINE,
)
_QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")
_THRESH_NAME = re.compile(
    r"^(?:MAX_[A-Z0-9_]+|[A-Z0-9_]+_(?:THRESHOLD|LIMIT)|[A-Z0-9_]*UMBRAL[A-Z0-9_]*)$")
_THRESH_RE = re.compile(r"^\s*([A-Z][A-Z0-9_]{2,})\s*=\s*\d+\s*$", re.MULTILINE)


def find_embedded_data(root: Path) -> list:
    """Candidatos a desacoplar: colecciones de strings (≥4) asignadas a constante
    MAYÚSCULA, y constantes de umbral numérico. Heurística — puede mentir; reporta,
    no actúa. ponytail: corta el cuerpo en el primer cierre; strings con paréntesis/
    corchetes adentro pueden confundirlo, se acepta por simple."""
    findings = []
    for path in _iter_files(root):
        parts = path.parts
        if "test" in path.name.lower() or any("test" in p.lower() for p in parts):
            continue
        if path.suffix == ".py":
            rel_ok = True
        elif path.suffix == ".ts":
            rel_ok = True
        else:
            continue
        text = _read(path)
        found = []
        for m in _ASSIGN_RE.finditer(text):
            name, open_ch = m.group(1), m.group(2)
            close = "]" if open_ch == "[" else ")"
            end = text.find(close, m.end())
            if end == -1:
                continue
            n = len(_QUOTED.findall(text[m.end():end]))
            if n >= _MIN_ITEMS:
                line = text.count("\n", 0, m.start()) + 1
                found.append({"name": name, "line": line, "detail": f"{n} ítems"})
        for m in _THRESH_RE.finditer(text):
            if _THRESH_NAME.match(m.group(1)):
                line = text.count("\n", 0, m.start()) + 1
                found.append({"name": m.group(1), "line": line, "detail": "umbral"})
        if not found:
            continue
        rel = path.relative_to(root)
        for f in found:
            findings.append({"file": str(rel), **f})
    return sorted(findings, key=lambda f: (f["file"], f["line"]))
```

(La variable `rel_ok` del boceto sobra — filtrar solo por sufijo; limpiar al escribir.)

- [ ] **Step 4: Verificar pase**

Run: `bash bin/test-catalog-gaps.sh 2>&1 | tail -3`
Expected: PASS en el caso nuevo; casos previos intactos.

- [ ] **Step 5: Commit** — `git commit --no-verify -m "audit: detector de datos embebidos desacoplables"`

### Task 2: Sección en la salida del audit

**Files:**
- Modify: `bin/audit-catalog-gaps.py` (`main()`)
- Test: `bin/test-catalog-gaps.sh` (ya cubierto por Task 1 Step 1 — esta tarea es solo cablear)

**Interfaces:**
- Consumes: `find_embedded_data(root)`.
- Produces: sección `DATOS EMBEBIDOS DESACOPLABLES` en salida texto; cap 8 filas; `--json` sin cambios.

- [ ] **Step 1: Implementar en `main()`**, después de `print(render_table(report))`:

```python
    embedded = find_embedded_data(root)
    if embedded:
        print(f"\nDATOS EMBEBIDOS DESACOPLABLES — {len(embedded)} candidato(s)")
        for e in embedded[:8]:
            print(f"   {e['file']}:{e['line']} · {e['name']} ({e['detail']})")
        if len(embedded) > 8:
            print(f"   … y {len(embedded) - 8} más")
        print("   → patrón de referencia: friction-lexicon.json "
              "+ cpt feedback learn (store + verbo + consumidor)")
```

- [ ] **Step 2: Verificar**: suite completa verde + smoke real contra ankify (`python3 bin/audit-catalog-gaps.py ../ankify`) mostrando candidatos plausibles.

- [ ] **Step 3: Commit** — `git commit --no-verify -m "audit: lista candidatos embebidos tras la tabla de features"`
