// Hook `event`: equivalente de PreCompact de Claude Code — deja un snapshot WIP
// (branch, status, commits recientes) en el store antes de que la compactación
// tire el contexto. Reusa bin/hooks/wip-snapshot.py, misma fuente que CC.

import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { WIP_SNAPSHOT } from "../../lib/paths.ts";

export function onCompacted(input: {
  event?: { type?: string };
  type?: string;
}): void {
  if ((input?.event?.type ?? input?.type) !== "session.compacted") return;
  try {
    if (!existsSync(WIP_SNAPSHOT)) return;
    execFileSync("python3", [WIP_SNAPSHOT], {
      encoding: "utf8",
      timeout: 5000,
      input: "{}",
    });
  } catch {} // ponytail: best-effort, igual que en CC — no puede romper la compactación
}
