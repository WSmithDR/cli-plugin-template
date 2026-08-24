// Paridad de UserPromptSubmit (nudge de intención): el transform ya toca el
// primer mensaje user; acá decidimos si además del bootstrap corresponde una
// línea del router plugin-dev. Gate duro: solo proyectos registrados.
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

// ponytail: stems suaves sin frontera — imperativos con tilde ("integrá",
// "sumá") y el literal plugin-dev; el gate real es registeredCwd().
const INTENT_RE = /(integra|agrega|sum[ae]|promov|audit|revis)|que (me )?falta|plugin[- ]dev/i;

function stripAccents(text: string): string {
  return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function registeredCwd(): boolean {
  const dir = process.env.CLI_PLUGIN_TEMPLATE_DATA_DIR
    ?? join(process.env.HOME ?? "", ".local/share/cli-plugin-template");
  const cwd = process.cwd();
  try {
    const registry = JSON.parse(readFileSync(join(dir, "registry.json"), "utf8")) as Array<{ local_path?: string }>;
    return registry.some((e) => {
      const lp = (e.local_path ?? "").replace(/\/+$/, "");
      return lp !== "" && (cwd === lp || cwd.startsWith(lp + "/"));
    });
  } catch {
    return false;
  }
}

export function intentNudge(firstMessageText: string): string | null {
  if (!INTENT_RE.test(stripAccents(firstMessageText))) return null;
  if (existsSync(".catalog-root")) return null;
  if (!registeredCwd()) return null;
  return "Intención de desarrollo de plugin detectada — usá la skill router plugin-dev.";
}
