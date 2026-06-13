// Plugin de OpenCode para cli-plugin-template.
//
// Modo dual:
//   Repo propio (CWD dentro del repo): injecta bootstrap + corre Stop hook
//   Repo ajeno (proyectos de terceros): solo corre Stop hook (pending feedback check)
//
// Hook mapping OpenCode ↔ Claude Code:
//   SessionStart          → experimental.chat.messages.transform
//   Stop                  → event({ type: "global.disposed" })
//   PreToolUse            → tool.execute.before
//   PostToolUse           → tool.execute.after

import { execSync } from "node:child_process";
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

function runPendingFeedbackCheck() {
  try {
    const script = join(REPO_ROOT, "bin", "hooks", "detect-pending-feedback.sh");
    if (!existsSync(script)) return;
    const output = execSync(`bash "${script}"`, {
      encoding: "utf8",
      timeout: 5000,
    }).trim();
    if (!output) return;
    const result = JSON.parse(output);
    if (result.systemMessage) {
      process.stdout.write(`\n${result.systemMessage}\n`);
    }
  } catch {}
}

export const CliPluginTemplate = async () => {
  const inOwnRepo = isInOwnRepo();
  const capabilities = {};

  // SessionStart equivalent: inject bootstrap only in own repo
  if (inOwnRepo) {
    const bootstrap = loadBootstrap();
    capabilities["experimental.chat.messages.transform"] = async ({ messages }) => {
      if (Array.isArray(messages) && messages.length > 0) {
        messages.unshift({ role: "system", content: bootstrap });
      }
      return { messages };
    };
  }

  // Stop equivalent: pending feedback check — runs in ANY repo
  capabilities["event"] = async ({ type }) => {
    if (type === "global.disposed") {
      runPendingFeedbackCheck();
    }
  };

  return capabilities;
};

export default CliPluginTemplate;
