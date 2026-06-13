#!/usr/bin/env bash
# install-opencode.sh — Registra cli-plugin-template como plugin global de OpenCode.
#
# Uso: bash bin/install-opencode.sh [--uninstall]

set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OC_CONFIG="${HOME}/.config/opencode/opencode.json"
PLUGIN_REL=".opencode/plugins/cli-plugin-template.js"

if [ ! -f "$OC_CONFIG" ]; then
  echo "✗ No existe $OC_CONFIG — OpenCode no está configurado"
  exit 1
fi

python3 - "$OC_CONFIG" "$PLUGIN_ROOT" "$PLUGIN_REL" "${1:-}" <<'PYEOF'
import json, os, sys

cfg_path, root, plugin_rel, action = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
plugin_abs = os.path.join(root, plugin_rel)
skills_abs = os.path.join(root, "skills")

with open(cfg_path) as f:
    cfg = json.load(f)

changed = False
is_uninstall = (action == "--uninstall")

# Plugin JS entry
plugs = cfg.setdefault("plugin", [])
if is_uninstall:
    if plugin_abs in plugs:
        cfg["plugin"] = [p for p in plugs if p != plugin_abs]
        changed = True
        print(f"  ✓ plugin removido: {plugin_abs}")
    else:
        print(f"  - plugin no estaba registrado")
else:
    if plugin_abs not in plugs:
        plugs.append(plugin_abs)
        changed = True
        print(f"  ✓ plugin registrado: {plugin_abs}")
    else:
        print(f"  - plugin ya registrado")

# Skills paths
skills = cfg.setdefault("skills", [])
if is_uninstall:
    if skills_abs in skills:
        cfg["skills"] = [s for s in skills if s != skills_abs]
        changed = True
        print(f"  ✓ skills removidas: {skills_abs}")
    else:
        print(f"  - skills no estaban registradas")
else:
    if skills_abs not in skills:
        skills.append(skills_abs)
        changed = True
        print(f"  ✓ skills agregadas: {skills_abs}")
    else:
        print(f"  - skills ya registradas")

if changed:
    with open(cfg_path, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    os.chmod(cfg_path, 0o644)
    print(f"\n✓ {cfg_path} actualizado")
else:
    print(f"\n✓ Todo ya estaba en su estado final")
PYEOF
