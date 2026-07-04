#!/bin/bash
# Tests del plugin de OpenCode (.opencode/). Data dir aislado; skip sin node.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
command -v node >/dev/null || { echo "SKIP: node no disponible"; exit 0; }

DATA=$(mktemp -d)
export CLI_PLUGIN_TEMPLATE_DATA_DIR="$DATA"
trap 'rm -rf "$DATA"' EXIT

printf '[{"name":"ankify","local_path":"/x","skill_namespaces":["ankify"]}]' > "$DATA/registry.json"
printf '{"type":"user","message":{"content":"ankify no funciona"}}\n' > "$DATA/t.jsonl"
export CPT_TRANSCRIPT_PATH="$DATA/t.jsonl"

echo ""
echo "=== .opencode plugin ==="

cd "$REPO_ROOT" && node --input-type=module -e '
import assert from "node:assert";
const mod = await import("./.opencode/plugins/cli-plugin-template.js");
const caps = await mod.default();
let pass = 0;

// config: registra el skills dir del plugin (path absoluto, no relativo al cwd)
const config = {};
await caps.config(config);
assert(config.skills.paths.length === 1 && config.skills.paths[0].endsWith("/skills"));
await caps.config(config); // idempotente
assert(config.skills.paths.length === 1);
console.log("  PASS: config registra skills dir (idempotente)"); pass++;

// transform: inyecta bootstrap en el primer mensaje de usuario, una sola vez
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

console.log(`\nResultado: ${pass} passed, 0 failed`);
'
