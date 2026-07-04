// Plugin de OpenCode para cli-plugin-template. Entry point: solo compone los
// módulos de .opencode/lib/ (paths, bootstrap, stop-hook).
//
// Hook mapping OpenCode ↔ Claude Code (detalle en
// skills/plugin-dev/references/tool-mapping.md):
//   skills auto-registradas  → config (push a config.skills.paths, patrón superpowers)
//   SessionStart             → experimental.chat.messages.transform (solo repo propio)
//   Stop                     → event global.disposed (pending feedback + fricción, en CUALQUIER repo)

import { SKILLS_DIR, isInOwnRepo } from "../lib/paths.js";
import { BOOTSTRAP_MARKER, getBootstrap } from "../lib/bootstrap.js";
import { runStopHook } from "../lib/stop-hook.js";

export const CliPluginTemplate = async () => ({
  // Registra las skills del catálogo en el host, resueltas desde la ubicación del
  // plugin (no del CWD): funcionan aunque el plugin esté instalado en otro proyecto.
  config: async (config) => {
    config.skills = config.skills || {};
    config.skills.paths = config.skills.paths || [];
    if (!config.skills.paths.includes(SKILLS_DIR)) {
      config.skills.paths.push(SKILLS_DIR);
    }
  },

  // Bootstrap en el PRIMER mensaje de usuario (no system: evita token bloat por
  // turno y modelos que rechazan múltiples system messages), con guard anti
  // doble inyección — el hook dispara en cada step del agente.
  "experimental.chat.messages.transform": async (_input, output) => {
    if (!isInOwnRepo()) return;
    const bootstrap = getBootstrap();
    if (!bootstrap || !output?.messages?.length) return;
    const firstUser = output.messages.find((m) => m?.info?.role === "user");
    if (!firstUser?.parts?.length) return;
    if (firstUser.parts.some((p) => p.type === "text" && p.text?.includes(BOOTSTRAP_MARKER))) {
      return;
    }
    const ref = firstUser.parts[0];
    firstUser.parts.unshift({ ...ref, type: "text", text: getBootstrap() });
  },

  // Stop equivalent — corre en cualquier repo.
  event: async (input) => {
    const type = input?.event?.type ?? input?.type;
    if (type === "global.disposed") {
      runStopHook();
    }
  },
});

export default CliPluginTemplate;
