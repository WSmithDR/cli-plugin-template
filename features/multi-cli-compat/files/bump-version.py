#!/usr/bin/env python3
"""bump-version.py — sincroniza la versión en TODOS los manifiestos + YAML.

Uso:
  python3 bump-version.py <major|minor|patch>
  python3 bump-version.py --set 1.2.3
  python3 bump-version.py --sync    # propaga plugin.json sin bumpear
  python3 bump-version.py --check   # detecta drift (exit 1 si hay)

Copiar de features/multi-cli-compat/files/bump-version.py.
Requiere PyYAML: pip3 install pyyaml
"""
import json, re, sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
ROOT = Path(__file__).resolve().parent
PLUGIN_REL = ".claude-plugin/plugin.json"
MARKETPLACE_REL = ".claude-plugin/marketplace.json"
CONFIG_YAML = "cli-config.yaml"
TOPLEVEL_MANIFESTS = [
    "gemini-extension.json",
    ".codex-plugin/plugin.json",
    ".cursor-plugin/plugin.json",
    ".copilot-plugin/plugin.json",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def bump(version: str, part: str) -> str:
    m = SEMVER.match(version)
    if not m:
        sys.exit(f"✗ version no semver: '{version}'")
    major, minor, patch = (int(x) for x in m.groups())
    if part == "major":
        major, minor, patch = major + 1, 0, 0
    elif part == "minor":
        minor, patch = minor + 1, 0
    elif part == "patch":
        patch += 1
    else:
        sys.exit(f"✗ bump inválido: '{part}' (major|minor|patch)")
    return f"{major}.{minor}.{patch}"


def _yaml_version(root: Path) -> str | None:
    p = root / CONFIG_YAML
    if not p.exists() or yaml is None:
        return None
    cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    return (cfg or {}).get("plugin", {}).get("version")


def _yaml_set_version(root: Path, new: str) -> bool:
    p = root / CONFIG_YAML
    if not p.exists() or yaml is None:
        return False
    cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not cfg:
        return False
    if cfg.setdefault("plugin", {}).get("version") == new:
        return False
    cfg["plugin"]["version"] = new
    p.write_text(yaml.dump(cfg, default_flow_style=False, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return True


def collect(root: Path) -> list[tuple[str, str | None]]:
    out: list[tuple[str, str | None]] = []
    for rel in [PLUGIN_REL, *TOPLEVEL_MANIFESTS]:
        p = root / rel
        if p.exists():
            out.append((rel, load(p).get("version")))
    mkt = root / MARKETPLACE_REL
    if mkt.exists():
        m = load(mkt)
        out.append((f"{MARKETPLACE_REL} (metadata)", (m.get("metadata") or {}).get("version")))
        for pl in m.get("plugins") or []:
            if isinstance(pl, dict):
                out.append((f"{MARKETPLACE_REL} ({pl.get('name')})", pl.get("version")))
    yv = _yaml_version(root)
    if yv is not None:
        out.append((CONFIG_YAML, yv))
    return out


def apply_version(root: Path, new: str) -> list[str]:
    touched: list[str] = []
    name = load(root / PLUGIN_REL).get("name") if (root / PLUGIN_REL).exists() else None
    for rel in [PLUGIN_REL, *TOPLEVEL_MANIFESTS]:
        p = root / rel
        if not p.exists():
            continue
        d = load(p)
        if d.get("version") != new:
            d["version"] = new
            dump(p, d)
            touched.append(rel)
    mkt = root / MARKETPLACE_REL
    if mkt.exists():
        m = load(mkt)
        changed = False
        if isinstance(m.get("metadata"), dict) and m["metadata"].get("version") != new:
            m["metadata"]["version"] = new
            changed = True
        plugins = m.get("plugins") or []
        matched = [p for p in plugins if isinstance(p, dict) and p.get("name") == name]
        for p in (matched or [p for p in plugins if isinstance(p, dict)]):
            if p.get("version") != new:
                p["version"] = new
                changed = True
        if changed:
            dump(mkt, m)
            touched.append(MARKETPLACE_REL)
    if _yaml_set_version(root, new):
        touched.append(CONFIG_YAML)
    return touched


def main(argv: list[str]) -> int:
    args = list(argv)
    root = ROOT
    if "--root" in args:
        i = args.index("--root")
        root = Path(args[i + 1]).resolve()
        del args[i:i + 2]

    plugin = root / PLUGIN_REL
    if not plugin.exists():
        sys.exit(f"✗ no existe {PLUGIN_REL} en {root}")
    canonical = load(plugin).get("version")

    if "--check" in args:
        items = collect(root)
        drift = [(rel, v) for rel, v in items if v != canonical]
        for rel, v in items:
            mark = "✓" if v == canonical else "✗"
            print(f"  {mark} {rel}: {v}")
        if drift:
            print(f"\n✗ drift: {len(drift)} manifiesto(s) ≠ plugin.json '{canonical}'")
            return 1
        print(f"\n✓ {len(items)} manifiestos sincronizados en {canonical}")
        return 0

    if "--set" in args:
        i = args.index("--set")
        target = args[i + 1]
        if not SEMVER.match(target):
            sys.exit(f"✗ --set requiere MAJOR.MINOR.PATCH, recibí '{target}'")
    elif "--sync" in args:
        target = canonical
    else:
        parts = [a for a in args if not a.startswith("--")]
        if len(parts) != 1:
            sys.exit("uso: bump-version.py <major|minor|patch> | --set X.Y.Z | --sync | --check")
        target = bump(canonical, parts[0])

    touched = apply_version(root, target)
    if not touched:
        print(f"✓ ya estaba todo en {target}, nada que hacer")
    else:
        print(f"✓ version → {target} (era {canonical})")
        for rel in touched:
            print(f"    actualizado {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
