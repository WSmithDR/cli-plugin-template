// Plugin de OpenCode para cli-plugin-template. Entry point: solo compone los
// hooks (convención ankify — cada hook en .opencode/hooks/<nombre>/).
// Mapeo OpenCode ↔ Claude Code (detalle en
// skills/plugin-dev/references/tool-mapping.md):
//   skills + agentes → config
//   SessionStart     → experimental.chat.messages.transform
//   Stop             → event global.disposed

import type { Plugin } from "@opencode-ai/plugin";
import { injectConfig } from "../hooks/config-inject";
import { injectBootstrap } from "../hooks/bootstrap-inject";
import { onStop } from "../hooks/stop-event";
import { afterHook, beforeHook } from "../hooks/tool-guard/index.ts";

export default (async () => {
  return {
    config: injectConfig,
    "experimental.chat.messages.transform": injectBootstrap,
    event: onStop,
    "tool.execute.before": beforeHook,
    "tool.execute.after": afterHook,
  };
}) satisfies Plugin;
