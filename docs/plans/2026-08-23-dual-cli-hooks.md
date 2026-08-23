# 4 Hooks nuevos con paridad CC ↔ OpenCode — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar 4 hooks (guard del contrato del catálogo, captura de fricción en fallos de test, nudge de intención, snapshot pre-compact) al meta-plugin, implementados para Claude Code y OpenCode.

**Architecture:** Cada hook es un script Python standalone en `bin/hooks/` que lee JSON por stdin (convención existente de `detect-pending-feedback.py`) y se registra en `hooks/hooks.json`. La capa OpenCode espeja la lógica en módulos TS puros bajo `.opencode/lib/` + `hooks/<nombre>/`, compuestos desde el entry ankify. Los tests viven en suites bash `bin/test-*.sh` (entran solas al CI por el loop del workflow) y en extensiones a `bin/test-opencode-shim.sh`.

**Tech Stack:** Python3 stdlib (hooks CC), TypeScript sin build (`@opencode-ai/plugin`: `tool.execute.before/after`), bash test harness propio, bun / node --experimental-strip-types.

## Global Constraints

- NO bumpear versiones a mano: el post-commit auto-bump lo hace y amende el commit (`feat:` → minor). El hash que imprime git es el previo a la enmienda.
- El pre-commit SIEMPRE aconseja con exit 1 en cualquier commit con staging: leerlo y re-commitear con `--no-verify`. Nunca saltarlo sin leer.
- Imports TS con extensión `.ts` explícita; sin enums ni namespaces (fallback node strip-types).
- Suites nuevas llamadas `bin/test-*.sh` entran al CI automáticamente (loop del workflow).
- Prohibido: bloques de script >2 líneas embebidos en SKILL.md (`audit-skill-structure.py` bloquea).
- Hooks CC leen JSON por stdin; PreToolUse: exit 2 + stderr = bloquear; UserPromptSubmit/PostToolUse: stdout = contexto inyectado, exit 0.
- Tests usan `CLI_PLUGIN_TEMPLATE_DATA_DIR` apuntando a tmpdir (patrón de `bin/test-opencode-shim.sh`).
- Registro de plugins: `$CLI_PLUGIN_TEMPLATE_DATA_DIR/registry.json` (default `~/.local/share/cli-plugin-template/`), formato `[{"name","local_path","skill_namespaces"}]`.

## Mapeo de eventos

| Evento CC | OpenCode | Nota |
|---|---|---|
| PreToolUse (Edit\|Write\|MultiEdit) | `tool.execute.before` | OC: abortar lanzando Error |
| PostToolUse (Bash) | `tool.execute.after` | OC: mutar `output.output` agregando hint |
| UserPromptSubmit | `experimental.chat.messages.transform` (existente) | OC: parte extra en el primer mensaje |
| PreCompact | **sin equivalente** | knob documentado, CC-only |

---

### Task 1: Guard del contrato del catálogo (PreToolUse)

**Files:**
- Create: `bin/hooks/catalog-guard.py`
- Create: `bin/test-catalog-hooks.sh` (suite nueva; las tasks 2–4 la extienden)
- Modify: `hooks/hooks.json`

**Interfaces:**
- Produces: script ejecutable `bin/hooks/catalog-guard.py`; entrada stdin `{"tool_name": str, "tool_input": {"file_path": str, "content"?: str}}`; salida: exit 0 silencioso (allow) o exit 2 + stderr (block).
- Reglas v1: (a) crear archivo bajo `features/<name>/` cuando `features/<name>/meta.yml` no existe y el archivo no es `meta.yml` → block "feature nuevo necesita meta.yml"; (b) contenido de `skills/*/SKILL.md` con fenced block de script (>2 líneas) → block citando la regla de modularización.

- [ ] **Step 1: Escribir tests fallando**

Crear `bin/test-catalog-hooks.sh`:

