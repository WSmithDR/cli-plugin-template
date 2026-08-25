// Espejo TS de bin/hooks/catalog-guard.py: mismas 2 reglas, un solo lugar por regla.
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";

const FEATURES_RE = /(^|\/)features\/([^/]+)\//;
const FENCE = /```(\w+)[^\n]*\n([\s\S]*?)```/g;
const SCRIPT_LANGS = new Set(["bash", "sh", "python", "python3", "node", "ts", "typescript", "js", "javascript"]);
const SENTINEL = ".catalog-root";

/** True si el feature vive dentro del repo del catálogo, que se identifica con el
 *  sentinel .catalog-root en su raíz (mismo criterio que paths.ts, session-start.sh
 *  e intent-nudge.py). Sin sentinel en ningún ancestro, el `features/<x>/` es de otro
 *  proyecto (p. ej. src/features/ de una app Next.js) y la regla 1 no corresponde. */
function enElCatalogo(featRoot: string): boolean {
  let dir = featRoot;
  for (;;) {
    if (existsSync(join(dir, SENTINEL))) return true;
    const padre = dirname(dir);
    if (padre === dir) return false;
    dir = padre;
  }
}

export function violations(filePath: string, content: string): string[] {
  const out: string[] = [];
  const norm = filePath.replace(/\\/g, "/");
  const segs = norm.split("/").filter(Boolean);
  const base = segs[segs.length - 1] ?? "";
  const m = FEATURES_RE.exec(norm);
  if (m && base !== "meta.yml") {
    // paridad con el .py: busca el ancestro llamado <feature> (p. ej. features/<n>/files/x.md),
    // no solo dirname() — si no, falsos positivos para archivos anidados.
    const idx = segs.lastIndexOf(m[2]);
    // paridad con el .py: la normalización (split + filter) pierde la "/" inicial
    // de rutas absolutas — sin re-prefijarla, existsSync resuelve relativo a cwd
    // y bloquea features que SÍ tienen meta.yml.
    const featRoot = (norm.startsWith("/") ? "/" : "") + segs.slice(0, idx + 1).join("/");
    if (idx >= 0 && enElCatalogo(featRoot) && !existsSync(join(featRoot, "meta.yml"))) {
      out.push(`features/${m[2]}/ no tiene meta.yml — crealo junto al resto del feature`);
    }
  }
  if (base === "SKILL.md" && norm.includes("/skills/")) {
    for (const [, lang, body] of (content || "").matchAll(FENCE)) {
      const lineas = body.split("\n").filter((l) => l.trim()).length;
      if (SCRIPT_LANGS.has(lang.toLowerCase()) && lineas > 2) {
        out.push(`SKILL.md embebe un bloque \`\`\`${lang} de más de 2 líneas — va a scripts/`);
        break;
      }
    }
  }
  return out;
}
