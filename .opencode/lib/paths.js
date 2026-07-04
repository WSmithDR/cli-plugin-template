// Resolución de rutas del plugin para OpenCode (espejo de bin/lib/paths.py:
// único lugar que sabe dónde vive cada cosa).

import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const REPO_ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
export const SKILLS_DIR = join(REPO_ROOT, "skills");
export const STOP_HOOK = join(REPO_ROOT, "bin", "hooks", "detect-pending-feedback.py");
export const AGENTS_MD = join(REPO_ROOT, "AGENTS.md");

const SENTINEL = join(REPO_ROOT, ".catalog-root");

export function isInOwnRepo() {
  try {
    return existsSync(SENTINEL) && process.cwd().startsWith(REPO_ROOT);
  } catch {
    return false;
  }
}
