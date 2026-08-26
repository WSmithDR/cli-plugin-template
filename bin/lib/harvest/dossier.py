"""Dossier por plugin: lo que ve el panel LLM (con tope y anti-ruido)."""
import json
from pathlib import Path

SKIP_PARTS = {"node_modules", ".git", "__pycache__"}
MAX_FILE_BYTES = 40_000

def build_dossier(plugin_path: str | Path, cli: str, max_bytes: int = 120_000) -> dict:
    root = Path(plugin_path)
    files = []
    # fuente propia siempre
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_PARTS for part in p.parts):
            continue
        # en opencode: packages bajo cache ya filtrados por scan (no descender a deps transitivas)
        rel = str(p.relative_to(root))
        if rel.startswith(".git/"):
            continue
        files.append(rel)
    files = sorted(files)[:200]

    excerpts = []
    used = 0
    # prioridad: manifests y SKILL.md primero
    def _priority(f: str) -> int:
        if f.endswith("plugin.json") or f.endswith("gemini-extension.json"):
            return 0
        if f.endswith("SKILL.md"):
            return 1
        if f.endswith("README.md"):
            return 2
        if f.startswith("skills/"):
            return 3
        if f.startswith("hooks/") or f.startswith("agents/"):
            return 4
        return 9
    files.sort(key=_priority)
    for rel in files:
        if used >= max_bytes:
            break
        p = root / rel
        try:
            if p.stat().st_size > MAX_FILE_BYTES:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if len(text) > MAX_FILE_BYTES:
            text = text[:MAX_FILE_BYTES] + "\n…[truncado]"
        if used + len(text) > max_bytes:
            text = text[: max_bytes - used] + "\n…[truncado por dossier]"
        excerpts.append({"path": rel, "content": text})
        used += len(text)

    manifest = {}
    for cand in (root / "plugin.json", root / ".claude-plugin/plugin.json", root / "gemini-extension.json"):
        if cand.exists():
            try:
                manifest = json.loads(cand.read_text(encoding="utf-8"))
            except Exception:
                pass
            break
    return {"cli": cli, "path": str(root), "manifest": manifest, "files": files, "excerpts": excerpts}
