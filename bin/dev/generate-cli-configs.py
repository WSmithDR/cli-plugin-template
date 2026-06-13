#!/usr/bin/env python3
"""
generate-cli-configs.py — Lee cli-config.yaml y regenera TODOS los manifiestos
multi-CLI del plugin.

Uso: python3 bin/dev/generate-cli-configs.py
     python3 bin/dev/generate-cli-configs.py --check   # dry-run, solo diff

Fuente única: cli-config.yaml en la raíz.
Editar ese archivo, correr este script, commitear.

Genera (si existen en el YAML):
  .claude-plugin/plugin.json
  .claude-plugin/marketplace.json
  .codex-plugin/plugin.json
  .copilot-plugin/plugin.json
  .cursor-plugin/plugin.json
  gemini-extension.json
  opencode.json
"""

import json
import os
import subprocess
import sys

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML requerido — pip3 install pyyaml")
    sys.exit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_FILE = os.path.join(ROOT, "cli-config.yaml")


def _load_cfg() -> dict:
    if not os.path.exists(CONFIG_FILE):
        print(f"ERROR: no se encuentra {CONFIG_FILE}")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


def _write(path: str, data: dict, *, check: bool = False) -> bool:
    """Escribe `data` como JSON en `path`. Retorna True si hubo cambios."""
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if check:
        if os.path.exists(path):
            existing = open(path).read()
            if existing == content:
                return False
            print(f"  ✗ {path} — desactualizado")
            return True
        print(f"  ✗ {path} — no existe")
        return True
    with open(path, "w") as f:
        f.write(content)
    print(f"  ✓ {path}")
    return True


def _resolve_home(p: str) -> str:
    return os.path.expanduser(p) if p.startswith("~/") else p


def _home_to_env(p: str) -> str:
    return ("{env:HOME}/" + p[2:]) if p.startswith("~/") else p


# ── Generadores por manifest ──────────────────────────────────────────────


def gen_claude_plugin_json(cfg: dict) -> tuple[str, dict] | None:
    p = cfg.get("plugin")
    if not p:
        return None
    doc = {
        "name": p["name"],
        "version": p["version"],
        "description": p.get("description", "").strip(),
    }
    for k in ("author", "repository", "license", "keywords", "skills"):
        if p.get(k):
            doc[k] = p[k]
    return (".claude-plugin/plugin.json", doc)


def gen_marketplace_json(cfg: dict) -> tuple[str, dict] | None:
    p = cfg.get("plugin")
    m = cfg.get("marketplace")
    if not p or not m:
        return None
    owner = m.get("owner", {})
    metadata = m.get("metadata", {})
    plugins_in = m.get("plugins", [])
    plugins_out = []
    for pl in plugins_in:
        entry = {
            "name": p["name"],
            "source": pl.get("source", "./"),
            "description": p.get("description", "").strip(),
            "version": p["version"],
        }
        if pl.get("author"):
            entry["author"] = pl["author"]
        if pl.get("category"):
            entry["category"] = pl["category"]
        if p.get("keywords"):
            entry["keywords"] = p["keywords"]
        plugins_out.append(entry)
    doc = {
        "name": p["name"],
        "owner": owner,
        "metadata": {
            "description": metadata.get("description", "").strip(),
            "version": p["version"],
        },
        "plugins": plugins_out,
    }
    return (".claude-plugin/marketplace.json", doc)


def gen_codex_json(cfg: dict) -> tuple[str, dict] | None:
    p = cfg.get("plugin")
    if not p:
        return None
    doc = {
        "name": p["name"],
        "description": p.get("description", "").strip(),
        "version": p["version"],
        "skills": p.get("skills", "./skills/"),
    }
    return (".codex-plugin/plugin.json", doc)


def gen_copilot_json(cfg: dict) -> tuple[str, dict] | None:
    p = cfg.get("plugin")
    if not p:
        return None
    doc = {
        "name": p["name"],
        "displayName": p["name"],
        "description": p.get("description", "").strip(),
        "version": p["version"],
        "skills": p.get("skills", "./skills/"),
    }
    return (".copilot-plugin/plugin.json", doc)


def gen_cursor_json(cfg: dict) -> tuple[str, dict] | None:
    p = cfg.get("plugin")
    if not p:
        return None
    doc = {
        "name": p["name"],
        "displayName": p["name"],
        "description": p.get("description", "").strip(),
        "version": p["version"],
        "skills": p.get("skills", "./skills/"),
    }
    return (".cursor-plugin/plugin.json", doc)


def gen_gemini_json(cfg: dict) -> tuple[str, dict] | None:
    gem = cfg.get("gemini_extension")
    p = cfg.get("plugin", {})
    if not gem:
        return None
    doc = {
        "name": gem.get("name", p.get("name", "unknown")),
        "version": p.get("version", "0.0.0"),
        "description": (gem.get("description") or p.get("description", "")).strip(),
        "contextFileName": gem.get("contextFileName", "GEMINI.md"),
    }
    return ("gemini-extension.json", doc)


def gen_opencode_json(cfg: dict) -> tuple[str, dict] | None:
    oc = cfg.get("opencode")
    p = cfg.get("plugin", {})
    if not oc:
        return None
    doc = {
        "$schema": "https://opencode.ai/config.json",
        "skills": oc.get("skills", {}).get("paths", [f"{p.get('skills', './skills/')}"]),
    }
    if oc.get("plugins"):
        doc["plugin"] = oc["plugins"]
    return ("opencode.json", doc)


GENERATORS = [
    gen_claude_plugin_json,
    gen_marketplace_json,
    gen_codex_json,
    gen_copilot_json,
    gen_cursor_json,
    gen_gemini_json,
    gen_opencode_json,
]


# ── CLI ──────────────────────────────────────────────────────────────────


def main():
    check = "--check" in sys.argv

    cfg = _load_cfg()
    changed = 0
    total = 0

    for gen in GENERATORS:
        result = gen(cfg)
        if result is None:
            continue
        rel, data = result
        total += 1
        if _write(os.path.join(ROOT, rel), data, check=check):
            changed += 1

    if check:
        if changed:
            print(f"\n✗ {changed}/{total} manifiestos desactualizados — corré generate-cli-configs.py")
            sys.exit(1)
        print(f"\n✓ {total} manifiestos actualizados")
        return

    print(f"\nListo. {total} manifiestos regenerados.")


if __name__ == "__main__":
    main()
