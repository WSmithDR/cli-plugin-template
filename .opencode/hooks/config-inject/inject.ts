// Hook `config`: registra skills del catálogo resueltas desde la ubicación del
// plugin (no del CWD) y los agentes de agents/ — funciona aunque el plugin esté
// instalado en otro proyecto.

import { SKILLS_DIR } from "../../lib/paths.ts";
import { registerAgents } from "./discover-agents.ts";

export async function injectConfig(config: Record<string, any>): Promise<void> {
  config.skills = config.skills || {};
  config.skills.paths = config.skills.paths || [];
  if (!config.skills.paths.includes(SKILLS_DIR)) {
    config.skills.paths.push(SKILLS_DIR);
  }
  registerAgents(config);
}
