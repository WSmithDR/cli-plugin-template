// Registra los agentes de agents/ en la config de OpenCode (patrón ankify):
// se definen una sola vez en formato neutral —name/description en frontmatter,
// instrucciones en el cuerpo— y acá se traducen a lo que OpenCode espera.
// Sin `tools`: los subagents de OpenCode ya traen bash/read/grep por defecto.

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { AGENTS_DIR } from "../../lib/paths.ts";

type OpenCodeAgent = { description?: string; prompt: string; mode: "subagent" };

function parseFrontmatter(md: string): { name: string; description: string; body: string } {
  const fm = /^---\n([\s\S]*?)\n---\n?/.exec(md);
  let name = "";
  let description = "";
  if (fm) {
    for (const line of fm[1].split("\n")) {
      const kv = /^(name|description):\s*(.+)$/.exec(line.trim());
      if (!kv) continue;
      const value = kv[2].trim().replace(/^["']|["']$/g, "");
      if (kv[1] === "name") name = value;
      else description = value;
    }
  }
  return { name, description, body: md.replace(/^---\n[\s\S]*?\n---\n?/, "").trim() };
}

export function discoverAgents(): Record<string, OpenCodeAgent> {
  const agents: Record<string, OpenCodeAgent> = {};
  if (!existsSync(AGENTS_DIR)) return agents;
  for (const entry of readdirSync(AGENTS_DIR, { withFileTypes: true })) {
    if (!entry.isFile() || !entry.name.endsWith(".md")) continue;
    const { name, description, body } = parseFrontmatter(
      readFileSync(join(AGENTS_DIR, entry.name), "utf8"),
    );
    if (!name || !body) continue;
    agents[name] = { description: description || undefined, prompt: body, mode: "subagent" };
  }
  return agents;
}

export function registerAgents(config: { agent?: Record<string, unknown> }): void {
  config.agent = config.agent || {};
  for (const [name, agent] of Object.entries(discoverAgents())) {
    // No se pisa lo que el usuario ya definió.
    if (!config.agent[name]) config.agent[name] = agent;
  }
}
