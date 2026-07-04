// Bootstrap inyectado en el primer mensaje de usuario cuando el CWD es el
// propio repo del catálogo. Cacheado a nivel módulo: el hook de transform
// dispara en cada step del agente y no debe repetir trabajo de disco
// (mismo patrón que superpowers, ver su issue #1202).

import { readFileSync } from "node:fs";
import { AGENTS_MD } from "./paths.js";

// Marcador estable para el guard anti doble inyección del transform.
export const BOOTSTRAP_MARKER = "## cli-plugin-template — bootstrap (OpenCode)";

let cache; // undefined = no cargado todavía

export function getBootstrap() {
  if (cache !== undefined) return cache;
  let agents = "";
  try {
    agents = readFileSync(AGENTS_MD, "utf8");
  } catch {
    agents = "";
  }
  cache = [
    BOOTSTRAP_MARKER,
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
  return cache;
}