```bash
#!/bin/bash
# Tests de los hooks nuevos del meta-plugin. Data dir aislado.
set -uo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA=$(mktemp -d)
trap 'rm -rf "$DATA"' EXIT
export CLI_PLUGIN_TEMPLATE_DATA_DIR="$DATA"
pass=0 fail=0

run_guard() { printf '%s' "$1" | python3 "$REPO_ROOT/bin/hooks/catalog-guard.py" >/dev/null 2>&1; }
expect_block() {
  if ! run_guard "$1"; then echo "  PASS: $2"; pass=$((pass+1)); else echo "  FAIL: $2 (esperaba bloqueo)"; fail=$((fail+1)); fi
}
expect_allow() {
  if run_guard "$1"; then echo "  PASS: $2"; pass=$((pass+1)); else echo "  FAIL: $2 (esperaba allow)"; fail=$((fail+1)); fi
}

echo ""
echo "=== catalog-guard.py (PreToolUse) ==="
mkdir -p "$REPO_ROOT/features/nuevo-feature"
expect_block '{"tool_name":"Write","tool_input":{"file_path":"'$REPO_ROOT'/features/nuevo-feature/files/x.md","content":"hola"}}' "feature sin meta.yml → block"
printf '{"version":"1.0.0","name":"nuevo-feature"}' > "$REPO_ROOT/features/nuevo-feature/meta.yml"
expect_allow '{"tool_name":"Write","tool_input":{"file_path":"'$REPO_ROOT'/features/nuevo-feature/files/x.md","content":"hola"}}' "feature con meta.yml → allow"
rm -rf "$REPO_ROOT/features/nuevo-feature"
expect_allow '{"tool_name":"Write","tool_input":{"file_path":"'$REPO_ROOT'/README.md","content":"x"}}' "archivo fuera del catálogo → allow"

BLOCK_MD='---\ndescription: x\n---\n# T\n```bash\nlinea1\nlinea2\nlinea3\n```\n'
ALLOW_MD='---\ndescription: x\n---\n# T\n```bash\nlinea1\n```\n'
expect_block '{"tool_name":"Edit","tool_input":{"file_path":"'$REPO_ROOT'/skills/plugin-dev/SKILL.md","content":"'"\$BLOCK_MD"'"}}' "SKILL.md con bloque >2 líneas → block"
expect_allow '{"tool_name":"Edit","tool_input":{"file_path":"'$REPO_ROOT'/skills/plugin-dev/SKILL.md","content":"'"\$ALLOW_MD"'"}}' "SKILL.md con bloque ≤2 líneas → allow"

echo ""
echo "Resultado: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
```

Nota: los casos SKILL.md usan `\n` literales dentro del JSON — si el harness de comillas complica, construir el payload con `python3 -c 'import json,sys;print(json.dumps({...}))'` en vez de interpolar a mano (más robusto, misma aserción).

- [ ] **Step 2: Verificar que falla**

Run: `bash bin/test-catalog-hooks.sh`
Expected: FAIL — `catalog-guard.py` no existe (los 5 casos marcan FAIL).

- [ ] **Step 3: Implementar `bin/hooks/catalog-guard.py`**

