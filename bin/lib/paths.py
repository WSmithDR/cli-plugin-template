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


# Scope de los aprendizajes que no son de un plugin en particular: convenciones de
# estilo e integración de CLIs valen para CUALQUIER plugin del taller, y guardarlas
# dentro de uno las volvería invisibles al editar otro. No se slugifica (el guión bajo
# lo perdería) y por eso tampoco puede chocar con el subdir de un plugin real.
GLOBAL_SCOPE = "_global"


def learnings_dir(scope: str) -> Path:
    """Aprendizajes vivos de un plugin, o del taller si scope es GLOBAL_SCOPE.

    A diferencia de los feedbacks —que nacen pending y mueren aplicados o descartados—,
    un aprendizaje es conocimiento vigente: se corrige o se borra, no se cierra.
    """
    if scope == GLOBAL_SCOPE:
        return data_dir() / GLOBAL_SCOPE / "learnings"
    return plugin_dir(scope) / "learnings"


def session_id_file() -> Path:
    return data_dir() / "current-session.id"


def harvest_offsets_file() -> Path:
    """Offsets por transcript para la detección idempotente de fricción (Stop hook)."""
    return data_dir() / "harvest-offsets.json"


def friction_lexicon_file() -> Path:
    """Léxico auto-creciente de frases de fricción que consume el Stop hook."""
    return data_dir() / "friction-lexicon.json"


def slugify(text: str) -> str:
    """Slug estable y filesystem-safe: lowercase, no-alnum→'-', colapsa, trunc 40."""
    s = re.sub(r"[^a-z0-9]+", "-", text.strip().lower())
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:40].strip("-")
