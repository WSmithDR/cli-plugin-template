#!/usr/bin/env python3
"""Valida la integridad del catálogo de features.

Chequea, para cada features/<nombre>/:
  - existe meta.yml y README.md
  - meta.yml es YAML válido y tiene los campos requeridos
  - meta.yml.name coincide con el nombre de la carpeta
  - cada feature listado en CATALOG.md existe y viceversa
  - depends_on apunta a features que existen

Salida: exit 0 si todo OK, exit 1 con la lista de errores.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEATURES = ROOT / "features"
CATALOG = ROOT / "CATALOG.md"
REQUIRED_META = {"name", "version", "cli_compat", "depends_on", "description"}

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
ALLOWED_CLI = {"claude-code", "opencode", "gemini-cli", "codex", "cursor",
               "copilot", "lsp", "any"}
# Secciones que CONTRIBUTING.md exige en cada README de feature.
REQUIRED_SECTIONS = ("Qué hace", "Por qué", "Integración", "Tests")

# Manifiestos del plugin que llevan una versión top-level: todos deben coincidir
# con plugin.json (single source of truth). marketplace.json se chequea aparte
# porque su versión está anidada.
VERSIONED_MANIFESTS = [
    ".claude-plugin/plugin.json",
    "gemini-extension.json",
    ".codex-plugin/plugin.json",
    ".cursor-plugin/plugin.json",
    ".copilot-plugin/plugin.json",
]

errors: list[str] = []


def load_yaml(path: Path) -> dict:
    """Parser mínimo: usa PyYAML si está, si no un fallback para este schema plano."""
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text) or {}
    except ImportError:
        return _fallback_parse(text)


def _fallback_parse(text: str) -> dict:
    """Parsea el subset de YAML que usan los meta.yml (claves de primer nivel)."""
    data: dict = {}
    key = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith(" ") or raw.startswith("-"):
            continue  # bloques anidados / listas: basta con saber que la clave existe
        m = re.match(r"^([a-zA-Z_]+):\s*(.*)$", raw)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val.startswith("[") and val.endswith("]"):
                data[key] = [x.strip() for x in val[1:-1].split(",") if x.strip()]
            elif val and val != ">":
                data[key] = val
            else:
                data[key] = ""
    return data


def feature_dirs() -> list[Path]:
    return sorted(p for p in FEATURES.iterdir() if p.is_dir())


def check_readme_sections(name: str, readme: Path) -> None:
    """Cada README debe tener las secciones que exige CONTRIBUTING.md."""
    text = readme.read_text(encoding="utf-8")
    headings = set(re.findall(r"^##\s+(.+?)\s*$", text, re.MULTILINE))
    for sec in REQUIRED_SECTIONS:
        if not any(h.lower().startswith(sec.lower()) for h in headings):
            errors.append(f"{name}: README sin sección '## {sec}'")


def load_json(path: Path) -> dict:
    import json
    return json.loads(path.read_text(encoding="utf-8"))


def check_manifest_versions() -> None:
    """Single source of truth: toda versión declarada en los manifiestos del
    plugin debe coincidir con la de .claude-plugin/plugin.json. Evita el drift
    silencioso (marketplace atrasado → `/plugin install` saltea el update)."""
    plugin_json = ROOT / ".claude-plugin/plugin.json"
    if not plugin_json.exists():
        return  # el catálogo puede usarse sin ser un plugin instalable
    canonical = load_json(plugin_json).get("version")
    if not canonical or not SEMVER.match(str(canonical)):
        errors.append(f".claude-plugin/plugin.json: version inválida '{canonical}'")
        return

    for rel in VERSIONED_MANIFESTS:
        path = ROOT / rel
        if not path.exists():
            continue
        v = load_json(path).get("version")
        if v is not None and v != canonical:
            errors.append(f"{rel}: version '{v}' ≠ plugin.json '{canonical}' (desync)")

    mkt = ROOT / ".claude-plugin/marketplace.json"
    if mkt.exists():
        m = load_json(mkt)
        meta_v = (m.get("metadata") or {}).get("version")
        if meta_v is not None and meta_v != canonical:
            errors.append(f"marketplace.json: metadata.version '{meta_v}' ≠ plugin.json '{canonical}'")
        for p in m.get("plugins") or []:
            pv = p.get("version") if isinstance(p, dict) else None
            if pv is not None and pv != canonical:
                errors.append(f"marketplace.json: plugin '{p.get('name')}' version '{pv}' ≠ plugin.json '{canonical}'")


def main() -> int:
    names = set()
    for d in feature_dirs():
        names.add(d.name)
        meta_path = d / "meta.yml"
        readme = d / "README.md"
        if not readme.exists():
            errors.append(f"{d.name}: falta README.md")
        if not meta_path.exists():
            errors.append(f"{d.name}: falta meta.yml")
            continue
        if readme.exists():
            check_readme_sections(d.name, readme)
        meta = load_yaml(meta_path)
        missing = REQUIRED_META - set(meta)
        if missing:
            errors.append(f"{d.name}: meta.yml sin campos {sorted(missing)}")
        if meta.get("name") and meta["name"] != d.name:
            errors.append(f"{d.name}: meta.name='{meta['name']}' no coincide con la carpeta")
        version = meta.get("version")
        if version and not SEMVER.match(str(version)):
            errors.append(f"{d.name}: version '{version}' no es semver (MAJOR.MINOR.PATCH)")
        for cli in meta.get("cli_compat") or []:
            if cli not in ALLOWED_CLI:
                errors.append(f"{d.name}: cli_compat '{cli}' no permitido {sorted(ALLOWED_CLI)}")

    # depends_on apunta a features existentes
    for d in feature_dirs():
        meta = load_yaml(d / "meta.yml") if (d / "meta.yml").exists() else {}
        for dep in meta.get("depends_on") or []:
            if dep not in names:
                errors.append(f"{d.name}: depends_on '{dep}' no existe")

    # CATALOG.md ↔ features/ coherentes
    catalog_text = CATALOG.read_text(encoding="utf-8") if CATALOG.exists() else ""
    linked = set(re.findall(r"features/([a-z0-9-]+)/README\.md", catalog_text))
    for name in names - linked:
        errors.append(f"{name}: existe en features/ pero no está en CATALOG.md")
    for name in linked - names:
        errors.append(f"{name}: linkeado en CATALOG.md pero no existe en features/")

    # Sincronía de versión entre todos los manifiestos del plugin
    check_manifest_versions()

    if errors:
        print("✗ Catálogo inválido:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"✓ Catálogo válido — {len(names)} features verificados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
