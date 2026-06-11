"""Resolución centralizada de rutas. Único lugar que conoce dónde viven los datos.

Ninguna skill arma paths a mano: todo path sale de acá.
"""
import hashlib
import os
from pathlib import Path

# Nombre del plugin — ajustar
PLUGIN_NAME = "<plugin>"


def data_dir() -> Path:
    """Directorio raíz de datos del plugin (XDG por defecto)."""
    base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    d = Path(base) / PLUGIN_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def entity_dir(entity: str) -> Path:
    """Directorio de una entidad (ej. proposals, feedback, curricula)."""
    d = data_dir() / entity
    d.mkdir(parents=True, exist_ok=True)
    return d


def project_hash(repo_root: str) -> str:
    """Hash estable de un proyecto para namespacing de datos."""
    return hashlib.sha1(os.path.abspath(repo_root).encode()).hexdigest()[:12]
