// Hook `event`: equivalente de Stop de Claude Code — corre en cualquier repo.

import { runStopHook } from "../../lib/stop-hook.ts";

export async function onStop(input: {
  event?: { type?: string };
  type?: string;
}): Promise<void> {
  if ((input?.event?.type ?? input?.type) === "global.disposed") {
    runStopHook();
  }
}
