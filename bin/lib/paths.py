"""Resolución centralizada de rutas del store externo del meta-plugin.

Único lugar que conoce dónde viven los datos de evolución de plugins.
Ninguna skill arma paths a mano: todo path sale de acá.

El store es plugin-aware: cada plugin administrado tiene su propio subdir
(`<data_dir>/<plugin>/`), y el registry (`registry.json`) es el allowlist.
"""
import os
import re
from pathlib import Path

# Nombre del store (no es el nombre de un plugin administrado, es el del meta-plugin)
STORE_NAME = "cli-plugin-template"
# Override explícito del data dir (tests, instalaciones no estándar)
DATA_ENV = "CLI_PLUGIN_TEMPLATE_DATA_DIR"


def data_dir() -> Path:
    """Raíz del store externo. Resolución: env override > XDG_DATA_HOME > ~/.local/share.

    No crea el directorio en import ni al resolver: la creación es on-write
    (ver gateway._ensure_dir). Los listados guardan con .exists().
    """
    override = os.environ.get(DATA_ENV)
    if override:
        return Path(override).expanduser()
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return Path(base) / STORE_NAME


def registry_file() -> Path:
    return data_dir() / "registry.json"


def plugin_dir(plugin: str) -> Path:
    return data_dir() / slugify(plugin)


def feedbacks_dir(plugin: str) -> Path:
    return plugin_dir(plugin) / "feedbacks"


def proposals_dir(plugin: str) -> Path:
    # Reservado para P2 (gate de aprobación + hotpatch).
    return plugin_dir(plugin) / "proposals"


def session_id_file() -> Path:
    return data_dir() / "current-session.id"


def harvest_offsets_file() -> Path:
    """Offsets por transcript para la detección idempotente de fricción (Stop hook)."""
    return data_dir() / "harvest-offsets.json"


def slugify(text: str) -> str:
    """Slug estable y filesystem-safe: lowercase, no-alnum→'-', colapsa, trunc 40."""
    s = re.sub(r"[^a-z0-9]+", "-", text.strip().lower())
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:40].strip("-")
