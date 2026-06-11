"""Gateway de persistencia. Único punto de contacto con el almacenamiento.

Cambiar el backend (FS → SQLite → API) se hace acá, sin tocar ninguna skill.
Las skills invocan a través del CLI unificado: `bin/<plugin> data <entity> <op>`.
"""
import json
from pathlib import Path

import paths


def save(entity: str, key: str, content: str) -> str:
    """Guarda contenido bajo una entidad/clave. Devuelve la ruta escrita."""
    dest = paths.entity_dir(entity) / f"{key}.md"
    dest.write_text(content, encoding="utf-8")
    return str(dest)


def load(entity: str, key: str) -> str | None:
    src = paths.entity_dir(entity) / f"{key}.md"
    return src.read_text(encoding="utf-8") if src.exists() else None


def list_keys(entity: str) -> list[str]:
    return sorted(p.stem for p in paths.entity_dir(entity).glob("*.md"))


def delete(entity: str, key: str) -> bool:
    target = paths.entity_dir(entity) / f"{key}.md"
    if target.exists():
        target.unlink()
        return True
    return False


def save_json(entity: str, key: str, obj: dict) -> str:
    """Escritura atómica de JSON (indent=2)."""
    dest = paths.entity_dir(entity) / f"{key}.json"
    dest.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(dest)
