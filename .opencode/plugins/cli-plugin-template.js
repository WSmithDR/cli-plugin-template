// Plugin de OpenCode para cli-plugin-template.
//
// GUARD: solo se activa si el CWD está dentro del repo de cli-plugin-template
// (detectado via sentinel .catalog-root). Si se registra en otro proyecto (ej:
// ankify), este plugin es no-op — evita inyectar bootstrap en sesiones ajenas.
//
// OpenCode no auto-descubre AGENTS.md ni el skill de entrada, así que inyectamos
// el bootstrap en el primer mensaje de cada sesión.
// El contenido se lee de AGENTS.md (estándar de facto) para no duplicar la guía.

import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const SENTINEL = join(REPO_ROOT, ".catalog-root");

function isInOwnRepo() {
  try {
    return existsSync(SENTINEL) && process.cwd().startsWith(REPO_ROOT);
  } catch {
    return false;
  }
}

function loadBootstrap() {
  let agents = "";
  try {
    agents = readFileSync(join(REPO_ROOT, "AGENTS.md"), "utf8");
  } catch {
    agents = "";
  }
  return [
    "## cli-plugin-template — bootstrap (OpenCode)",
    "",
    "Este proyecto es el meta-plugin cli-plugin-template. Para guiar el desarrollo",
    "de plugins, usá las skills del catálogo en `skills/` en vez de improvisar:",
    "el entry point es `skills/plugin-dev/SKILL.md` (router), que enruta a",
    "`plugin-audit`, `plugin-feature`, `plugin-recommend` y `plugin-promote`.",
    "",
    "Las skills nombran tools de Claude Code (`Skill`, `Task`, `Read`, `Edit`).",
    "Traducí esos nombres con `skills/plugin-dev/references/tool-mapping.md`.",
    "",
    "--- AGENTS.md ---",
    agents,
  ].join("\n");
}

export const CliPluginTemplate = async () => {
  if (!isInOwnRepo()) {
    return {};
  }

  const bootstrap = loadBootstrap();
  return {
    "experimental.chat.messages.transform": async ({ messages }) => {
      if (Array.isArray(messages) && messages.length > 0) {
        messages.unshift({ role: "system", content: bootstrap });
      }
      return { messages };
    },
  };
};

export default CliPluginTemplate;
