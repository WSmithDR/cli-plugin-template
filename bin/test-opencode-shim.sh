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

// tool.execute.before: feature sin meta.yml → throw; README suelto → pasa
let threw = false;
try {
  await caps["tool.execute.before"](
    { tool: "write", sessionID: "s", callID: "c" },
    { args: { filePath: process.cwd() + "/features/fanta/files/a.md", content: "x" } },
  );
} catch { threw = true; }
assert(threw, "guard bloquea feature sin meta.yml");
await caps["tool.execute.before"](
  { tool: "write", sessionID: "s", callID: "c" },
  { args: { filePath: process.cwd() + "/README.md", content: "x" } },
);
console.log("  PASS: tool.execute.before homologa el guard"); pass++;

// ruta absoluta hacia un feature CON meta.yml existente → NO debe bloquear
const fs0 = await import("node:fs");
fs0.mkdirSync(process.cwd() + "/features/real/files", { recursive: true });
fs0.writeFileSync(process.cwd() + "/features/real/meta.yml", "version: 1.0.0\n");
await caps["tool.execute.before"](
  { tool: "write", sessionID: "s", callID: "c" },
  { args: { filePath: process.cwd() + "/features/real/files/a.md", content: "x" } },
);
console.log("  PASS: ruta absoluta con meta.yml existente no bloquea"); pass++;

// edit sobre SKILL.md con new_string que embebe script >2 líneas → bloquear
let threwEdit = false;
try {
  await caps["tool.execute.before"](
    { tool: "edit", sessionID: "s", callID: "c" },
    { args: { file_path: process.cwd() + "/skills/alfa/SKILL.md", new_string: "```bash\nuno\ndos\ntres\n```" } },
  );
} catch { threwEdit = true; }
assert(threwEdit, "guard escanea new_string");
console.log("  PASS: tool.execute.before escanea new_string"); pass++;

// tool.execute.after: bash con suite fallida agrega hint al output (conteo >0)
const after = { title: "t", output: "Resultado: 3 passed, 2 failed", metadata: {} };
await caps["tool.execute.after"](
  { tool: "bash", sessionID: "s", callID: "c", args: { command: "bash bin/test-x.sh" } },
  after,
);
assert(after.output.includes("cpt feedback save"), "hint de fricción presente");
console.log("  PASS: tool.execute.after sugiere feedback en fallo"); pass++;

// nudge de intención en el transform (proyecto externo registrado)
const fsmod = await import("node:fs");
fsmod.writeFileSync(
  process.env.CLI_PLUGIN_TEMPLATE_DATA_DIR + "/registry.json",
  JSON.stringify([{ name: "fantasma", local_path: process.cwd(), skill_namespaces: [] }]),
);
const out2 = { messages: [{ info: { role: "user" }, parts: [{ type: "text", text: "integrá health-check acá" }] }] };
await caps["experimental.chat.messages.transform"]({}, out2);
assert(out2.messages[0].parts.some((p) => p.text?.includes("plugin-dev")), "nudge de intención inyectado");
console.log("  PASS: transform agrega nudge de intención"); pass++;

// triggers restaurados: sumá (verbo) y plugin-dev (literal)
for (const texto of ["sumá el feature x al catálogo", "plugin-dev me sirve para esto"]) {
  const out3 = { messages: [{ info: { role: "user" }, parts: [{ type: "text", text: texto }] }] };
  await caps["experimental.chat.messages.transform"]({}, out3);
  assert(
    out3.messages[0].parts.some((p) => p.text?.includes("plugin-dev")),
    `nudge faltante para trigger: ${texto}`,
  );
}
console.log("  PASS: triggers de intención restaurados (sumá / plugin-dev)"); pass++;

console.log(`\nResultado externo: ${pass} passed, 0 failed`);
'
)

echo "=== .opencode plugin (repo propio: bootstrap + Stop) ==="

# restaurar registry original (la fase externa lo sobrescribió con su proyecto)
printf '[{"name":"ankify","local_path":"/x","skill_namespaces":["ankify"]}]' > "$DATA/registry.json"

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

// tool.execute.after: suite verde no habla; con fallos sí sugiere feedback
const green = { output: "Resultado: 3 passed, 0 failed" };
await caps["tool.execute.after"]({ tool: "bash", args: { command: "bash bin/test-catalog-hooks.sh" } }, green);
assert(!green.output.includes("Suite fallida"));
console.log("  PASS: suite verde → silencio"); pass++;
const red = { output: "Resultado: 3 passed, 2 failed" };
await caps["tool.execute.after"]({ tool: "bash", args: { command: "bash bin/test-catalog-hooks.sh" } }, red);
assert(red.output.includes("Suite fallida"));
console.log("  PASS: suite con fallos → nudge"); pass++;

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
