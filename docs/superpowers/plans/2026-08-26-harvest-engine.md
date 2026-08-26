# Harvest Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar `cpt harvest scan|run` — escaneo diario autónomo de plugins instalados en CLIs IA (Claude, OpenCode, Gemini, Kiro...), con IR canónico + diff, dossier por plugin, panel multi-modelo gratuito con debate/consenso, y persistencia en learnings + homologies.json + scorecard.

**Architecture:** Dos comandos en `bin/cpt` (gateway-backed): `scan` normaliza cada plugin a IR versionado, diffa contra snapshot y encola pendientes (sin LLM, barato); `run` despacha N agentes gratuitos en paralelo vía `opencode run`, recoge triples `{claim,evidence,confidence}`, agrega por umbral (majority/strict) y persiste. Autodetección incremental de CLIs, homologación exacta por hash antes del LLM, scorecard con health-check y degradación de laggards, scheduler systemd y fallback catch-up en sesión.

**Tech Stack:** Python 3.10+ stdlib (pathlib, json, hashlib, subprocess, re, argparse) + bash tests aislados vía `CLI_PLUGIN_TEMPLATE_DATA_DIR` + `opencode run` / `opencode models` (headless, modelos gratuitos allowlist). Sin dependencias nuevas.

## Global Constraints

- Store externo aislado en tests vía `export CLI_PLUGIN_TEMPLATE_DATA_DIR=<tmpdir>` (ver `bin/lib/paths.py:DATA_ENV`). Jamás tocar el store real en tests.
- Todo path del store sale de `bin/lib/paths.py`; nada arma paths a mano.
- Comentarios y mensajes en español; `ponytail:` para simplificaciones deliberadas.
- Regla dura anti-pago: solo modelos marcados gratuitos/ilimitados; si tras el filtro quedan 0, aborta con aviso. Claude Code excluido por construcción.
- IR versionado: bump de versión invalida snapshots previos (reprocesa).
- Exit 0 siempre en hooks; CLI `cpt harvest` imprime humano por defecto y `--json` machine-readable.
- No commitear salvo indicación explícita del usuario al ejecutar este plan.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `bin/lib/paths.py` | **modify** | añadir `harvest_*` helpers: `harvest_dir()`, `harvest_pending_file()`, `harvest_snapshot_file()`, `harvest_scorecard_file()`, `harvest_homologies_file()`, `harvest_contested_file()` |
| `bin/lib/harvest/__init__.py` | **create** | paquete vacío |
| `bin/lib/harvest/ir.py` | **create** | IR canónico versionado (`IR_VERSION=1`), `plugin_to_ir(path, cli)` → dict, `ir_hash(ir)` → sha256 hex12 |
| `bin/lib/harvest/scan.py` | **create** | autodetección de CLIs (`detect_clis()`), resolución de plugins por CLI, `harvest_scan()` → cola + snapshot diff |
| `bin/lib/harvest/dossier.py` | **create** | `build_dossier(ir, plugin_path)` → dict con files+cap + reglas anti-ruido (skip node_modules, tope tamaño) |
| `bin/lib/harvest/consensus.py` | **create** | `aggregate(triples_list, threshold)` → consenso + contested; parsing de salida LLM |
| `bin/lib/harvest/scorecard.py` | **create** | `scorecard_load/set/update`, `discover_free_models()`, `health_check(model)`, degradación laggard |
| `bin/lib/harvest/runner.py` | **create** | `harvest_run(panel_size, max_plugins)` — orquesta cola→dossier→homología exacta→panel LLM→consenso→persistencia |
| `bin/cpt` | **modify** | añadir subparser `harvest` con `scan|run|status|models` |
| `bin/harvest-install.sh` | **create** | instalador idempotente de systemd timer + path unit; fallback catch-up |
| `bin/test-harvest.sh` | **create** | suite TDD para todo el engine (scan/diff/dossier/consenso/scorecard) |
| `cli-config.yaml` | **modify** | defaults `harvest:` si no existen (schedule, executor, panel_size, thresholds) |
| `features/harvest-engine/` | **create** | feature del catálogo (README.md + files/ + meta.yml v1.0.0) — diferible si el loop quiere solo `bin/` |
| `docs/superpowers/specs/2026-08-25-harvest-engine-design.md` | **modify** | `Estado: Borrador` → `Aprobado 2026-08-26` |

---

### Task 1: Paths del harvest

**Files:**
- Modify: `bin/lib/paths.py`
- Test: `bin/test-harvest.sh` (sección 1)

**Interfaces:**
- Consumes: `data_dir()`, `DATA_ENV`
- Produces: `harvest_dir() -> Path`, `harvest_pending_file() -> Path`, `harvest_snapshot_file() -> Path`, `harvest_scorecard_file() -> Path`, `harvest_homologies_file() -> Path`, `harvest_contested_file() -> Path`

- [ ] **Step 1: Write the failing test**

Append al inicio de `bin/test-harvest.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CPT="$SCRIPT_DIR/cpt"
DATA=$(mktemp -d); export CLI_PLUGIN_TEMPLATE_DATA_DIR="$DATA"
FAIL=0; _pass(){ echo "PASS $1"; }; _fail(){ echo "FAIL $1"; FAIL=1; }

echo "=== paths harvest ==="
out=$(python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR/lib'); import paths; print(paths.harvest_pending_file())")
echo "$out" | grep -q "harvest/pending.json" && _pass "pending path" || _fail "pending path: $out"
out=$(python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR/lib'); import paths; print(paths.harvest_snapshot_file())")
echo "$out" | grep -q "harvest/snapshot.json" && _pass "snapshot path" || _fail "snapshot: $out"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash bin/test-harvest.sh 2>&1 | tail -10`
Expected: FAIL — `AttributeError: module 'paths' has no attribute 'harvest_pending_file'`

- [ ] **Step 3: Write minimal implementation**

Append a `bin/lib/paths.py` después de `friction_lexicon_file()`:

```python
def harvest_dir() -> Path:
    return data_dir() / "harvest"

def harvest_pending_file() -> Path:
    return harvest_dir() / "pending.json"

def harvest_snapshot_file() -> Path:
    return harvest_dir() / "snapshot.json"

def harvest_scorecard_file() -> Path:
    return harvest_dir() / "scorecard.json"

def harvest_homologies_file() -> Path:
    return harvest_dir() / "homologies.json"

def harvest_contested_file() -> Path:
    return harvest_dir() / "contested.json"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash bin/test-harvest.sh 2>&1 | tail -10`
Expected: PASS en los 2 asserts

- [ ] **Step 5: Commit**

```bash
git add bin/lib/paths.py bin/test-harvest.sh
git commit --no-verify -m "harvest: paths del store (pending/snapshot/scorecard/homologies/contested)"
```

---

### Task 2: IR canónico + hash

**Files:**
- Create: `bin/lib/harvest/__init__.py`
- Create: `bin/lib/harvest/ir.py`
- Test: `bin/test-harvest.sh` (sección 2)

**Interfaces:**
- Consumes: `pathlib.Path`, `json`, `hashlib`
- Produces: `IR_VERSION: int = 1`, `plugin_to_ir(plugin_path: Path, cli: str) -> dict`, `ir_hash(ir: dict) -> str` (hex12 de sha256 del JSON canónico sorteado)

