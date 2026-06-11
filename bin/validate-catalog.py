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
        meta = load_yaml(meta_path)
        missing = REQUIRED_META - set(meta)
        if missing:
            errors.append(f"{d.name}: meta.yml sin campos {sorted(missing)}")
        if meta.get("name") and meta["name"] != d.name:
            errors.append(f"{d.name}: meta.name='{meta['name']}' no coincide con la carpeta")

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

    if errors:
        print("✗ Catálogo inválido:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"✓ Catálogo válido — {len(names)} features verificados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
