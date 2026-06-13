#!/usr/bin/env python3
"""
generate-cli-configs.py — Lee cli-config.yaml y regenera:
  .mcp.json          (Claude Code)
  opencode.json      (OpenCode)
  gemini-extension.json (Gemini CLI)

Uso: python3 bin/dev/generate-cli-configs.py
Ejecutar tras editar cli-config.yaml.
"""

import json
import os
import sys

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML requerido — pip3 install pyyaml")
    sys.exit(1)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_FILE = os.path.join(REPO_ROOT, "cli-config.yaml")


def _resolve_path(p: str) -> str:
    if p.startswith("~/"):
        return os.path.expanduser(p)
    return p


def _home_to_env_var(p: str) -> str:
    if p.startswith("~/"):
        return "{env:HOME}/" + p[2:]
    return p


def generate_mcp_json(cfg: dict) -> dict:
    servers = {}
    for name, srv in cfg.get("mcp_servers", {}).items():
        entry = {"command": srv["command"], "args": [_resolve_path(a) for a in srv.get("args", [])]}
        if srv.get("env"):
            entry["env"] = srv["env"]
        servers[name] = entry
    return {"mcpServers": servers}


def generate_opencode_json(cfg: dict) -> dict:
    doc = {
        "$schema": "https://opencode.ai/config.json",
        "mcp": {},
        "skills": {"paths": cfg.get("opencode", {}).get("skills", {}).get("paths", [])},
    }
    if cfg.get("opencode", {}).get("plugins"):
        doc["plugin"] = cfg["opencode"]["plugins"]
    for name, srv in cfg.get("mcp_servers", {}).items():
        cmd_parts = [srv["command"]] + [_home_to_env_var(a) for a in srv.get("args", [])]
        entry = {"type": "local", "command": cmd_parts}
        if srv.get("env"):
            entry["environment"] = srv["env"]
        doc["mcp"][name] = entry
    return doc


def generate_gemini_json(cfg: dict) -> dict:
    gem = cfg.get("gemini_extension", {})
    pinfo = cfg.get("plugin", {})
    return {
        "name": gem.get("name", pinfo.get("name", "unknown")),
        "description": gem.get("description", ""),
        "version": pinfo.get("version", "0.0.0"),
        "contextFileName": gem.get("contextFileName", "GEMINI.md"),
    }


def main():
    if not os.path.exists(CONFIG_FILE):
        print(f"ERROR: no se encuentra {CONFIG_FILE}")
        sys.exit(1)

    with open(CONFIG_FILE) as f:
        cfg = yaml.safe_load(f)

    outputs = {
        ".mcp.json": generate_mcp_json(cfg),
        "opencode.json": generate_opencode_json(cfg),
        "gemini-extension.json": generate_gemini_json(cfg),
    }

    for filename, data in outputs.items():
        path = os.path.join(REPO_ROOT, filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        print(f"✓ {filename}")

    print("\nListo. 3 archivos regenerados.")


if __name__ == "__main__":
    main()