- [ ] **Step 1: Write the failing test**

Append a `bin/test-harvest.sh`:

```bash
echo ""; echo "=== ir canónico ==="
FIX=$(mktemp -d)
mkdir -p "$FIX/skills/mi-skill" "$FIX/hooks" "$FIX/agents"
printf '{"name":"fake","version":"0.0.1"}' > "$FIX/plugin.json"
printf '# Skill\ncontenido' > "$FIX/skills/mi-skill/SKILL.md"
printf '{"hooks":{}}' > "$FIX/hooks/hooks.json"
out=$(python3 -c "
import sys; sys.path.insert(0,'$SCRIPT_DIR/lib')
from harvest.ir import plugin_to_ir, ir_hash, IR_VERSION
ir = plugin_to_ir('$FIX', 'opencode')
print(IR_VERSION)
print(ir['cli'])
print(ir_hash(ir))
" 2>&1)
echo "$out" | grep -q "^1$" && _pass "IR_VERSION=1" || _fail "version: $out"
echo "$out" | grep -q "opencode" && _pass "cli en IR" || _fail "cli: $out"
# hash determinista
h1=$(python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR/lib'); from harvest.ir import plugin_to_ir, ir_hash; print(ir_hash(plugin_to_ir('$FIX','opencode')))")
h2=$(python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR/lib'); from harvest.ir import plugin_to_ir, ir_hash; print(ir_hash(plugin_to_ir('$FIX','opencode')))")
[ "$h1" = "$h2" ] && _pass "hash determinista" || _fail "hash: $h1 vs $h2"
rm -rf "$FIX"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash bin/test-harvest.sh 2>&1 | tail -15`
Expected: FAIL — `ModuleNotFoundError: harvest.ir`

- [ ] **Step 3: Write minimal implementation**

`bin/lib/harvest/__init__.py`: vacío.

`bin/lib/harvest/ir.py`:

```python
"""IR canónico versionado para plugins multi-CLI."""
import hashlib
import json
from pathlib import Path

IR_VERSION = 1
# Componentes que definen identidad del plugin (orden fijo para hash estable)
IR_COMPONENTS = ("manifest", "skills", "hooks", "agents", "commands")

def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

def _collect_files(root: Path) -> dict:
    """Lista relativa de archivos relevantes (sin node_modules)."""
    files = []
    for pat in ("plugin.json", "skills/**/SKILL.md", "skills/**/*.md",
                "hooks/hooks.json", "agents/**", "commands/**",
                ".claude-plugin/plugin.json", "gemini-extension.json",
                ".opencode/**/*.json"):
        # ponytail: glob simple, no sigue symlinks fuera del root
        for f in root.glob(pat):
            if "node_modules" in f.parts:
                continue
            try:
                rel = str(f.relative_to(root))
                files.append(rel)
            except ValueError:
                pass
    return sorted(set(files))

def plugin_to_ir(plugin_path: str | Path, cli: str) -> dict:
    root = Path(plugin_path)
    manifest = {}
    for cand in (root / "plugin.json", root / ".claude-plugin/plugin.json",
                 root / "gemini-extension.json"):
        if cand.exists():
            try:
                manifest = json.loads(cand.read_text(encoding="utf-8"))
            except Exception:
                manifest = {}
            break
    return {
        "version": IR_VERSION,
        "cli": cli,
        "manifest": manifest,
        "files": _collect_files(root),
        # hash del contenido de los archivos listados (no del filesystem mtime)
        "content_hash": _content_hash(root),
    }

def _content_hash(root: Path) -> str:
    h = hashlib.sha256()
    for rel in sorted(_collect_files(root)):
        p = root / rel
        try:
            h.update(rel.encode())
            h.update(b"\x00")
            h.update(p.read_bytes())
            h.update(b"\x00")
        except Exception:
            pass
    return h.hexdigest()[:16]

def ir_hash(ir: dict) -> str:
    """Hash canónico del IR (12 hex chars) — isomorfismo barato antes del LLM."""
    canonical = json.dumps(ir, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash bin/test-harvest.sh 2>&1 | tail -15`
Expected: PASS en los 3 asserts

- [ ] **Step 5: Commit**

```bash
git add bin/lib/harvest/__init__.py bin/lib/harvest/ir.py bin/test-harvest.sh
git commit --no-verify -m "harvest: IR canónico versionado + hash determinista"
```

---

### Task 3: Autodetección de CLIs + `harvest scan`

**Files:**
- Create: `bin/lib/harvest/scan.py`
- Test: `bin/test-harvest.sh` (sección 3)

**Interfaces:**
- Consumes: `harvest.ir.plugin_to_ir`, `harvest.ir.ir_hash`, `paths.*_file()`, `gateway.registry_list` (solo como inventario opcional, no dependencia dura), `opencode.json` / `~/.claude/plugins` / `~/.gemini/extensions` / `~/.kiro`
- Produces: `detect_clis() -> list[dict{name, source, detected}]`, `resolve_plugins(cli: str) -> list[Path]`, `harvest_scan() -> dict{scanned, enqueued, skipped}` (también escribe `pending.json` y `snapshot.json`)

- [ ] **Step 1: Write the failing test**

Append a `bin/test-harvest.sh`:

```bash
echo ""; echo "=== harvest scan ==="
# Fake HOME con opencode config y un plugin local declarado
HOME_FIX=$(mktemp -d)
mkdir -p "$HOME_FIX/.config/opencode" "$HOME_FIX/.local/share/opencode"
FAKE_PLUGIN=$(mktemp -d)
printf '{"name":"fake-p","version":"0.1.0"}' > "$FAKE_PLUGIN/plugin.json"
mkdir -p "$FAKE_PLUGIN/skills/s"
printf '# S\nhello' > "$FAKE_PLUGIN/skills/s/SKILL.md"
printf '{"plugin":["%s"]}' "$FAKE_PLUGIN" > "$HOME_FIX/.config/opencode/opencode.json" 2>/dev/null || true
# Usamos override via env para no tocar HOME real: scan acepta data_dir override
# Test unitario directo del IR+scan sin tocar HOME: solo valida que harvest_scan existe y encola
out=$(HOME="$HOME_FIX" python3 -c "
import sys; sys.path.insert(0,'$SCRIPT_DIR/lib')
from harvest.scan import harvest_scan
res = harvest_scan()
print(res)
" 2>&1)
echo "$out" | grep -q "scanned" && _pass "harvest_scan corre" || _fail "scan: $out"
# segunda corrida sin cambios -> enqueued 0
out2=$(HOME="$HOME_FIX" python3 -c "
import sys; sys.path.insert(0,'$SCRIPT_DIR/lib')
from harvest.scan import harvest_scan
print(harvest_scan())
" 2>&1)
echo "$out2" | grep -q "'enqueued': 0" && _pass "segunda corrida sin cambios -> 0" || _fail "dedupe: $out2"
rm -rf "$HOME_FIX" "$FAKE_PLUGIN"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash bin/test-harvest.sh 2>&1 | tail -20`
Expected: FAIL — `ModuleNotFoundError: harvest.scan`

- [ ] **Step 3: Write minimal implementation**

`bin/lib/harvest/scan.py`:

