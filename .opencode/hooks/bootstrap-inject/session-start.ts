// Gap de paridad con Claude Code: su SessionStart corre session-start.sh en
// CUALQUIER proyecto donde el plugin está instalado (sugiere auditoría una vez
// por proyecto con re-arme por versión del catálogo, ofrece multi-cli-compat y
// alta en registry). El script trae sus propios guards (sentinel .catalog-root,
// marcador en .git); acá solo lo ejecutamos una vez por proceso e inyectamos el
// stdout si no es vacío.

import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { BOOTSTRAP_MARKER } from "../../lib/bootstrap.ts";
import { SESSION_START_SH } from "../../lib/paths.ts";

let cache: string | undefined;

export function getSessionStartMessage(): string {
  if (cache !== undefined) return cache;
  try {
    if (!existsSync(SESSION_START_SH)) return (cache = "");
    const out = execFileSync("bash", [SESSION_START_SH], {
      encoding: "utf8",
      timeout: 10000,
    }).trim();
    // El transform es stateless entre steps: mismo marcador que el bootstrap
    // para que un solo guard evite re-inyección.
    return (cache = out ? `${BOOTSTRAP_MARKER}\n\n${out}` : "");
  } catch {
    return (cache = "");
  }
}