```python
#!/usr/bin/env python3
"""PreToolUse guard: hace cumplir el contrato del catálogo EN EL MOMENTO del edit,
no recién en el pre-commit. Lee {tool_name, tool_input{file_path, content?}} por stdin.
exit 2 + stderr = bloquear (convención Claude Code); exit 0 = allow silencioso.
Reglas v1:
  1. features/<name>/ sin meta.yml (y el archivo no ES meta.yml) → block.
  2. skills/*/SKILL.md con fenced block de script >2 líneas → block (regla de
     bin/audit-skill-structure.py, aplicada antes de escribir).
"""
import json
import re
import sys
from pathlib import Path

FENCE = re.compile(r"```(\w+)[^\n]*\n(.*?)```", re.DOTALL)
SCRIPT_LANGS = {"bash", "sh", "python", "python3", "node", "ts", "typescript", "js", "javascript"}
FEATURES_RE = re.compile(r"(^|/)features/([^/]+)/")


def violations(file_path: str, content: str) -> list[str]:
    out: list[str] = []
    m = FEATURES_RE.search(file_path.replace("\\", "/"))
    if m and Path(file_path).name != "meta.yml":
        if not (Path(file_path).parent / "meta.yml").exists():
            out.append(f"features/{m.group(2)}/ no tiene meta.yml — crealo junto al resto del feature")
    base = Path(file_path).name
    if base == "SKILL.md" and "/skills/" in file_path.replace("\\", "/"):
        for lang, body in FENCE.findall(content or ""):
            if lang.lower() in SCRIPT_LANGS and len([l for l in body.split("\n") if l.strip()]) > 2:
                out.append(
                    f"SKILL.md embebe un bloque ```{lang} de más de 2 líneas — va a scripts/ "
                    "(regla de modularización; audit-skill-structure.py lo bloquearía igual)"
                )
                break
    return out


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    tool_input = data.get("tool_input") or {}
    path = tool_input.get("file_path") or ""
    if not path:
        sys.exit(0)
    found = violations(path, tool_input.get("content") or "")
    if not found:
        sys.exit(0)
    print("CATALOG-GUARD: " + "; ".join(found), file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Registrar en `hooks/hooks.json`**

Agregar dentro de `"hooks"` (mantener SessionStart y Stop intactos):

```json
"PreToolUse": [
  {
    "matcher": "Edit|Write|MultiEdit",
    "hooks": [
      { "type": "command", "command": "python3 ${CLAUDE_PLUGIN_ROOT}/bin/hooks/catalog-guard.py" }
    ]
  }
],
```

- [ ] **Step 5: Suite verde**

Run: `bash bin/test-catalog-hooks.sh`
Expected: `5 passed, 0 failed`.

- [ ] **Step 6: Commit**

```bash
git add bin/hooks/catalog-guard.py bin/test-catalog-hooks.sh hooks/hooks.json
git commit --no-verify -m "feat(hooks): guard del contrato del catalogo en PreToolUse"
```

---

### Task 2: Captura de fricción en fallos de test (PostToolUse)

**Files:**
- Create: `bin/hooks/test-failure-nudge.py`
- Modify: `bin/test-catalog-hooks.sh` (agregar sección)
- Modify: `hooks/hooks.json`

**Interfaces:**
- Consumes: patrón de suite del repo (`bin/test-*.sh`).
- Produces: stdin `{"tool_input": {"command": str}, "tool_response": obj}`; stdout una línea de sugerencia si hay fallo de suite; siempre exit 0.

- [ ] **Step 1: Tests fallando** — agregar a `bin/test-catalog-hooks.sh` antes del resumen final:

```bash
NUDGE="$REPO_ROOT/bin/hooks/test-failure-nudge.py"
echo ""
echo "=== test-failure-nudge.py (PostToolUse) ==="
run_nudge() { printf '%s' "$1" | python3 "$NUDGE" 2>/dev/null; }

out=$(run_nudge '{"tool_input":{"command":"bash bin/test-catalog-hooks.sh"},"tool_response":{"success":false}}')
if echo "$out" | grep -q "cpt feedback save"; then echo "  PASS: suite fallida → sugiere feedback"; pass=$((pass+1)); else echo "  FAIL: suite fallida sin sugerencia"; fail=$((fail+1)); fi

out=$(run_nudge '{"tool_input":{"command":"bash bin/test-catalog-hooks.sh"},"tool_response":{"success":true}}')
if [ -z "$out" ]; then echo "  PASS: suite ok → silencio"; pass=$((pass+1)); else echo "  FAIL: suite ok no debe hablar"; fail=$((fail+1)); fi

out=$(run_nudge '{"tool_input":{"command":"ls -la"},"tool_response":{"success":false}}')
if [ -z "$out" ]; then echo "  PASS: comando ajeno → silencio"; pass=$((pass+1)); else echo "  FAIL: ls no es suite"; fail=$((fail+1)); fi
```

- [ ] **Step 2: Verificar fallo** — Run: `bash bin/test-catalog-hooks.sh` → Expected: 3 FAIL nuevos.

- [ ] **Step 3: Implementar `bin/hooks/test-failure-nudge.py`**

```python
#!/usr/bin/env python3
"""PostToolUse: si un comando Bash corrió una suite del repo y falló, sugiere registrar
la fricción vía cpt feedback save (el ciclo growth-engine cerrando en caliente, no al
final de sesión como el Stop hook). stdout = contexto inyectado; siempre exit 0."""
import json
import re
import sys

SUITE_RE = re.compile(r"(bin/test-[\w./-]+\.sh|\bpytest\b|\bnpm (run )?test\b)")


def failed(resp: dict) -> bool:
    # ponytail: heurística sobre formas variables de tool_response; endurecer con datos reales.
    if resp.get("success") is False:
        return True
    code = resp.get("exit_code", resp.get("code"))
    return isinstance(code, int) and code != 0


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not SUITE_RE.search(cmd):
        return
    if not failed(data.get("tool_response") or {}):
        return
    plugin = "cli-plugin-template"  # este repo; generalizar con registry si crece
    print(f"Suite fallida — ¿fricción del plugin? Registrála: bin/cpt feedback save "
          f"{plugin} '<síntoma>' --status pending")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Registrar en `hooks/hooks.json`**

```json
"PostToolUse": [
  {
    "matcher": "Bash",
    "hooks": [
      { "type": "command", "command": "python3 ${CLAUDE_PLUGIN_ROOT}/bin/hooks/test-failure-nudge.py" }
    ]
  }
],
```

- [ ] **Step 5: Suite verde** — Run: `bash bin/test-catalog-hooks.sh` → Expected: `8 passed, 0 failed`.

- [ ] **Step 6: Commit**

```bash
git add bin/hooks/test-failure-nudge.py bin/test-catalog-hooks.sh hooks/hooks.json
git commit --no-verify -m "feat(hooks): nudge de friccion en fallos de test via PostToolUse"
```

---

### Task 3: Nudge de intención (UserPromptSubmit)

**Files:**
- Create: `bin/hooks/intent-nudge.py`
- Modify: `bin/test-catalog-hooks.sh`, `hooks/hooks.json`

**Interfaces:**
- Consumes: `$CLI_PLUGIN_TEMPLATE_DATA_DIR/registry.json`.
- Produces: stdin `{"prompt": str}`; si el prompt matchea vocabulario de intención Y cwd está dentro de un plugin registrado → stdout UNA línea; sino silencio. Exit 0 siempre.

- [ ] **Step 1: Tests fallando** — sección nueva en la suite:

```bash
INTENT="$REPO_ROOT/bin/hooks/intent-nudge.py"
echo ""
echo "=== intent-nudge.py (UserPromptSubmit) ==="
printf '[{"name":"ankify","local_path":"/tmp/proj-ankify","skill_namespaces":["ankify"]}]' > "$DATA/registry.json"

out=$(cd /tmp/proj-ankify && printf '%s' '{"prompt":"integrá versionado al plugin"}' | python3 "$INTENT")
if echo "$out" | grep -q "plugin-dev"; then echo "  PASS: intención en plugin registrado → sugiere router"; pass=$((pass+1)); else echo "  FAIL: intención sin sugerencia"; fail=$((fail+1)); fi

out=$(cd "$REPO_ROOT" && printf '%s' '{"prompt":"integrá versionado al plugin"}' | python3 "$INTENT")
if [ -z "$out" ]; then echo "  PASS: repo propio (sentinel) → silencio"; pass=$((pass+1)); else echo "  FAIL: en el catálogo sobra el nudge"; fail=$((fail+1)); fi

out=$(cd /tmp/proj-ankify && printf '%s' '{"prompt":"qué hora es"}' | python3 "$INTENT")
if [ -z "$out" ]; then echo "  PASS: prompt sin intención → silencio"; pass=$((pass+1)); else echo "  FAIL: falso positivo"; fail=$((fail+1)); fi
mkdir -p /tmp/proj-ankify
```

(Crear `/tmp/proj-ankify` ANTES del primer caso.)

- [ ] **Step 2: Verificar fallo** — Run: `bash bin/test-catalog-hooks.sh` → Expected: 3 FAIL nuevos.

- [ ] **Step 3: Implementar `bin/hooks/intent-nudge.py`**

```python
#!/usr/bin/env python3
"""UserPromptSubmit: si el usuario expresa intención de desarrollo de plugin y está
parado en un plugin registrado (o en el propio catálogo), sugiere la skill router
plugin-dev. Grep puro — corre en TODOS los turnos, tiene que ser barato y callarse."""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

INTENT_RE = re.compile(
    r"\b(integr[áa]|agreg[áa]|sum[áe]|promov[ée]|audit[áa]|revis[áa])\b.*plugin\b"
    r"|\bqu[eé] (me )?falta\b.*plugin\b|\bplugin[- ]dev\b", re.IGNORECASE)


def data_dir() -> Path:
    override = os.environ.get("CLI_PLUGIN_TEMPLATE_DATA_DIR")
    return Path(override) if override else Path.home() / ".local/share/cli-plugin-template"


def registered_cwd() -> bool:
    try:
        registry = json.loads((data_dir() / "registry.json").read_text())
    except Exception:
        return False
    cwd = os.getcwd()
    for entry in registry:
        lp = (entry.get("local_path") or "").rstrip("/")
        if lp and cwd.startswith(lp):
            return True
    return False


def main() -> None:
    try:
        prompt = (json.load(sys.stdin).get("prompt") or "")
    except Exception:
        return
    if not INTENT_RE.search(prompt):
        return
    sentinel = Path(".catalog-root")
    if sentinel.exists() or not registered_cwd():
        return
    print("Intención de desarrollo de plugin detectada — cargá la skill router plugin-dev.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Registrar en `hooks/hooks.json`** (sin matcher):

```json
"UserPromptSubmit": [
  {
    "hooks": [
      { "type": "command", "command": "python3 ${CLAUDE_PLUGIN_ROOT}/bin/hooks/intent-nudge.py" }
    ]
  }
],
```

- [ ] **Step 5: Suite verde** — Run: `bash bin/test-catalog-hooks.sh` → Expected: `11 passed, 0 failed`.

- [ ] **Step 6: Commit**

```bash
git add bin/hooks/intent-nudge.py bin/test-catalog-hooks.sh hooks/hooks.json
git commit --no-verify -m "feat(hooks): nudge del router plugin-dev en UserPromptSubmit"
```

---

### Task 4: Snapshot WIP (PreCompact, CC-only)

**Files:**
- Create: `bin/hooks/wip-snapshot.py`
- Modify: `bin/test-catalog-hooks.sh`, `hooks/hooks.json`

**Interfaces:**
- Produces: escribe `$CLI_PLUGIN_TEMPLATE_DATA_DIR/wip/<ISO>.txt` con branch + status corto + últimos 3 commits; stdout confirma la ruta. Exit 0 siempre. Sin equivalente OpenCode (knob documentado en Task 6).

- [ ] **Step 1: Test fallando**:

```bash
WIP="$REPO_ROOT/bin/hooks/wip-snapshot.py"
echo ""
echo "=== wip-snapshot.py (PreCompact) ==="
out=$(cd "$REPO_ROOT" && printf '{}' | python3 "$WIP")
snap=$(ls -t "$DATA"/wip/*.txt 2>/dev/null | head -1)
if [ -n "$snap" ] && grep -q "^## Branch" "$snap"; then echo "  PASS: snapshot creado con branch"; pass=$((pass+1)); else echo "  FAIL: sin snapshot utilizable"; fail=$((fail+1)); fi
```

- [ ] **Step 2: Verificar fallo** — Run: `bash bin/test-catalog-hooks.sh` → Expected: 1 FAIL nuevo.

- [ ] **Step 3: Implementar `bin/hooks/wip-snapshot.py`**

```python
#!/usr/bin/env python3
"""PreCompact: antes de compactar contexto, deja un snapshot mínimo del estado del repo
(branch, status, commits recientes) en el store, para que la sesión post-compacto no
arranque ciega. CC-only: OpenCode no expone evento equivalente."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


def main() -> None:
    try:
        json.load(sys.stdin)
    except Exception:
        pass
    from paths import data_dir  # bin/lib/paths.py ya resuelve CLI_PLUGIN_TEMPLATE_DATA_DIR
    wip = data_dir() / "wip"
    wip.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    body = (
        f"## Branch\n{git('rev-parse', '--abbrev-ref', 'HEAD')}\n\n"
        f"## Status\n{git('status', '--short')}\n\n"
        f"## Últimos commits\n{git('log', '--oneline', '-3')}\n"
    )
    path = wip / f"{stamp}.txt"
    path.write_text(body)
    print(f"WIP snapshot → {path}")


if __name__ == "__main__":
    main()
```

Verificar primero cómo exporta `data_dir()` `bin/lib/paths.py` (si el nombre difiere, usar el real; si no existe helper, inline el mismo default del intent-nudge).

- [ ] **Step 4: Registrar en `hooks/hooks.json`**:

```json
"PreCompact": [
  {
    "matcher": "manual|auto",
    "hooks": [
      { "type": "command", "command": "python3 ${CLAUDE_PLUGIN_ROOT}/bin/hooks/wip-snapshot.py" }
    ]
  }
],
```

- [ ] **Step 5: Suite completa verde** — Run: `bash bin/test-catalog-hooks.sh && bash bin/test-hooks.sh`
Expected: `12 passed, 0 failed` + suite vieja de hooks intacta.

- [ ] **Step 6: Commit**

```bash
git add bin/hooks/wip-snapshot.py bin/test-catalog-hooks.sh hooks/hooks.json
git commit --no-verify -m "feat(hooks): snapshot WIP en PreCompact"
```

---

### Task 5: Paridad OpenCode (guard + after-hook + nudge)

**Files:**
- Create: `.opencode/lib/catalog-guard.ts`
- Create: `.opencode/hooks/tool-guard/index.ts`
- Create: `.opencode/hooks/bootstrap-inject/intent.ts`
- Modify: `.opencode/plugins/cli-plugin-template.ts`, `.opencode/hooks/bootstrap-inject/index.ts`, `bin/test-opencode-shim.sh`

**Interfaces:**
- Consumes: SDK `"tool.execute.before"(input:{tool},output:{args})` y `"tool.execute.after"(input:{tool,args},output:{title,output})` (shapes confirmadas en @opencode-ai/plugin).
- Produces: `violations(args): string[]` (misma lógica que el .py); `beforeHook(input,output): Promise<void>` que lanza Error ante violación; `intentPart(text): string|null`.

- [ ] **Step 1: Tests fallando** — extender `bin/test-opencode-shim.sh` (en el proceso del proyecto externo, tras los asserts existentes):

```js
// tool.execute.before: feature sin meta.yml → throw; archivo suelto → pasa
const guard = await import(new URL("../lib/catalog-guard.ts", process.env.PLUGIN_TS).href).catch(() => null);
let threw = false;
try {
  await caps["tool.execute.before"]({ tool: "write" }, { args: { filePath: "/ext/features/fanta/files/a.md", content: "x" } });
} catch { threw = true; }
assert(threw, "guard bloquea feature sin meta.yml");
await caps["tool.execute.before"]({ tool: "write" }, { args: { filePath: "/ext/README.md", content: "x" } });
console.log("  PASS: tool.execute.before homologa el guard"); pass++;

// tool.execute.after: bash con suite fallida agrega hint al output
const after = { title: "t", output: "FAIL: algo", metadata: {} };
await caps["tool.execute.after"]({ tool: "bash", args: { command: "bash bin/test-x.sh" } }, after);
assert(after.output.includes("cpt feedback save"), "hint de fricción presente");
console.log("  PASS: tool.execute.after sugiere feedback en fallo"); pass++;

// nudge de intención en el transform (proyecto externo registrado)
process.env.CLI_PLUGIN_TEMPLATE_DATA_DIR && require("node:fs").writeFileSync(
  process.env.CLI_PLUGIN_TEMPLATE_DATA_DIR + "/registry.json",
  JSON.stringify([{ name: "fantasma", local_path: process.cwd(), skill_namespaces: [] }]));
const out2 = { messages: [{ info: { role: "user" }, parts: [{ type: "text", text: "integrá health-check acá" }] }] };
await caps["experimental.chat.messages.transform"]({}, out2);
assert(out2.messages[0].parts.some((p) => p.text?.includes("plugin-dev")), "nudge de intención inyectado");
console.log("  PASS: transform agrega nudge de intención"); pass++;
```

(Ajustar `pass++` al contador existente del shim y la forma de escribir el registry al estilo real del archivo.)

- [ ] **Step 2: Verificar fallo** — Run: `bash bin/test-opencode-shim.sh` → Expected: FAIL (capacidades no existen).

- [ ] **Step 3: Implementar `.opencode/lib/catalog-guard.ts`**

```ts
// Espejo TS de bin/hooks/catalog-guard.py: mismas 2 reglas, un solo lugar por regla.
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";

const FEATURES_RE = /(^|\/)features\/([^/]+)\//;
const FENCE = /```(\w+)[^\n]*\n([\s\S]*?)```/g;
const SCRIPT_LANGS = new Set(["bash", "sh", "python", "python3", "node", "ts", "typescript", "js", "javascript"]);

export function violations(filePath: string, content: string): string[] {
  const out: string[] = [];
  const norm = filePath.replace(/\\/g, "/");
  const m = FEATURES_RE.exec(norm);
  if (m && norm.split("/").pop() !== "meta.yml") {
    if (!existsSync(join(dirname(filePath), "meta.yml"))) {
      out.push(`features/${m[2]}/ no tiene meta.yml`);
    }
  }
  const base = norm.split("/").pop();
  if (base === "SKILL.md" && norm.includes("/skills/")) {
    for (const [, lang, body] of (content || "").matchAll(FENCE)) {
      const lineas = body.split("\n").filter((l) => l.trim()).length;
      if (SCRIPT_LANGS.has(lang.toLowerCase()) && lineas > 2) {
        out.push(`bloque \`\`\`${lang} de ${lineas} líneas — va a scripts/`);
        break;
      }
    }
  }
  return out;
}
```

- [ ] **Step 4: Implementar `.opencode/hooks/tool-guard/index.ts`**

```ts
// Paridad de PreToolUse (throw = bloquear) y PostToolUse (mutar output con hint).
import { violations } from "../../lib/catalog-guard.ts";

