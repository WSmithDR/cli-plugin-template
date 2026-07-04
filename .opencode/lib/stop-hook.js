// Adaptador OpenCode del Stop hook (pending feedback + detección de fricción).
// La lógica vive en bin/hooks/detect-pending-feedback.py; acá solo se cumple el
// contrato universal: JSON por stdin → {"systemMessage": ...} por stdout.

import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { STOP_HOOK } from "./paths.js";

export function runStopHook() {
  try {
    if (!existsSync(STOP_HOOK)) return;
    // ponytail: OpenCode no expone un transcript .jsonl como Claude Code; si el
    // host puede proveer uno lo pasa por CPT_TRANSCRIPT_PATH y la detección de
    // fricción se activa sola. Sin transcript, igual reporta feedbacks pendientes.
    const input = JSON.stringify({
      transcript_path: process.env.CPT_TRANSCRIPT_PATH || "",
    });
    const output = execFileSync("python3", [STOP_HOOK], {
      encoding: "utf8",
      timeout: 5000,
      input,
    }).trim();
    if (!output) return;
    const result = JSON.parse(output);
    if (result.systemMessage) {
      process.stdout.write(`\n${result.systemMessage}\n`);
    }
  } catch {}
}
