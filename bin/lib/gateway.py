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

def _fm_get(content: str, field: str) -> Optional[str]:
    m = re.search(rf"^{field}:\s*(\S+)", content, re.MULTILINE)
    return m.group(1) if m else None


def _fm_set(content: str, fields: dict) -> str:
    """Escribe campos en el frontmatter (reemplaza o inserta tras el `---` de apertura),
    y de paso normaliza el formato viejo: borra los booleanos `applied:`/`discarded:` y
    renombra `created_at:` → `created:`. Si no hay frontmatter, lo crea."""
    if not content.startswith("---"):
        content = "---\n---\n" + content
    m = re.match(r"---\n(.*?\n)---", content, re.DOTALL)
    if m:  # limpieza acotada al frontmatter: el body puede citar 'applied:' en un snippet
        fm = re.sub(r"^(applied|discarded)(_at)?:.*\n", "", m.group(1), flags=re.MULTILINE)
        content = "---\n" + fm + "---" + content[m.end():]
    content = re.sub(r"^created_at:", "created:", content, count=1, flags=re.MULTILINE)
    for field, value in reversed(list(fields.items())):
        if re.search(rf"^{field}:", content, re.MULTILINE):
            content = re.sub(rf"^{field}:.*$", f"{field}: {value}",
                             content, count=1, flags=re.MULTILINE)
        else:
            content = re.sub(r"^---\s*$", f"---\n{field}: {value}",
                             content, count=1, flags=re.MULTILINE)
    return content


def _plugin_version(plugin: str) -> Optional[str]:
    """La versión que declara el manifiesto del plugin en su repo local, o None.

    Ojo con lo que significa: es la versión del árbol que `plugin-hotpatch` va a
    parchear, que no siempre es la que se estaba usando cuando apareció la fricción
    (el clon local puede estar atrasado respecto de la versión instalada). Por eso
    quien captura puede declarar `plugin_version` en el frontmatter y gana sobre esto.
    Sin manifiesto no se inventa nada: mejor sin campo que con una versión falsa."""
    local = (registry_get(plugin) or {}).get("local_path", "")
    if not local:
        return None
    manifest = (registry_get(plugin) or {}).get("manifest") or ".claude-plugin/plugin.json"
    return _read_json(Path(local) / manifest, {}).get("version") or None


def _foreign_path(plugin: str, declared: Optional[str]) -> Optional[str]:
    """La raíz desde donde CORRIÓ el plugin, y solo si no es la del registry.

    Nunca se infiere: `cpt` no tiene cómo saberlo —su propio `CLAUDE_PLUGIN_ROOT`
    apunta al meta-plugin, no al plugin bajo prueba—. El único que ve la ruta real es
    quien captura, que la tiene en el `Base directory for this skill:` de la
    invocación (con `--plugin-dir`, esa ruta es la local).

    Si coincide con `local_path` se descarta: sellar lo que ya dice el registry es
    ruido. Cuando difiere, en cambio, es la advertencia que `plugin-hotpatch` necesita
    — va a parchear `local_path`, que NO es el árbol donde se vio la fricción."""
    if not declared:
        return None
    local = (registry_get(plugin) or {}).get("local_path", "")
    if not local:
        return declared
    try:
        if Path(declared.strip("\"'")).resolve() == Path(local).resolve():
            return None
    except OSError:
        pass  # ruta irresoluble (borrada, permisos): se conserva tal cual se declaró
    return declared


def feedback_save(plugin: str, slug: str, content: str) -> str:
    """Guarda un feedback bajo el plugin con el frontmatter normalizado:
    `status` + `created` + `last_updated` + `plugin_version` + `plugin_path`.
    Devuelve la ruta escrita.

    Reparto de responsabilidades: el contenido manda sobre el cuerpo, `feedback_set_status`
    manda sobre el estado (por eso al sobrescribir gana el status ya guardado, no el que
    traiga el contenido nuevo), y el store manda sobre las fechas — `created` se preserva
    del archivo previo (o de su `created_at` viejo) y `last_updated` es siempre hoy.

    `plugin_version` sella contra QUÉ versión se observó la fricción, porque un feedback
    sin versión parece hablar del código de hoy: un `patch_target` puede haber dejado de
    existir entre la captura y el patch. Se preserva como `created` — describe el momento
    de la observación, no el de la última escritura— y solo se completa desde el manifiesto
    cuando el archivo es nuevo: a un feedback viejo sin sello no se le inventa uno.

    `plugin_path` es su complemento para cuando el plugin corrió desde otro árbol que el
    del registry (`claude --plugin-dir <ruta>`, un worktree, otro clon). Solo lo declara
    quien captura, y solo sobrevive si difiere de `local_path` — ver `_foreign_path`."""
    path = paths.feedbacks_dir(plugin) / f"feedback_{paths.slugify(slug)}.md"
    prev = _read(path)
    today = _today()
    created = (_fm_get(prev, "created") or _fm_get(prev, "created_at")
               or _fm_get(content, "created") or _fm_get(content, "created_at") or today)
    stamped = {"status": _state_of(prev or content),
               "created": created, "last_updated": today}
    version = (_fm_get(content, "plugin_version") or _fm_get(prev, "plugin_version")
               or (_plugin_version(plugin) if not prev else None))
    if version:
        stamped["plugin_version"] = version
    foreign = _foreign_path(plugin, _fm_get(content, "plugin_path") or _fm_get(prev, "plugin_path"))
    if foreign:
        stamped["plugin_path"] = foreign
    else:
        # Declarada pero redundante: se borra en vez de dejarla repitiendo el registry.
        content = re.sub(r"^plugin_path:.*\n", "", content, count=1, flags=re.MULTILINE)
    _write(path, _fm_set(content, stamped))
    return str(path)