export async function beforeHook(_input: unknown, output: { args: Record<string, unknown> }): Promise<void> {
  const args = output?.args ?? {};
  const path = String(args.file_path ?? args.filePath ?? "");
  if (!path) return;
  const found = violations(path, String(args.content ?? ""));
  if (found.length) throw new Error(`CATALOG-GUARD: ${found.join("; ")}`);
}

const SUITE_RE = /(bin\/test-[\w./-]+\.sh|\bpytest\b)/;

export async function afterHook(input: { tool?: string; args?: Record<string, unknown> }, output: { output?: string }): Promise<void> {
  if ((input?.tool ?? "") !== "bash") return;
  const cmd = String(input?.args?.command ?? "");
  const resp = String(output?.output ?? "");
  if (!SUITE_RE.test(cmd)) return;
  if (!/(FAIL|failed|✗)/i.test(resp)) return;
  output.output += "\nSuite fallida — ¿fricción del plugin? bin/cpt feedback save cli-plugin-template '<síntoma>' --status pending";
}
```

- [ ] **Step 5: Nudge en el transform — `.opencode/hooks/bootstrap-inject/intent.ts`**

```ts
// Paridad de UserPromptSubmit: el transform ya toca el primer mensaje user; acá
// decidimos si además del bootstrap corresponde una línea del router plugin-dev.
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const INTENT_RE = /\b(integr[áa]|agreg[áa]|promov[ée]|audit[áa]|revis[áa])\b.*plugin\b|\bqu[eé] (me )?falta\b.*plugin\b/i;

