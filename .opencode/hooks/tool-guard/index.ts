// Paridad de PreToolUse (throw = bloquear) y PostToolUse (mutar output con hint).
import { violations } from "../../lib/catalog-guard.ts";

export async function beforeHook(
  _input: unknown,
  output: { args: Record<string, unknown> },
): Promise<void> {
  const args = output?.args ?? {};
  const path = String(args.file_path ?? args.filePath ?? "");
  if (!path) return;
  // paridad con el .py (`content or new_string`): los edits llegan por new_string
  const text = String(args.content ?? args.new_string ?? "");
  const found = violations(path, text);
  if (found.length) throw new Error(`CATALOG-GUARD: ${found.join("; ")}`);
}

const SUITE_RE = /(bin\/test-[\w./-]+\.sh|\bpytest\b)/;

export async function afterHook(
  input: { tool?: string; args?: Record<string, unknown> },
  output: { output?: string },
): Promise<void> {
  if ((input?.tool ?? "") !== "bash") return;
  const cmd = String(input?.args?.command ?? "");
  const resp = String(output?.output ?? "");
  if (!SUITE_RE.test(cmd)) return;
  // requiere conteo >0: "0 failed" en corridas verdes no debe hablar
  if (!/[1-9]\d* +fail/i.test(resp)) return;
  output.output += "\nSuite fallida — ¿fricción del plugin? bin/cpt feedback save cli-plugin-template '<síntoma>' --status pending";
}
