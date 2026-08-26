"""IR canónico versionado para plugins multi-CLI."""
import hashlib
import json
from pathlib import Path

IR_VERSION = 1
# Componentes que definen identidad del plugin (orden fijo para hash estable)
IR_COMPONENTS = ("manifest", "skills", "hooks", "agents", "commands")


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _collect_files(root: Path) -> dict:
    """Lista relativa de archivos relevantes (sin node_modules)."""
    files = []
    for pat in ("plugin.json", "skills/**/SKILL.md", "skills/**/*.md",
                "hooks/hooks.json", "agents/**", "commands/**",
                ".claude-plugin/plugin.json", "gemini-extension.json",
                ".opencode/**/*.json"):
        # ponytail: glob simple, no sigue symlinks fuera del root
        for f in root.glob(pat):
            if "node_modules" in f.parts:
                continue
            try:
                rel = str(f.relative_to(root))
                files.append(rel)
            except ValueError:
                pass
    return sorted(set(files))


def plugin_to_ir(plugin_path: str | Path, cli: str) -> dict:
    root = Path(plugin_path)
    manifest = {}
    for cand in (root / "plugin.json", root / ".claude-plugin/plugin.json",
                 root / "gemini-extension.json"):
        if cand.exists():
            try:
                manifest = json.loads(cand.read_text(encoding="utf-8"))
            except Exception:
                manifest = {}
            break
    return {
        "version": IR_VERSION,
        "cli": cli,
        "manifest": manifest,
        "files": _collect_files(root),
        # hash del contenido de los archivos listados (no del filesystem mtime)
        "content_hash": _content_hash(root),
    }


def _content_hash(root: Path) -> str:
    h = hashlib.sha256()
    for rel in sorted(_collect_files(root)):
        p = root / rel
        try:
            h.update(rel.encode())
            h.update(b"\x00")
            h.update(p.read_bytes())
            h.update(b"\x00")
        except Exception:
            pass
    return h.hexdigest()[:16]


def ir_hash(ir: dict) -> str:
    """Hash canónico del IR (12 hex chars) — isomorfismo barato antes del LLM."""
    canonical = json.dumps(ir, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]