function registeredCwd(): boolean {
  const dir = process.env.CLI_PLUGIN_TEMPLATE_DATA_DIR
    ?? join(process.env.HOME ?? "", ".local/share/cli-plugin-template");
  try {
    const registry = JSON.parse(readFileSync(join(dir, "registry.json"), "utf8")) as Array<{ local_path?: string }>;
    return registry.some((e) => e.local_path && process.cwd().startsWith(e.local_path));
  } catch {
    return false;
  }
}

export function intentNudge(firstMessageText: string): string | null {
  if (!INTENT_RE.test(firstMessageText)) return null;
  if (existsSync(".catalog-root")) return null;
  if (!registeredCwd()) return null;
  return "Intención de desarrollo de plugin detectada — usá la skill router plugin-dev.";
}
```

En `bootstrap-inject/index.ts`, después de calcular `injections`, agregar:

```ts
import { intentNudge } from "./intent.ts";
const texto = firstUser.parts.map((p) => p.text ?? "").join("\n");
const nudge = intentNudge(texto);
if (nudge) injections.push(nudge);
```

- [ ] **Step 6: Componer en el entry `.opencode/plugins/cli-plugin-template.ts`**

```ts
import { beforeHook, afterHook } from "../hooks/tool-guard";

export default (async () => {
  return {
    config: injectConfig,
    "experimental.chat.messages.transform": injectBootstrap,
    event: onStop,
    "tool.execute.before": beforeHook,
    "tool.execute.after": afterHook,
  };
}) satisfies Plugin;
```

- [ ] **Step 7: Typecheck + suites verdes**

Run: `bun x tsc --noEmit && bash bin/test-opencode-shim.sh && bash bin/test-catalog-hooks.sh`
Expected: tsc limpio, todas las assertions PASS.

- [ ] **Step 8: Commit**

```bash
git add .opencode/ bin/test-opencode-shim.sh
git commit --no-verify -m "feat(opencode): paridad de tool.execute.before/after y nudge de intención"
```

---

### Task 6: Documentación de paridad y knobs

**Files:**
- Modify: `AGENTS.md` (= symlink `CLAUDE.md`)
- Modify: `skills/plugin-dev/references/tool-mapping.md`

- [ ] **Step 1: AGENTS.md — sección "Modo plugin"**, actualizar la lista de hooks:

Texto a insertar después de la frase del hook SessionStart existente:
"Hooks activos: `SessionStart` (sugiere auditoría la primera vez), `Stop` (cosecha fricción pendiente), `PreToolUse` en Edit/Write (guard del contrato del catálogo: meta.yml y modularización de skills), `PostToolUse` en Bash (sugiere `cpt feedback save` ante fallos de suite), `UserPromptSubmit` (nudge del router plugin-dev en plugins registrados) y `PreCompact` (snapshot WIP al store — solo Claude Code: OpenCode no expone evento equivalente)."

- [ ] **Step 2: `references/tool-mapping.md`** — agregar filas a la tabla de hooks:

| Claude Code | OpenCode | Nota |
|---|---|---|
| `PreToolUse` | `tool.execute.before` | OC bloquea lanzando `Error`; CC usa exit 2 + stderr |
| `PostToolUse` | `tool.execute.after` | CC inyecta stdout; OC muta `output.output` |
| `UserPromptSubmit` | `experimental.chat.messages.transform` | OC: parte extra en el primer mensaje user |
| `PreCompact` | *(sin equivalente)* | knob: solo Claude Code |

- [ ] **Step 3: Batería completa**

Run: `for t in bin/test-*.sh; do bash "$t" || exit 1; done && bun x tsc --noEmit`
Expected: 15/15 suites verdes (13 actuales + test-catalog-hooks + ninguna eliminada), tsc limpio.

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md CLAUDE.md skills/plugin-dev/references/tool-mapping.md
git commit --no-verify -m "docs(hooks): paridad CC/OpenCode de los 4 hooks nuevos"
```

---

## Self-Review

- **Cobertura**: 4 hooks propuestos → Tasks 1–4 (CC) + Task 5 (OC) + Task 6 (docs). PreCompact CC-only explícito en mapping y docs. ✓
- **Placeholders**: ningún TBD; único punto abierto declarado es verificar el nombre exacto de `data_dir()` en `bin/lib/paths.py` (Task 4 Step 3 tiene fallback inline). ✓
- **Tipos/consistencia**: `violations(path, content)` firma idéntica py/ts; nombres de caps OC (`tool.execute.before/after`) verificados contra el .d.ts instalado. ✓
