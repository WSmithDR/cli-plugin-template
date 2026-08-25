#!/usr/bin/env python3
"""Store de aprendizajes vigentes. Standalone: sin deps más allá de stdlib.

Un aprendizaje es markdown con frontmatter sellado por el store:
  scope / created / last_updated / category
Upsert por slug: guardar dos veces CORRIGE, no duplica. created se preserva;
last_updated es siempre hoy. Borrado real — lo obsoleto no se archiva.
"""
import os
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Optional

CATEGORIES = ("convencion", "integracion-cli", "compat-multi-cli")
GLOBAL_SCOPE = "_global"


def data_dir() -> Path:
    override = os.environ.get("MY_PLUGIN_DATA_DIR")  # ← adaptar
    return Path(override) if override else Path.home() / ".local/share/my-plugin"


def learnings_dir(scope: str) -> Path:
    return data_dir() / scope / "learnings"


def slugify(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    flat = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", flat).strip("-")[:60]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _fm_get(content: str, key: str) -> str:
    m = re.search(rf"^{key}:\s*(.+)$", content, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _fm_set(content: str, fields: dict) -> str:
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)
    fm = "\n".join(f"{k}: {v}" for k, v in fields.items())
    return f"---\n{fm}\n---\n{body.lstrip()}"


def learning_save(slug: str, content: str, plugin: Optional[str] = None,
                  category: Optional[str] = None) -> str:
    category = _fm_get(content, "category") or category
    if category and category not in CATEGORIES:
        raise SystemExit(f"categoría inválida: {category} (usá una de {', '.join(CATEGORIES)})")
    scope = slugify(plugin) if plugin else GLOBAL_SCOPE
    path = learnings_dir(scope) / f"learning_{slugify(slug)}.md"
    prev = _read(path)
    today = date.today().isoformat()
    stamped = {"scope": scope,
               "created": _fm_get(prev, "created") or _fm_get(content, "created") or today,
               "last_updated": today}
    if category:
        stamped["category"] = category
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_fm_set(content, stamped), encoding="utf-8")
    return str(path)


def learning_list(plugin: Optional[str] = None,
                  category: Optional[str] = None) -> list:
    """`<scope>/<slug>` de los aprendizajes vigentes; lo del plugin MÁS el global."""
    scopes = ([slugify(plugin), GLOBAL_SCOPE] if plugin else [GLOBAL_SCOPE])
    out = []
    for scope in scopes:
        d = learnings_dir(scope)
        if not d.exists():
            continue
        for path in sorted(d.glob("learning_*.md")):
            if category and _fm_get(_read(path), "category") != category:
                continue
            out.append(f"{scope}/{path.stem[len('learning_'):]}")
    return out


def learning_load(scope: str, slug: str) -> str:
    path = learnings_dir(scope) / f"learning_{slugify(slug)}.md"
    if not path.exists():
        raise SystemExit(f"no existe el aprendizaje: {scope}/{slug}")
    return _read(path)


def learning_delete(scope: str, slug: str) -> str:
    path = learnings_dir(scope) / f"learning_{slugify(slug)}.md"
    if not path.exists():
        raise SystemExit(f"no existe el aprendizaje: {scope}/{slug}")
    path.unlink()
    return str(path)


if __name__ == "__main__":
    # Self-check mínimo
    import tempfile
    os.environ["MY_PLUGIN_DATA_DIR"] = tempfile.mkdtemp()
    p = learning_save("test-slug", "cuerpo de prueba", plugin="miplugin",
                      category="convencion")
    assert "learning_test-slug.md" in p and learning_list("miplugin") == ["miplugin/test-slug"]
    first_created = _fm_get(learning_load("miplugin", "test-slug"), "created")
    learning_save("test-slug", "cuerpo corregido", plugin="miplugin", category="convencion")
    assert _fm_get(learning_load("miplugin", "test-slug"), "created") == first_created
    assert len(learning_list("miplugin")) == 1
    learning_delete("miplugin", "test-slug")
    assert learning_list("miplugin") == []
    print("OK")
