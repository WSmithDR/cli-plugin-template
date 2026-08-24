// Resolución de rutas del plugin para OpenCode (espejo de bin/lib/paths.py:
// único lugar que sabe dónde vive cada cosa).

import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const REPO_ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
export const SKILLS_DIR = join(REPO_ROOT, "skills");
export const AGENTS_DIR = join(REPO_ROOT, "agents");
export const STOP_HOOK = join(REPO_ROOT, "bin", "hooks", "detect-pending-feedback.py");
export const WIP_SNAPSHOT = join(REPO_ROOT, "bin", "hooks", "wip-snapshot.py");
export const SESSION_START_SH = join(REPO_ROOT, "bin", "hooks", "session-start.sh");
export const AGENTS_MD = join(REPO_ROOT, "AGENTS.md");

const SENTINEL = join(REPO_ROOT, ".catalog-root");

export function isInOwnRepo(): boolean {
  try {
    return existsSync(SENTINEL) && process.cwd().startsWith(REPO_ROOT);
  } catch {
    return false;
  }
}