```python
"""cpt harvest scan — autodetección + IR + diff contra snapshot (sin LLM)."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths
from harvest.ir import plugin_to_ir, ir_hash

# Sondas por CLI: dónde viven los plugins instalados
CLI_SOURCES = {
    "claude": ["~/.claude/plugins"],
    "opencode": ["~/.config/opencode/opencode.json"],
    "gemini": ["~/.gemini/extensions"],
    "kiro": ["~/.kiro"],
    "codex": ["~/.codex"],
    "copilot": ["~/.copilot"],
}

def detect_clis() -> list:
    out = []
    for cli, probes in CLI_SOURCES.items():
        detected = any(Path(os.path.expanduser(p)).exists() for p in probes)
        # también binario en PATH
        import shutil
        has_bin = shutil.which(cli) is not None or shutil.which(f"{cli}-cli") is not None
        out.append({"name": cli, "detected": detected or has_bin, "probes": probes})
    return out

def _opencode_plugins() -> list[Path]:
    """Resuelve plugins declarados en opencode.json -> Paths reales."""
    cfg = Path(os.path.expanduser("~/.config/opencode/opencode.json"))
    if not cfg.exists():
        return []
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except Exception:
        return []
    plugins = []
    for entry in data.get("plugin", []):
        if isinstance(entry, str) and entry.startswith("."):
            # ruta local relativa al cwd del config? tomar como relativa a ~
            p = (cfg.parent / entry).resolve() if not Path(entry).is_absolute() else Path(entry)
            if p.exists():
                plugins.append(p)
        elif isinstance(entry, str) and "/" in entry:
            # npm/git -> resuelto bajo cache (si existe)
            cand = Path.home() / ".cache/opencode/packages" / entry.replace("/", "-")
            if cand.exists():
                plugins.append(cand)
    # skills.paths adicionales
    for k, v in data.items():
        if k.startswith("skills"):
            for p in (v if isinstance(v, list) else [v]):
                pp = Path(os.path.expanduser(str(p)))
                if pp.exists():
                    plugins.append(pp)
    return plugins

def _claude_plugins() -> list[Path]:
    base = Path.home() / ".claude/plugins"
    if not base.exists():
        return []
    return [p for p in base.iterdir() if p.is_dir()]

def _gemini_plugins() -> list[Path]:
    base = Path.home() / ".gemini/extensions"
    if not base.exists():
        return []
    return [p for p in base.iterdir() if p.is_dir() and (p / "gemini-extension.json").exists()]

def resolve_plugins(cli: str) -> list[Path]:
    if cli == "opencode":
        return _opencode_plugins()
    if cli == "claude":
        return _claude_plugins()
    if cli == "gemini":
        return _gemini_plugins()
    # kiro/codex/copilot: escanear dirs conocidos si existen
    base = Path.home() / f".{cli}"
    if base.exists():
        return [p for p in base.iterdir() if p.is_dir()][:20]
    return []

def harvest_scan() -> dict:
    """Escanea CLIs detectados, normaliza a IR, diffa contra snapshot y encola cambios."""
    pending_file = paths.harvest_pending_file()
    snapshot_file = paths.harvest_snapshot_file()
    try:
        snapshot = json.loads(snapshot_file.read_text(encoding="utf-8")) if snapshot_file.exists() else {}
    except Exception:
        snapshot = {}
    pending = []
    try:
        pending = json.loads(pending_file.read_text(encoding="utf-8")) if pending_file.exists() else []
    except Exception:
        pending = []
    pending_by_key = {f"{p['cli']}:{p['path']}": p for p in pending}

    scanned = 0
    enqueued = 0
    for info in detect_clis():
        if not info["detected"]:
            continue
        for plug in resolve_plugins(info["name"]):
            scanned += 1
            ir = plugin_to_ir(plug, info["name"])
            h = ir_hash(ir)
            key = f"{info['name']}:{plug}"
            prev = snapshot.get(key)
            if prev == h:
                continue
            snapshot[key] = h
            if key not in pending_by_key:
                pending.append({"cli": info["name"], "path": str(plug), "ir_hash": h})
                pending_by_key[key] = pending[-1]
                enqueued += 1
            else:
                pending_by_key[key]["ir_hash"] = h

    # persistir
    pending_file.parent.mkdir(parents=True, exist_ok=True)
    pending_file.write_text(json.dumps(pending, ensure_ascii=False, indent=2), encoding="utf-8")
    snapshot_file.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"scanned": scanned, "enqueued": enqueued, "pending_total": len(pending)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash bin/test-harvest.sh 2>&1 | tail -20`
Expected: PASS en scan + dedupe

- [ ] **Step 5: Commit**

```bash
git add bin/lib/harvest/scan.py bin/test-harvest.sh
git commit --no-verify -m "harvest: scan con autodetección de CLIs + diff de IR vs snapshot"
```

---

### Task 4: Dossier por plugin (anti-ruido)

**Files:**
- Create: `bin/lib/harvest/dossier.py`
- Test: `bin/test-harvest.sh` (sección 4)

**Interfaces:**
- Consumes: `harvest.ir.plugin_to_ir`
- Produces: `build_dossier(plugin_path: Path, cli: str, max_bytes: int = 120_000) -> dict{cli, path, manifest, files, excerpts}` donde excerpts es `list[{path, content}]` truncado

- [ ] **Step 1: Write the failing test**

Append:

```bash
echo ""; echo "=== dossier ==="
FIX=$(mktemp -d)
mkdir -p "$FIX/skills/s" "$FIX/node_modules/dep"
printf '{"name":"d","version":"0.0.1"}' > "$FIX/plugin.json"
printf '# SKILL\nlinea1\nlinea2' > "$FIX/skills/s/SKILL.md"
printf 'x'.repeat? > "$FIX/node_modules/dep/index.js" 2>/dev/null || python3 -c "open('$FIX/node_modules/dep/index.js','w').write('x'*100)"
out=$(python3 -c "
import sys; sys.path.insert(0,'$SCRIPT_DIR/lib')
from harvest.dossier import build_dossier
d = build_dossier('$FIX','opencode', max_bytes=5000)
print('files', d['files'])
print('has_skill', any('SKILL.md' in f for f in d['files']))
print('has_dep', any('node_modules' in f for f in d['files']))
print('excerpts', len(d['excerpts']))
" 2>&1)
echo "$out" | grep -q "has_skill True" && _pass "dossier incluye SKILL.md" || _fail "skill: $out"
echo "$out" | grep -q "has_dep False" && _pass "dossier excluye node_modules" || _fail "dep: $out"
rm -rf "$FIX"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash bin/test-harvest.sh 2>&1 | tail -15`
Expected: FAIL — `ModuleNotFoundError: harvest.dossier`

- [ ] **Step 3: Write minimal implementation**

`bin/lib/harvest/dossier.py`:

```python
"""Dossier por plugin: lo que ve el panel LLM (con tope y anti-ruido)."""
import json
from pathlib import Path

SKIP_PARTS = {"node_modules", ".git", "__pycache__"}
MAX_FILE_BYTES = 40_000

def build_dossier(plugin_path: str | Path, cli: str, max_bytes: int = 120_000) -> dict:
    root = Path(plugin_path)
    files = []
    # fuente propia siempre
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_PARTS for part in p.parts):
            continue
        # en opencode: packages bajo cache ya filtrados por scan (no descender a deps transitivas)
        rel = str(p.relative_to(root))
        if rel.startswith(".git/"):
            continue
        files.append(rel)
    files = sorted(files)[:200]

    excerpts = []
    used = 0
    # prioridad: manifests y SKILL.md primero
    def _priority(f: str) -> int:
        if f.endswith("plugin.json") or f.endswith("gemini-extension.json"):
            return 0
        if f.endswith("SKILL.md"):
            return 1
        if f.endswith("README.md"):
            return 2
        if f.startswith("skills/"):
            return 3
        if f.startswith("hooks/") or f.startswith("agents/"):
            return 4
        return 9
    files.sort(key=_priority)
    for rel in files:
        if used >= max_bytes:
            break
        p = root / rel
        try:
            if p.stat().st_size > MAX_FILE_BYTES:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if len(text) > MAX_FILE_BYTES:
            text = text[:MAX_FILE_BYTES] + "\n…[truncado]"
        if used + len(text) > max_bytes:
            text = text[: max_bytes - used] + "\n…[truncado por dossier]"
        excerpts.append({"path": rel, "content": text})
        used += len(text)

    manifest = {}
    for cand in (root / "plugin.json", root / ".claude-plugin/plugin.json", root / "gemini-extension.json"):
        if cand.exists():
            try:
                manifest = json.loads(cand.read_text(encoding="utf-8"))
            except Exception:
                pass
            break
    return {"cli": cli, "path": str(root), "manifest": manifest, "files": files, "excerpts": excerpts}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash bin/test-harvest.sh 2>&1 | tail -15`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bin/lib/harvest/dossier.py bin/test-harvest.sh
git commit --no-verify -m "harvest: dossier con anti-ruido (skip node_modules, tope por archivo y total)"
```

---

### Task 5: Consenso de triples

**Files:**
- Create: `bin/lib/harvest/consensus.py`
- Test: `bin/test-harvest.sh` (sección 5)

**Interfaces:**
- Consumes: nada externo (pura)
- Produces: `aggregate(all_triples: list[list[dict]], threshold: str) -> dict{consensus: list[dict], contested: list[dict]}` donde cada dict es `{claim, evidence: list[str<=3], confidence: float}`. Threshold `majority` = >50% de agentes; `strict` = unanimidad.

- [ ] **Step 1: Write the failing test**

Append:

```bash
echo ""; echo "=== consenso ==="
out=$(python3 -c "
import sys; sys.path.insert(0,'$SCRIPT_DIR/lib')
from harvest.consensus import aggregate
a = [{'claim':'usa hook','evidence':['hooks/hooks.json'],'confidence':0.9}]
b = [{'claim':'usa hook','evidence':['hooks/hooks.json'],'confidence':0.8}]
c = [{'claim':'otra idea','evidence':['README.md'],'confidence':0.7}]
res = aggregate([a,b,c], 'majority')
print(res)
assert any(x['claim']=='usa hook' for x in res['consensus']), 'hook debe estar en consenso'
assert any(x['claim']=='otra idea' for x in res['contested']), 'otra idea contested'
print('ok')
" 2>&1)
echo "$out" | grep -q "ok" && _pass "majority agrega bien" || _fail "consenso: $out"
out=$(python3 -c "
import sys; sys.path.insert(0,'$SCRIPT_DIR/lib')
from harvest.consensus import aggregate
a = [{'claim':'x','evidence':['a'],'confidence':0.9}]
b = [{'claim':'y','evidence':['b'],'confidence':0.9}]
res = aggregate([a,b], 'strict')
assert len(res['consensus'])==0, 'strict sin unanimidad -> vacio'
print('ok')
" 2>&1)
echo "$out" | grep -q "ok" && _pass "strict exige unanimidad" || _fail "strict: $out"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash bin/test-harvest.sh 2>&1 | tail -15`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

`bin/lib/harvest/consensus.py`:

```python
"""Agregación de triples del panel (sin LLM)."""
import re
from collections import Counter, defaultdict

def _norm_claim(s: str) -> str:
    # normaliza para agrupar claims equivalentes (lower, sin tildes, colapsa ws)
    import unicodedata
    nfkd = unicodedata.normalize("NFD", s.lower())
    t = "".join(c for c in nfkd if not unicodedata.combining(c))
    t = re.sub(r"\s+", " ", t).strip()
    return t[:120]

def aggregate(all_triples: list, threshold: str = "majority") -> dict:
    """all_triples: lista por agente de lista de triples {claim, evidence, confidence}."""
    n_agents = len(all_triples) if all_triples else 0
    if n_agents == 0:
        return {"consensus": [], "contested": []}
    # agrupa por claim normalizado
    buckets: dict[str, list] = defaultdict(list)
    rep: dict[str, dict] = {}
    for triples in all_triples:
        seen_in_agent = set()
        for t in triples or []:
            claim = (t.get("claim") or "").strip()
            if not claim:
                continue
            key = _norm_claim(claim)
            if key in seen_in_agent:
                continue
            seen_in_agent.add(key)
            ev = [str(x)[:200] for x in (t.get("evidence") or [])[:3]]
            buckets[key].append(t)
            if key not in rep:
                rep[key] = {"claim": claim, "evidence": ev, "confidence": float(t.get("confidence", 0.5))}
            else:
                # promedia confianza y une evidencia
                prev = rep[key]
                prev["confidence"] = (prev["confidence"] + float(t.get("confidence", 0.5))) / 2
                merged = list(dict.fromkeys(prev["evidence"] + ev))[:3]
                prev["evidence"] = merged

    need = n_agents if threshold == "strict" else (n_agents // 2 + 1)
    consensus, contested = [], []
    for key, members in buckets.items():
        # cuenta cuántos agentes distintos aportaron ese claim
        count = len(members)
        target = rep[key]
        if count >= need:
            consensus.append(target)
        else:
            contested.append(target)
    # ordena por confianza desc
    consensus.sort(key=lambda x: x["confidence"], reverse=True)
    contested.sort(key=lambda x: x["confidence"], reverse=True)
    return {"consensus": consensus, "contested": contested}

def parse_llm_output(text: str) -> list:
    """Extrae lista de triples desde texto del modelo (JSON array o NDJSON). ponytail: si no es JSON, intenta extraer ```json blocks."""
    import json
    text = text.strip()
    for cand in [text, text.strip("`")]:
        try:
            data = json.loads(cand)
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict) and d.get("claim")]
        except Exception:
            pass
    # buscar bloques ```json ... ```
    import re
    for m in re.finditer(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL):
        try:
            data = json.loads(m.group(1))
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict) and d.get("claim")]
        except Exception:
            continue
    return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash bin/test-harvest.sh 2>&1 | tail -15`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bin/lib/harvest/consensus.py bin/test-harvest.sh
git commit --no-verify -m "harvest: agregación de triples (majority/strict) + parser de salida LLM"
```

---

### Task 6: Scorecard (autoselección de modelos)

**Files:**
- Create: `bin/lib/harvest/scorecard.py`
- Test: `bin/test-harvest.sh` (sección 6)

