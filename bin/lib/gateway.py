"""Gateway de persistencia del meta-plugin. Único punto de contacto con el store.

Cambiar el backend (FS → SQLite → API) se hace acá, sin tocar ninguna skill.
Las skills invocan a través del CLI unificado: `bin/cpt registry|feedback ...`.

Dos dominios:
  - registry: allowlist de plugins propios (baranda 1) + sus skill namespaces.
  - feedback: capturas de fricción por plugin (`<plugin>/feedbacks/feedback_<slug>.md`).
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import paths


# ── helpers ──────────────────────────────────────────────────

def _ensure_dir(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)


def _read(path: Path, default: str = "") -> str:
    return path.read_text(encoding="utf-8") if path.exists() else default


def _write(path: Path, content: str) -> None:
    _ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def _read_json(path: Path, default: Any = None) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default
    return default


def _write_json(path: Path, data: Any) -> None:
    _ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ── registry (allowlist) ─────────────────────────────────────

def registry_load() -> list[dict]:
    return _read_json(paths.registry_file(), []) or []


def registry_get(name: str) -> Optional[dict]:
    slug = paths.slugify(name)
    for entry in registry_load():
        if entry.get("name") == slug:
            return entry
    return None


def registry_register(name: str, local_path: str, remote: str = "",
                      manifest: str = ".claude-plugin/plugin.json",
                      skill_namespaces: Optional[list[str]] = None) -> dict:
    """Alta idempotente por `name`. Si ya existe, actualiza local_path/remote/
    manifest/skill_namespaces (p.ej. repo movido) y conserva `registered_at`."""
    slug = paths.slugify(name)
    namespaces = skill_namespaces or [slug]
    data = registry_load()
    for entry in data:
        if entry.get("name") == slug:
            entry.update({
                "local_path": local_path,
                "remote": remote,
                "manifest": manifest,
                "skill_namespaces": namespaces,
            })
            _write_json(paths.registry_file(), data)
            return entry
    entry = {
        "name": slug,
        "local_path": local_path,
        "remote": remote,
        "manifest": manifest,
        "skill_namespaces": namespaces,
        "registered_at": _today(),
    }
    data.append(entry)
    _write_json(paths.registry_file(), data)
    return entry


def registry_list() -> list[dict]:
    return registry_load()


def registry_resolve_namespace(skill_namespace: str) -> Optional[str]:
    """Mapea un skill namespace ('ankify:anki-capture' o 'ankify') al `name` de
    un plugin registrado. Devuelve None si no está en el allowlist."""
    prefix = skill_namespace.split(":", 1)[0].strip()
    if not prefix:
        return None
    for entry in registry_load():
        if prefix in entry.get("skill_namespaces", []):
            return entry["name"]
    return None


# ── feedback (captura de fricción por plugin) ────────────────

def feedback_save(plugin: str, slug: str, content: str) -> str:
    """Guarda un feedback bajo el plugin. Devuelve la ruta escrita."""
    path = paths.feedbacks_dir(plugin) / f"feedback_{paths.slugify(slug)}.md"
    _write(path, content)
    return str(path)


def feedback_load(plugin: str, slug: str) -> str:
    path = paths.feedbacks_dir(plugin) / f"feedback_{paths.slugify(slug)}.md"
    return _read(path)


def _strip_prefix(stem: str) -> str:
    return stem[len("feedback_"):] if stem.startswith("feedback_") else stem


def _is_pending(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    m = re.search(r"^applied:\s*(\S+)", content, re.MULTILINE)
    return m is None or m.group(1) == "false"


def feedback_list(plugin: Optional[str] = None, pending_only: bool = False) -> list[str]:
    """Lista feedbacks como '<plugin>/<slug>'. plugin=None → todos los registrados
    + cualquier subdir con feedbacks. pending_only filtra applied:false."""
    if plugin is not None:
        plugins = [paths.slugify(plugin)]
    else:
        plugins = sorted({e["name"] for e in registry_load()})
        # Incluir subdirs presentes en disco aunque no estén en el registry.
        root = paths.data_dir()
        if root.exists():
            for child in root.iterdir():
                if child.is_dir() and (child / "feedbacks").is_dir():
                    plugins.append(child.name)
        plugins = sorted(set(plugins))

    result: list[str] = []
    for p in plugins:
        d = paths.feedbacks_dir(p)
        if not d.exists():
            continue
        for f in sorted(d.glob("feedback_*.md")):
            if pending_only and not _is_pending(f):
                continue
            result.append(f"{p}/{_strip_prefix(f.stem)}")
    return result


def feedback_mark_applied(plugin: str, slug: str, applied_at: Optional[str] = None) -> str:
    """Marca un feedback como aplicado: applied:false→true y agrega/actualiza applied_at.
    Devuelve la ruta. Idempotente."""
    path = paths.feedbacks_dir(plugin) / f"feedback_{paths.slugify(slug)}.md"
    content = _read(path)
    if not content:
        raise FileNotFoundError(f"feedback no existe: {plugin}/{slug}")
    stamp = applied_at or _today()
    if re.search(r"^applied:", content, re.MULTILINE):
        content = re.sub(r"^applied:.*$", "applied: true", content, count=1, flags=re.MULTILINE)
    if re.search(r"^applied_at:", content, re.MULTILINE):
        content = re.sub(r"^applied_at:.*$", f"applied_at: {stamp}", content, count=1, flags=re.MULTILINE)
    else:
        content = re.sub(r"^applied: true$", f"applied: true\napplied_at: {stamp}",
                         content, count=1, flags=re.MULTILINE)
    _write(path, content)
    return str(path)


# ── proposals (gate de aprobación, baranda 2) ────────────────

def proposal_save(plugin: str, slug: str, content: str) -> str:
    path = paths.proposals_dir(plugin) / f"{paths.slugify(slug)}.md"
    _write(path, content)
    return str(path)


def proposal_load(plugin: str, slug: str) -> str:
    path = paths.proposals_dir(plugin) / f"{paths.slugify(slug)}.md"
    return _read(path)


def _status_of(path: Path) -> str:
    m = re.search(r"^status:\s*(\S+)", path.read_text(encoding="utf-8"), re.MULTILINE)
    return m.group(1) if m else ""


def proposal_list(plugin: Optional[str] = None, status: Optional[str] = None) -> list[str]:
    """Lista propuestas como '<plugin>/<slug>'. status filtra por el frontmatter."""
    if plugin is not None:
        plugins = [paths.slugify(plugin)]
    else:
        plugins = sorted({e["name"] for e in registry_load()})
        root = paths.data_dir()
        if root.exists():
            for child in root.iterdir():
                if child.is_dir() and (child / "proposals").is_dir():
                    plugins.append(child.name)
        plugins = sorted(set(plugins))

    result: list[str] = []
    for p in plugins:
        d = paths.proposals_dir(p)
        if not d.exists():
            continue
        for f in sorted(d.glob("*.md")):
            if status is not None and _status_of(f) != status:
                continue
            result.append(f"{p}/{f.stem}")
    return result


def proposal_set_status(plugin: str, slug: str, status: str) -> str:
    """Actualiza el status del frontmatter de una propuesta. Devuelve la ruta."""
    path = paths.proposals_dir(plugin) / f"{paths.slugify(slug)}.md"
    content = _read(path)
    if not content:
        raise FileNotFoundError(f"propuesta no existe: {plugin}/{slug}")
    if re.search(r"^status:", content, re.MULTILINE):
        content = re.sub(r"^status:.*$", f"status: {status}", content, count=1, flags=re.MULTILINE)
    else:
        content = re.sub(r"^---\s*$", f"---\nstatus: {status}", content, count=1, flags=re.MULTILINE)
    _write(path, content)
    return str(path)


# ── growth dashboard (P4) ────────────────────────────────────

PROPOSAL_STATUSES = ("pending", "approved", "discarded")


def _known_plugins() -> list[str]:
    """Plugins registrados + cualquier subdir con datos (feedbacks/ o proposals/)."""
    names = {e["name"] for e in registry_load()}
    root = paths.data_dir()
    if root.exists():
        for child in root.iterdir():
            if child.is_dir() and ((child / "feedbacks").is_dir() or (child / "proposals").is_dir()):
                names.add(child.name)
    return sorted(names)


def growth_summary(plugin: Optional[str] = None) -> dict:
    """Estado de evolución agregado: por plugin, feedbacks (pendientes/aplicados) y
    propuestas por status. plugin=None → todos los conocidos."""
    plugins = [paths.slugify(plugin)] if plugin else _known_plugins()
    registered = {e["name"]: e for e in registry_load()}

    rows = []
    for p in plugins:
        fb_total = len(feedback_list(plugin=p))
        fb_pending = len(feedback_list(plugin=p, pending_only=True))
        props = {s: len(proposal_list(plugin=p, status=s)) for s in PROPOSAL_STATUSES}
        rows.append({
            "name": p,
            "registered": p in registered,
            "local_path": registered.get(p, {}).get("local_path", ""),
            "feedbacks": {"pending": fb_pending, "applied": fb_total - fb_pending, "total": fb_total},
            "proposals": {**props, "total": sum(props.values())},
        })

    totals = {
        "plugins": len(rows),
        "feedbacks_pending": sum(r["feedbacks"]["pending"] for r in rows),
        "feedbacks_applied": sum(r["feedbacks"]["applied"] for r in rows),
        "proposals_pending": sum(r["proposals"]["pending"] for r in rows),
        "proposals_approved": sum(r["proposals"]["approved"] for r in rows),
    }
    return {"plugins": rows, "totals": totals}
