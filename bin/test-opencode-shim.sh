#!/bin/bash
# Tests del plugin de OpenCode (.opencode/, TypeScript). Data dir aislado.
# Runner: bun (nativo TS) → node --experimental-strip-types → skip.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PLUGIN_TS="$REPO_ROOT/.opencode/plugins/cli-plugin-template.ts"

RUNNER=()
if command -v bun >/dev/null; then
  RUNNER=(bun -e)
elif node --experimental-strip-types -e "process.exit(0)" >/dev/null 2>&1; then
  RUNNER=(node --experimental-strip-types --input-type=module -e)
else
  echo "SKIP: sin bun ni node >=22.6 no se puede cargar la capa .ts"
  exit 0
fi

DATA=$(mktemp -d)
export CLI_PLUGIN_TEMPLATE_DATA_DIR="$DATA"
trap 'rm -rf "$DATA" "$EXT"' EXIT

printf '[{"name":"ankify","local_path":"/x","skill_namespaces":["ankify"]}]' > "$DATA/registry.json"
printf '{"type":"user","message":{"content":"ankify no funciona"}}\n' > "$DATA/t.jsonl"
export CPT_TRANSCRIPT_PATH="$DATA/t.jsonl"

echo ""
echo "=== .opencode plugin (proyecto externo: session-start + agentes) ==="

# Proceso 1: cwd en un proyecto de plugin ajeno — el transform debe inyectar el
# stdout del session-start universal; config debe registrar skills + agentes.
EXT=$(mktemp -d)
mkdir -p "$EXT/.claude-plugin"
printf '{"name":"plugin-fantasma"}' > "$EXT/.claude-plugin/plugin.json"

(
  cd "$EXT"
  "${RUNNER[@]}" '
import assert from "node:assert";
const mod = await import(process.env.PLUGIN_TS);
const caps = await mod.default();
let pass = 0;

// config: skills dir + agentes del catálogo registrados (idempotente)
const config = {};
await caps.config(config);
assert(config.skills.paths.length === 1 && config.skills.paths[0].endsWith("/skills"));
assert(config.agent["feedback-harvester"], "feedback-harvester registrado");
assert(config.agent["feedback-harvester"].mode === "subagent");
assert(config.agent["feedback-harvester"].description?.includes("Cosecha fricciones"));
const nAgentes = Object.keys(config.agent).length;
await caps.config(config);
assert(Object.keys(config.agent).length === nAgentes);
console.log("  PASS: config registra skills + agentes (idempotente)"); pass++;

// transform en proyecto externo: inyecta sugerencia de auditoría, una sola vez
const output = { messages: [{ info: { role: "user" }, parts: [{ type: "text", text: "hola" }] }] };
await caps["experimental.chat.messages.transform"]({}, output);
const partes = output.messages[0].parts.length;
assert(partes >= 2, "session-start inyectado");
assert(output.messages[0].parts.some((p) => p.text && p.text.includes("/plugin-audit")));
await caps["experimental.chat.messages.transform"]({}, output);
await caps["experimental.chat.messages.transform"]({}, output);
assert(output.messages[0].parts.length === partes);
console.log("  PASS: session-start externo inyectado una sola vez"); pass++;

console.log(`\nResultado externo: ${pass} passed, 0 failed`);
'
)

echo "=== .opencode plugin (repo propio: bootstrap + Stop) ==="

# Proceso 2: cwd en el repo propio — bootstrap AGENTS.md + Stop hook universal.
cd "$REPO_ROOT"
"${RUNNER[@]}" '
import assert from "node:assert";
const mod = await import(process.env.PLUGIN_TS);
const caps = await mod.default();
let pass = 0;

// transform en repo propio: bootstrap AGENTS.md, una sola vez
const output = { messages: [{ info: { role: "user" }, parts: [{ type: "text", text: "hola" }] }] };
await caps["experimental.chat.messages.transform"]({}, output);
assert(output.messages[0].parts[0].text.includes("cli-plugin-template — bootstrap"));
await caps["experimental.chat.messages.transform"]({}, output); // guard
assert(output.messages[0].parts.length === 2);
console.log("  PASS: bootstrap inyectado una sola vez"); pass++;

// event: Stop dispara el hook (fricción via CPT_TRANSCRIPT_PATH → stdout)
let captured = "";
const write = process.stdout.write.bind(process.stdout);
process.stdout.write = (s) => { captured += s; return true; };
await caps.event({ event: { type: "global.disposed" } });
process.stdout.write = write;
assert(captured.includes("POSSIBLE PLUGIN FRICTION"));
console.log("  PASS: Stop → detecta fricción con transcript"); pass++;

// segundo Stop: idempotente por offset
captured = "";
process.stdout.write = (s) => { captured += s; return true; };
await caps.event({ event: { type: "global.disposed" } });
process.stdout.write = write;
assert(!captured.includes("POSSIBLE PLUGIN FRICTION"));
console.log("  PASS: segundo Stop no repite"); pass++;

console.log(`\nResultado propio: ${pass} passed, 0 failed`);
'
