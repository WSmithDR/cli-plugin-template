// Hook `experimental.chat.messages.transform`: inyecta el bootstrap/sugerencias
// en el PRIMER mensaje de usuario (no system: evita token bloat por turno y
// modelos que rechazan múltiples system messages), con guard anti doble
// inyección — el hook dispara en cada step del agente.
//   repo propio    → bootstrap (AGENTS.md)
//   cualquier repo → stdout de bin/hooks/session-start.sh (auditoría/registry)

import { isInOwnRepo } from "../../lib/paths.ts";
import { BOOTSTRAP_MARKER, getBootstrap } from "../../lib/bootstrap.ts";
import { getSessionStartMessage } from "./session-start.ts";

type TextPart = { type: string; text?: string };
type UserMessage = { info?: { role?: string }; parts?: TextPart[] };

export async function injectBootstrap(
  _input: unknown,
  output: { messages?: UserMessage[] },
): Promise<void> {
  const firstUser: UserMessage | undefined = output?.messages?.find(
    (m) => m?.info?.role === "user",
  );
  if (!firstUser?.parts?.length) return;

  const injections: string[] = [];
  if (isInOwnRepo()) injections.push(getBootstrap());
  const sessionStart = getSessionStartMessage();
  if (sessionStart && !injections.includes(sessionStart)) injections.push(sessionStart);
  if (!injections.length) return;
  if (firstUser.parts.some((p) => p.type === "text" && p.text?.includes(BOOTSTRAP_MARKER))) {
    return;
  }

  const ref = firstUser.parts[0];
  firstUser.parts.unshift(...injections.map((text) => ({ ...ref, type: "text", text })));
}