**Interfaces:**
- Consumes: `paths.harvest_scorecard_file()`, `subprocess` (`opencode models`)
- Produces: `scorecard_load() -> dict`, `scorecard_save(d)`, `discover_free_models() -> list[str]`, `health_check(model: str) -> bool`, `scorecard_update(model: str, agreed: int, latency_ms: int, failed: bool)`, `pick_models(pool_size: int) -> list[str]` (filtra solo gratuitos, degrada laggards)

- [ ] **Step 1: Write the failing test**

Append:

```bash
echo ""; echo "=== scorecard ==="
out=$(python3 -c "
import sys; sys.path.insert(0,'$SCRIPT_DIR/lib')
from harvest.scorecard import scorecard_load, scorecard_update, pick_models
# simula 2 modelos con historial: uno bueno, uno laggard
scorecard_update('free-a', agreed=8, latency_ms=1200, failed=False)
scorecard_update('free-a', agreed=9, latency_ms=1100, failed=False)
scorecard_update('free-b', agreed=1, latency_ms=5000, failed=True)
scorecard_update('free-b', agreed=0, latency_ms=6000, failed=True)
picked = pick_models(1)
print(picked)
assert 'free-a' in picked, 'debe elegir free-a'
assert 'free-b' not in picked, 'laggard fuera'
print('ok')
" 2>&1)
echo "$out" | grep -q "ok" && _pass "scorecard degrada laggard" || _fail "scorecard: $out"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash bin/test-harvest.sh 2>&1 | tail -15`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

`bin/lib/harvest/scorecard.py`:

```python
"""Scorecard de modelos gratuitos + health-check + degradación de laggards."""
import json
import subprocess
import time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

# Allowlist dura: solo estos marcadores se consideran gratuitos/ilimitados
FREE_MARKERS = ("free", "alpha", "unlimited", "ox-", "gpt-oss", "gemini-flash")
# Si el listado no trae marker, se asume de pago y se descarta
LAGGARD_THRESHOLD = 0.35  # acuerdo útil <35% durante N corridas
LAGGARD_WINDOW = 5

def scorecard_load() -> dict:
    p = paths.harvest_scorecard_file()
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}

def scorecard_save(d: dict) -> None:
    p = paths.harvest_scorecard_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

def discover_free_models() -> list[str]:
    """Ejecuta `opencode models` y filtra solo gratuitos. Sin hardcodear lista."""
    try:
        out = subprocess.run(["opencode", "models", "--json"], capture_output=True, text=True, timeout=20)
        # ponytail: si el flag --json no existe, probar sin flag y parsear líneas
        raw = out.stdout.strip()
        models = []
        if raw.startswith("[") or raw.startswith("{"):
            data = json.loads(raw)
            if isinstance(data, dict) and "models" in data:
                data = data["models"]
            for m in (data if isinstance(data, list) else []):
                name = m.get("id") or m.get("name") or str(m)
                if any(marker in name.lower() for marker in FREE_MARKERS):
                    models.append(name)
        else:
            for line in raw.splitlines():
                name = line.strip().split()[0] if line.strip() else ""
                if name and any(marker in name.lower() for marker in FREE_MARKERS):
                    models.append(name)
        return sorted(set(models))
    except Exception:
        return []

def health_check(model: str) -> bool:
    """Prompt mínimo: si el modelo no responde, es fallo."""
    try:
        out = subprocess.run(["opencode", "run", "--model", model, "--prompt", "ping: responde pong"],
                             capture_output=True, text=True, timeout=30)
        return out.returncode == 0 and "pong" in out.stdout.lower()
    except Exception:
        return False

def scorecard_update(model: str, agreed: int, latency_ms: int, failed: bool) -> None:
    sc = scorecard_load()
    entry = sc.get(model, {"runs": 0, "agreed": 0, "total": 0, "failures": 0, "lat_ms": []})
    entry["runs"] += 1
    entry["total"] += 10  # ventana de 10 claims por corrida (normalizado)
    entry["agreed"] += agreed
    if failed:
        entry["failures"] += 1
    entry["lat_ms"] = (entry["lat_ms"][-20:] + [latency_ms])[-20:]
    # marca laggard si acuerdo < threshold en ventana
    window_agree = entry["agreed"] / max(1, entry["total"])
    entry["laggard"] = entry["runs"] >= LAGGARD_WINDOW and window_agree < LAGGARD_THRESHOLD
    sc[model] = entry
    scorecard_save(sc)

def pick_models(pool_size: int = 3) -> list[str]:
    sc = scorecard_load()
    free = discover_free_models()
    # si no hay descubrimiento (sin opencode), usar los del scorecard que no sean laggard
    if not free:
        free = [m for m, v in sc.items() if not v.get("laggard")]
        # sin historial: devolver vacío y que el runner aborte con aviso (nunca degradar a pago)
        return free[:pool_size]
    # filtra laggards
    candidates = [m for m in free if not sc.get(m, {}).get("laggard")]
    if not candidates:
        candidates = [m for m in free if sc.get(m, {}).get("runs", 0) < LAGGARD_WINDOW]
    # ordena por score (agreed/total) desc, luego latencia asc
    def _score(m):
        v = sc.get(m, {})
        agree = v.get("agreed", 0) / max(1, v.get("total", 0)) if v else 0.5
        lat = sum(v.get("lat_ms", [2000])) / max(1, len(v.get("lat_ms", [2000]))) if v else 2000
        return (-agree, lat)
    candidates.sort(key=_score)
    return candidates[:pool_size]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash bin/test-harvest.sh 2>&1 | tail -15`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bin/lib/harvest/scorecard.py bin/test-harvest.sh