def feedback_load(plugin: str, slug: str) -> str:
    path = paths.feedbacks_dir(plugin) / f"feedback_{paths.slugify(slug)}.md"
    return _read(path)


def _strip_prefix(stem: str) -> str:
    return stem[len("feedback_"):] if stem.startswith("feedback_") else stem


FEEDBACK_STATUSES = ("pending", "applied", "discarded")


def _state_of(content: str) -> str:
    """'pending' | 'applied' | 'discarded' según el frontmatter.
    Lee `status:`; si no está, cae al formato viejo (booleanos `applied:`/`discarded:`),
    así los feedbacks escritos antes de la unificación siguen valiendo sin migración."""
    m = re.search(r"^status:\s*(\S+)", content, re.MULTILINE)
    if m and m.group(1) in FEEDBACK_STATUSES:
        return m.group(1)
    if re.search(r"^discarded:\s*true", content, re.MULTILINE):
        return "discarded"
    m = re.search(r"^applied:\s*(\S+)", content, re.MULTILINE)
    return "pending" if (m is None or m.group(1) == "false") else "applied"


def _feedback_state(path: Path) -> str:
    return _state_of(path.read_text(encoding="utf-8"))


def _is_pending(path: Path) -> bool:
    return _feedback_state(path) == "pending"


def feedback_list(plugin: Optional[str] = None, pending_only: bool = False,
                  state: Optional[str] = None) -> list[str]:
    """Lista feedbacks como '<plugin>/<slug>'. plugin=None → todos los registrados
    + cualquier subdir con feedbacks. pending_only deja solo los pendientes;
    state filtra por 'pending'|'applied'|'discarded'."""
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
            st = _feedback_state(f)
            if pending_only and st != "pending":
                continue
            if state is not None and st != state:
                continue
            result.append(f"{p}/{_strip_prefix(f.stem)}")
    return result


def feedback_set_status(plugin: str, slug: str, status: str, at: Optional[str] = None) -> str:
    """Pone `status: <status>` + `last_updated: <fecha>` en el frontmatter. Idempotente.
    Si el feedback venía del formato viejo, `_fm_set` lo normaliza: `status` queda como
    única fuente de verdad y `created` se preserva."""
    if status not in FEEDBACK_STATUSES:
        raise ValueError(f"status inválido: {status} (esperado: {'|'.join(FEEDBACK_STATUSES)})")
    path = paths.feedbacks_dir(plugin) / f"feedback_{paths.slugify(slug)}.md"
    content = _read(path)
    if not content:
        raise FileNotFoundError(f"feedback no existe: {plugin}/{slug}")
    _write(path, _fm_set(content, {"status": status, "last_updated": at or _today()}))
    return str(path)


# ── harvest offsets (detección idempotente de fricción) ──────

def harvest_offset_get(key: str) -> int:
    """Offset ya escaneado del transcript `key` (0 si nunca se escaneó)."""
    offsets = _read_json(paths.harvest_offsets_file(), {}) or {}
    value = offsets.get(key, 0)
    return value if isinstance(value, int) and value >= 0 else 0


def harvest_offset_set(key: str, value: int) -> None:
    offsets = _read_json(paths.harvest_offsets_file(), {}) or {}
    offsets[key] = value
    _write_json(paths.harvest_offsets_file(), offsets)


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
        fb_discarded = len(feedback_list(plugin=p, state="discarded"))
        props = {s: len(proposal_list(plugin=p, status=s)) for s in PROPOSAL_STATUSES}
        rows.append({
            "name": p,
            "registered": p in registered,
            "local_path": registered.get(p, {}).get("local_path", ""),
            "feedbacks": {"pending": fb_pending, "applied": fb_total - fb_pending - fb_discarded,
                          "discarded": fb_discarded, "total": fb_total},
            "proposals": {**props, "total": sum(props.values())},
        })

    totals = {
        "plugins": len(rows),
        "feedbacks_pending": sum(r["feedbacks"]["pending"] for r in rows),
        "feedbacks_applied": sum(r["feedbacks"]["applied"] for r in rows),
        "feedbacks_discarded": sum(r["feedbacks"]["discarded"] for r in rows),
        "proposals_pending": sum(r["proposals"]["pending"] for r in rows),
        "proposals_approved": sum(r["proposals"]["approved"] for r in rows),
    }
    return {"plugins": rows, "totals": totals}