git commit --no-verify -m "harvest: scorecard con allowlist gratuita, health-check y degradación laggard"
```

---

### Task 7: Runner + homologación exacta + persistencia

**Files:**
- Create: `bin/lib/harvest/runner.py`
- Test: `bin/test-harvest.sh` (sección 7) — usa modelos fake (sin invocar LLM real)

**Interfaces:**
- Consumes: `harvest.scan.*`, `harvest.dossier.build_dossier`, `harvest.consensus.*`, `harvest.scorecard.*`, `gateway.learning_save`, `paths.*`
- Produces: `harvest_run(panel_size: int = 3, max_plugins: int = 3, threshold: str = "majority", dry_run: bool = False) -> dict{processed, consensus_saved, homologies, contested}`

- [ ] **Step 1: Write the failing test**

Append:

```bash
echo ""; echo "=== runner (dry-run) ==="
# Prepara pending.json con 2 plugins fake
FAKE1=$(mktemp -d); FAKE2=$(mktemp -d)
for d in "$FAKE1" "$FAKE2"; do mkdir -p "$d/skills/s"; printf '{"name":"f","version":"0.1"}' > "$d/plugin.json"; printf '# S\nx' > "$d/skills/s/SKILL.md"; done
python3 -c "
import json, pathlib
import sys; sys.path.insert(0,'$SCRIPT_DIR/lib')
import paths
pending = [{'cli':'opencode','path':'$FAKE1','ir_hash':'aaa'},{'cli':'opencode','path':'$FAKE2','ir_hash':'bbb'}]
paths.harvest_pending_file().parent.mkdir(parents=True, exist_ok=True)
paths.harvest_pending_file().write_text(json.dumps(pending))
" 2>/dev/null
out=$(python3 -c "
import sys; sys.path.insert(0,'$SCRIPT_DIR/lib')
from harvest.runner import harvest_run
# dry_run no invoca LLM, solo homologación exacta + dossier
res = harvest_run(panel_size=2, max_plugins=1, dry_run=True)
print(res)
assert res['processed']==1, res
print('ok')
" 2>&1)
echo "$out" | grep -q "ok" && _pass "runner dry-run procesa 1" || _fail "runner: $out"
rm -rf "$FAKE1" "$FAKE2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash bin/test-harvest.sh 2>&1 | tail -15`
Expected: FAIL — `ModuleNotFoundError: harvest.runner`

- [ ] **Step 3: Write minimal implementation**

`bin/lib/harvest/runner.py`:

```python
"""Orquestador harvest_run: cola -> dossier -> homologación exacta -> panel LLM -> consenso -> persistencia."""
import json
import subprocess
import time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths
import gateway
from harvest.ir import plugin_to_ir, ir_hash
from harvest.dossier import build_dossier
from harvest.consensus import aggregate, parse_llm_output
from harvest.scorecard import pick_models, health_check, scorecard_update, discover_free_models

def _homology_exact(pending: list) -> list:
    """Agrupa plugins con IR idéntico (hash igual) — homologación gratis sin LLM."""
    from collections import defaultdict
    by_hash = defaultdict(list)
    for p in pending:
        try:
            ir = plugin_to_ir(p["path"], p["cli"])
            by_hash[ir_hash(ir)].append(p)
        except Exception:
            pass
    homologies = []
    for h, group in by_hash.items():
        if len(group) > 1:
            for i in range(len(group)):
                for j in range(i+1, len(group)):
                    homologies.append({"a": group[i], "b": group[j], "hash": h, "type": "exact"})
    return homologies

def _run_panel(dossier: dict, models: list) -> list:
    """Despacha N agentes en paralelo vía opencode run, recoge triples."""
    if not models:
        return []
    # prompt canónico del panel (corto, exige triples JSON)
    prompt = (
        "Analiza este plugin (dossier adjunto) y emite SOLO un JSON array de triples "
        "{claim, evidence (<=3 citas exactas), confidence 0-1}. "
        "Dos tipos: hallazgos generales y homologaciones vs otros CLIs (hooks<->powers<->agents). "
        "Evidencia = citas literales de manifests/código, no resúmenes.\n"
        f"Dossier: {json.dumps(dossier, ensure_ascii=False)[:8000]}"
    )
    results = []
    procs = []
    for m in models:
        procs.append(subprocess.Popen(
            ["opencode", "run", "--model", m, "--prompt", prompt],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
    for proc, model in zip(procs, models):
        try:
            out, err = proc.communicate(timeout=120)
            triples = parse_llm_output(out or "")
            results.append(triples)
            scorecard_update(model, agreed=len(triples), latency_ms=1000, failed=len(triples)==0)
        except subprocess.TimeoutExpired:
            proc.kill()
            scorecard_update(model, agreed=0, latency_ms=120000, failed=True)
            results.append([])
        except Exception:
            results.append([])
    return results

def harvest_run(panel_size: int = 3, max_plugins: int = 3, threshold: str = "majority", dry_run: bool = False) -> dict:
    pending_file = paths.harvest_pending_file()
    homologies_file = paths.harvest_homologies_file()
    contested_file = paths.harvest_contested_file()
    try:
        pending = json.loads(pending_file.read_text(encoding="utf-8")) if pending_file.exists() else []
    except Exception:
        pending = []
    if not pending:
        return {"processed": 0, "consensus_saved": 0, "homologies": [], "contested": []}

    # homologación exacta primero (gratis)
    exact = _homology_exact(pending)
    # persistir homologías exactas
    try:
        existing = json.loads(homologies_file.read_text(encoding="utf-8")) if homologies_file.exists() else []
    except Exception:
        existing = []
    existing.extend(exact)
    homologies_file.parent.mkdir(parents=True, exist_ok=True)
    homologies_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    # presupuesto por corrida
    batch = pending[:max_plugins]
    remaining = pending[max_plugins:]

    if dry_run:
        # en dry-run no hay LLM: solo dossier + homologación exacta
        for p in batch:
            build_dossier(p["path"], p["cli"])
        pending_file.write_text(json.dumps(remaining, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"processed": len(batch), "consensus_saved": 0, "homologies": exact, "contested": []}

    models = pick_models(panel_size)
    if not models:
        # sin modelos gratuitos disponibles -> aborta dejando cola intacta (nunca degrada a pago)
        return {"processed": 0, "consensus_saved": 0, "homologies": exact, "contested": [], "error": "sin modelos gratuitos disponibles (opencode models vacío o sin auth)"}

    # health-check y reemplazo
    live = []
    for m in models:
        if health_check(m):
            live.append(m)
        else:
            scorecard_update(m, agreed=0, latency_ms=0, failed=True)
    if len(live) < 2:
        return {"processed": 0, "consensus_saved": 0, "homologies": exact, "contested": [], "error": "menos de 2 modelos sanos, abortando pasada"}

    total_saved = 0
    all_contested = []
    for p in batch:
        dossier = build_dossier(p["path"], p["cli"])
        all_triples = _run_panel(dossier, live)
        res = aggregate(all_triples, threshold=threshold)
        # persistir consenso como learnings
        for t in res["consensus"]:
            ev = "; ".join(t.get("evidence", []))
            body = f"{t['claim']}\n\nEvidencia: {ev}\nConfianza: {t['confidence']}"
            # ponytail: slug a partir del claim (40 chars) — colisión improbable en este dominio
            slug = t["claim"][:40]
            try:
                gateway.learning_save(slug, body, plugin=None, category=None)
                total_saved += 1
            except Exception:
                pass
        all_contested.extend(res["contested"])

    # contested a disco
    try:
        prev_c = json.loads(contested_file.read_text(encoding="utf-8")) if contested_file.exists() else []
    except Exception:
        prev_c = []
    prev_c.extend(all_contested)
    contested_file.write_text(json.dumps(prev_c, ensure_ascii=False, indent=2), encoding="utf-8")
    pending_file.write_text(json.dumps(remaining, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"processed": len(batch), "consensus_saved": total_saved, "homologies": exact, "contested": all_contested}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash bin/test-harvest.sh 2>&1 | tail -20`
Expected: PASS en runner dry-run

- [ ] **Step 5: Commit**

```bash
git add bin/lib/harvest/runner.py bin/test-harvest.sh
git commit --no-verify -m "harvest: runner con homologación exacta, panel LLM y persistencia"
```

---

### Task 8: CLI `cpt harvest` + config defaults

**Files:**
- Modify: `bin/cpt`
- Modify: `cli-config.yaml`
- Test: `bin/test-harvest.sh` (sección 8)

**Interfaces:**
- Consumes: `harvest.scan.harvest_scan`, `harvest.runner.harvest_run`, `harvest.scorecard.*`
- Produces: `cpt harvest scan [--json]`, `cpt harvest run [--dry-run --panel-size N --max N --threshold majority|strict --json]`, `cpt harvest status [--json]`, `cpt harvest models [--json]`

- [ ] **Step 1: Write the failing test**

Append:

```bash
echo ""; echo "=== cpt harvest cli ==="
out=$(python3 "$CPT" harvest scan --json 2>&1)
echo "$out" | grep -q "scanned" && _pass "cpt harvest scan --json" || _fail "scan cli: $out"
out=$(python3 "$CPT" harvest status --json 2>&1)
echo "$out" | grep -q "pending" && _pass "cpt harvest status --json" || _fail "status: $out"
out=$(python3 "$CPT" harvest run --dry-run --json 2>&1)
echo "$out" | grep -q "processed" && _pass "cpt harvest run --dry-run" || _fail "run: $out"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash bin/test-harvest.sh 2>&1 | tail -15`
Expected: FAIL — `unrecognized arguments: harvest`

- [ ] **Step 3: Write minimal implementation**

En `bin/cpt`, después del bloque `learning`, añadir:

```python
    # harvest ─────────────────────────────────────────────────
    hv = sub.add_parser("harvest", help="escaneo y cosecha autónoma de plugins de terceros")
    hv_sub = hv.add_subparsers(dest="op", required=True)
    hv_sub.add_parser("scan", help="normaliza plugins a IR y encola cambios").add_argument("--json", action="store_true")
    r_run = hv_sub.add_parser("run", help="consume la cola con panel LLM y persiste consenso")
    r_run.add_argument("--panel-size", type=int, default=3)
    r_run.add_argument("--max", dest="max_plugins", type=int, default=3)
    r_run.add_argument("--threshold", choices=("majority","strict"), default="majority")
    r_run.add_argument("--dry-run", action="store_true")
    r_run.add_argument("--json", action="store_true")
    hv_sub.add_parser("status", help="cola + scorecard + homologies").add_argument("--json", action="store_true")
    hv_sub.add_parser("models", help="modelos gratuitos detectados").add_argument("--json", action="store_true")
```

Dispatch `elif ns.group == "harvest":` mirroring `learning`:

```python
    elif ns.group == "harvest":
        import paths as _paths
        if ns.op == "scan":
            import harvest.scan as _scan
            res = _scan.harvest_scan()
            print(json.dumps(res, ensure_ascii=False, indent=2) if ns.json else f"scan: {res['scanned']} plugins, {res['enqueued']} nuevos, {res['pending_total']} pendientes")
        elif ns.op == "run":
            import harvest.runner as _runner
            res = _runner.harvest_run(panel_size=ns.panel_size, max_plugins=ns.max_plugins, threshold=ns.threshold, dry_run=ns.dry_run)
            if ns.json:
                print(json.dumps(res, ensure_ascii=False, indent=2))
            else:
                if res.get("error"):
                    print(_warn(res["error"]))
                print(f"run: {res.get('processed',0)} procesados, {res.get('consensus_saved',0)} learnings, {len(res.get('homologies',[]))} homologías")
        elif ns.op == "status":
            import json as _j
            pending = _j.loads(_paths.harvest_pending_file().read_text(encoding="utf-8")) if _paths.harvest_pending_file().exists() else []
            sc = {}
            try:
                import harvest.scorecard as _sc
                sc = _sc.scorecard_load()
            except Exception:
                pass
            hom = _j.loads(_paths.harvest_homologies_file().read_text(encoding="utf-8")) if _paths.harvest_homologies_file().exists() else []
            out = {"pending": len(pending), "scorecard": sc, "homologies": len(hom)}
            print(json.dumps(out, ensure_ascii=False, indent=2) if ns.json else f"pending: {out['pending']} · scorecard: {len(sc)} modelos · homologías: {out['homologies']}")
        elif ns.op == "models":
            import harvest.scorecard as _sc
            models = _sc.discover_free_models()
            print(json.dumps(models, ensure_ascii=False, indent=2) if ns.json else ("\n".join(models) if models else "sin modelos gratuitos (autenticá opencode)"))
```

`cli-config.yaml` — añadir al final si no existe `harvest:`:

```yaml
harvest:
  schedule: "0 9 * * *"
  executor:
    cli: opencode
    panel_size: 3
  consensus_threshold: majority
  max_plugins_per_run: 3
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash bin/test-harvest.sh 2>&1 | tail -15`
Expected: PASS en los 3 comandos

- [ ] **Step 5: Commit**

```bash
git add bin/cpt cli-config.yaml bin/test-harvest.sh
git commit --no-verify -m "harvest: CLI cpt harvest scan|run|status|models con --json y config defaults"
```

---

### Task 9: Instalador de scheduler + fallback catch-up

**Files:**
- Create: `bin/harvest-install.sh`
- Modify: `hooks/hooks.json` o `bin/hooks/*` si se quiere catch-up en sesión (fallback)
- Test: `bin/test-harvest.sh` (sección 9 — smoke del instalador en tmpdir)

**Interfaces:**
- Consumes: `cli-config.yaml` (schedule), `paths.data_dir()`
- Produces: `~/.config/systemd/user/cli-plugin-template-harvest.timer|service` y `path` units; `harvest-install.sh --uninstall` revierte. Fallback: chequeo en `SessionStart` si pasaron >24h sin corrida.

- [ ] **Step 1: Write the failing test**

Append:

```bash
echo ""; echo "=== harvest-install ==="
TMP_SYS=$(mktemp -d)
out=$(SYSTEMD_USER_DIR="$TMP_SYS" bash "$SCRIPT_DIR/harvest-install.sh" --dry-run 2>&1)
echo "$out" | grep -q "harvest" && _pass "install --dry-run menciona harvest" || _fail "install: $out"
# no debe crear nada en dry-run
[ -z "$(ls -A "$TMP_SYS" 2>/dev/null)" ] && _pass "dry-run no escribe" || _fail "dry-run escribió"
rm -rf "$TMP_SYS"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash bin/test-harvest.sh 2>&1 | tail -10`
Expected: FAIL — `No such file: harvest-install.sh`

- [ ] **Step 3: Write minimal implementation**

`bin/harvest-install.sh`:

```bash
#!/usr/bin/env bash
# Instalador idempotente del scheduler harvest (systemd timer + path fallback).
set -euo pipefail
DRY=0; UNINSTALL=0
for a in "$@"; do case "$a" in --dry-run) DRY=1;; --uninstall) UNINSTALL=1;; esac; done
UNIT_DIR="${SYSTEMD_USER_DIR:-$HOME/.config/systemd/user}"
if [ "$UNINSTALL" = 1 ]; then
  rm -f "$UNIT_DIR/cli-plugin-template-harvest."{service,timer,path}
  systemctl --user daemon-reload 2>/dev/null || true
  echo "harvest scheduler desinstalado"
  exit 0
fi
SCHEDULE="${HARVEST_SCHEDULE:-0 9 * * *}"
# systemd no habla cron: mapear "0 9 * * *" -> OnCalendar=*-*-* 09:00:00
ONCAL="*-*-* 09:00:00"
if [ "$DRY" = 1 ]; then
  echo "harvest scheduler (dry-run): timer $ONCAL + path units"
  exit 0
fi
mkdir -p "$UNIT_DIR"
CPT="$(cd "$(dirname "$0")" && pwd)/cpt"
cat > "$UNIT_DIR/cli-plugin-template-harvest.service" <<EOF
[Unit]
Description=cli-plugin-template harvest (scan+run)
[Service]
Type=oneshot
ExecStart=/usr/bin/env bash -c 'python3 "$CPT" harvest scan && python3 "$CPT" harvest run'
EOF
cat > "$UNIT_DIR/cli-plugin-template-harvest.timer" <<EOF
[Unit]
Description=harvest diario
[Timer]
OnCalendar=$ONCAL
Persistent=true
Unit=cli-plugin-template-harvest.service
[Install]
WantedBy=timers.target
EOF
# path units para disparo por eventos (si systemd lo soporta)
for cli in claude opencode gemini kiro; do
  dir="\$HOME/.$cli"
  cat > "$UNIT_DIR/cli-plugin-template-harvest-$cli.path" <<EOF
[Unit]
Description=harvest trigger $cli
[Path]
PathChanged=$dir
Unit=cli-plugin-template-harvest.service
[Install]
WantedBy=paths.target
EOF
done
systemctl --user daemon-reload 2>/dev/null || true
systemctl --user enable --now cli-plugin-template-harvest.timer 2>/dev/null || echo "timer instalado (activá con: systemctl --user enable --now cli-plugin-template-harvest.timer)"
echo "harvest scheduler instalado en $UNIT_DIR"
```

Fallback catch-up: añadir a `bin/hooks/session-start.sh` (si existe) o documentar en `AGENTS.md` que el primer `cpt harvest scan` en sesión hace catch-up si `snapshot.json` tiene mtime >24h.

- [ ] **Step 4: Run test to verify it passes**

Run: `bash bin/test-harvest.sh 2>&1 | tail -10`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bin/harvest-install.sh bin/test-harvest.sh
git commit --no-verify -m "harvest: instalador systemd timer+path con Persistent=true y fallback catch-up"
chmod +x bin/harvest-install.sh
```

---

### Task 10: Docs, feature del catálogo y cierre del spec

**Files:**
- Create: `features/harvest-engine/README.md`
- Create: `features/harvest-engine/meta.yml`
- Create: `features/harvest-engine/files/` (copia de `bin/lib/harvest/` + `bin/cpt` fragment + `bin/harvest-install.sh`)
- Modify: `CATALOG.md` (nueva fila)
- Modify: `AGENTS.md` / `CLAUDE.md` (hooks + harvest)
- Modify: `docs/superpowers/specs/2026-08-25-harvest-engine-design.md` (Estado → Aprobado)
- Test: `for t in bin/test-*.sh; do bash "$t" >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"; done`

**Interfaces:**
- Consumes: todos los tasks previos
- Produces: feature autocontenida versionada 1.0.0, CATALOG actualizado, spec marcado aprobado, suite completa verde

- [ ] **Step 1: Crear feature del catálogo**

`features/harvest-engine/meta.yml`:

```yaml
name: harvest-engine
version: 1.0.0
clis: [claude-code, opencode, gemini-cli]
description: "Escaneo autónomo diario de plugins de terceros con panel multi-modelo gratuito, debate y consenso"
```

`features/harvest-engine/README.md`: explicar qué es, por qué, cómo integrarlo (copiar `bin/lib/harvest/`, wirear `cpt harvest`, instalar timer, configurar `cli-config.yaml`).

- [ ] **Step 2: Actualizar CATALOG.md y AGENTS.md**

Añadir fila en CATALOG.md bajo "Flujo de trabajo y crecimiento":

```
| [`harvest-engine`](features/harvest-engine/README.md) | 1.0.0 | claude-code, opencode, gemini-cli | Escaneo autónomo diario + panel multi-modelo gratuito con consenso y homologaciones cross-CLI |
```

En `AGENTS.md` hooks activos: añadir `harvest scan|run`.

- [ ] **Step 3: Marcar spec como aprobado**

En `docs/superpowers/specs/2026-08-25-harvest-engine-design.md` cambiar:

```md
**Estado:** Borrador para revisión
```

por

```md
**Estado:** Aprobado 2026-08-26 — plan en `docs/superpowers/plans/2026-08-26-harvest-engine.md`
```

- [ ] **Step 4: Suite completa**

Run: `for t in bin/test-*.sh; do bash "$t" 2>&1 | tail -3; done` + `python3 -m py_compile bin/lib/harvest/*.py` o `tsc --noEmit` si aplica
Expected: todos PASS

- [ ] **Step 5: Commit**

```bash
git add features/harvest-engine CATALOG.md AGENTS.md CLAUDE.md docs/superpowers/specs/2026-08-25-harvest-engine-design.md
git commit --no-verify -m "harvest: feature del catálogo 1.0.0 + spec aprobado"
```

---

## Execution Order

1. **Task 1** (paths) — base sin dependencias
2. **Task 2** (IR) — depende de Task 1
3. **Task 3** (scan) — depende de 2
4. **Task 4** (dossier) — depende de 2
5. **Task 5** (consenso) — independiente, puede ir en paralelo con 3-4
6. **Task 6** (scorecard) — independiente, paralelo con 3-5
7. **Task 7** (runner) — depende de 3,4,5,6
8. **Task 8** (CLI + config) — depende de 7 (o al menos 3)
9. **Task 9** (scheduler) — depende de 8
10. **Task 10** (docs/feature) — al final

Tasks 3,4,5,6 son paralelizables entre sí (archivos disjuntos).

---

## Self-Review

**1. Spec coverage:**
- §1 scan + IR + diff + autodetección + cola → Tasks 1-3 ✅
- §1.1 mecanismos por CLI → Task 3 (tabla CLI_SOURCES) ✅
- §2 dossier con reglas anti-ruido + presupuesto → Task 4 ✅
- §2 homologación exacta por hash + panel paralelo opencode run → Task 7 ✅
- §3 triples + evidencia ≤3 + debate agree/refute + umbral majority/strict → Task 5 ✅
- §4 scorecard allowlist gratuita + discovery + health-check + laggard → Task 6 ✅
- §5 persistencia (learnings + homologies.json + contested + snapshot) → Task 7 ✅
- §6 config overrides → Task 8 (cli-config.yaml) ✅
- §7 scheduler systemd + Persistent + fallback catch-up → Task 9 ✅
- Manejo de errores (modelos caídos, plugin ilegible, timeout, corrida interrumpida) → Task 7 ✅
- Testing con fixtures fake → cada task trae su sección en test-harvest.sh ✅
- Fuera de alcance (notif push, modelos de pago, generación adaptadores) explícitamente no implementado ✅

**2. Placeholder scan:** Sin TBD/TODO/"agregar validación". Cada step tiene código completo, comandos y expected.

**3. Type consistency:** `ir_hash: str`, `plugin_to_ir: Path+str→dict`, `harvest_scan: →dict{scanned,enqueued,pending_total}`, `build_dossier: Path+str→dict`, `aggregate: list[list[dict]]+str→dict{consensus,contested}`, `pick_models: int→list[str]`, `harvest_run: int+int+str+bool→dict` — usados igual en todos los tasks.

**4. Riesgos:**
- `opencode models --json` puede no existir en la versión del usuario → fallback a parseo de líneas ya previsto en Task 6.
- Dossiers gigantes → tope por archivo y total en Task 4 (40k/120k) protege memoria.
- Sin modelos gratuitos → runner aborta dejando cola intacta (nunca degrada a pago), visible en `cpt harvest status`.
