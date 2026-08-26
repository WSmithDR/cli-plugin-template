"""cpt harvest scan — autodetección + IR + diff contra snapshot (sin LLM)."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths
from harvest.ir import plugin_to_ir, ir_hash

# Sondas por CLI: dónde viven los plugins instalados
CLI_SOURCES = {
    "claude": ["~/.claude/plugins"],
    "opencode": ["~/.config/opencode/opencode.json"],
    "gemini": ["~/.gemini/extensions"],
    "kiro": ["~/.kiro"],
    "codex": ["~/.codex"],
    "copilot": ["~/.copilot"],
}

def detect_clis() -> list:
    out = []
    for cli, probes in CLI_SOURCES.items():
        detected = any(Path(os.path.expanduser(p)).exists() for p in probes)
        # también binario en PATH
        import shutil
        has_bin = shutil.which(cli) is not None or shutil.which(f"{cli}-cli") is not None
        out.append({"name": cli, "detected": detected or has_bin, "probes": probes})
    return out

def _opencode_plugins() -> list[Path]:
    """Resuelve plugins declarados en opencode.json -> Paths reales."""
    cfg = Path(os.path.expanduser("~/.config/opencode/opencode.json"))
    if not cfg.exists():
        return []
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except Exception:
        return []
    plugins = []
    for entry in data.get("plugin", []):
        if not isinstance(entry, str):
            continue
        # ponytail: prioriza existencia directa (absoluto/expanduser/relativo a cfg.parent) antes que cache npm
        # esto fija el bug del brief que trataba "/tmp/..." como npm porque solo miraba "/" in entry
        expanded = Path(os.path.expanduser(entry))
        if not expanded.is_absolute():
            # relativo al dir del config (cfg.parent / entry) resuelve tanto "./foo" como "foo/bar"
            # si entry es absoluta, Path(...) / "/tmp/..." -> "/tmp/..." igualmente, pero el caso absoluto ya se filtró arriba
            try:
                expanded = (cfg.parent / entry).resolve()
            except Exception:
                expanded = cfg.parent / entry
        else:
            try:
                expanded = expanded.resolve()
            except Exception:
                pass
        if expanded.exists():
            plugins.append(expanded)
            continue
        if "/" in entry:
            # npm/git -> resuelto bajo cache (si existe)
            cand = Path.home() / ".cache/opencode/packages" / entry.replace("/", "-")
            if cand.exists():
                plugins.append(cand)
    # skills.paths adicionales
    for k, v in data.items():
        if k.startswith("skills"):
            for p in (v if isinstance(v, list) else [v]):
                pp = Path(os.path.expanduser(str(p)))
                if pp.exists():
                    plugins.append(pp)
    return plugins

def _claude_plugins() -> list[Path]:
    base = Path.home() / ".claude/plugins"
    if not base.exists():
        return []
    return [p for p in base.iterdir() if p.is_dir()]

def _gemini_plugins() -> list[Path]:
    base = Path.home() / ".gemini/extensions"
    if not base.exists():
        return []
    return [p for p in base.iterdir() if p.is_dir() and (p / "gemini-extension.json").exists()]

def resolve_plugins(cli: str) -> list[Path]:
    if cli == "opencode":
        return _opencode_plugins()
    if cli == "claude":
        return _claude_plugins()
    if cli == "gemini":
        return _gemini_plugins()
    # kiro/codex/copilot: escanear dirs conocidos si existen
    base = Path.home() / f".{cli}"
    if base.exists():
        return [p for p in base.iterdir() if p.is_dir()][:20]
    return []

def harvest_scan() -> dict:
    """Escanea CLIs detectados, normaliza a IR, diffa contra snapshot y encola cambios."""
    pending_file = paths.harvest_pending_file()
    snapshot_file = paths.harvest_snapshot_file()
    try:
        snapshot = json.loads(snapshot_file.read_text(encoding="utf-8")) if snapshot_file.exists() else {}
    except Exception:
        snapshot = {}
    pending = []
    try:
        pending = json.loads(pending_file.read_text(encoding="utf-8")) if pending_file.exists() else []
    except Exception:
        pending = []
    pending_by_key = {f"{p['cli']}:{p['path']}": p for p in pending}

    scanned = 0
    enqueued = 0
    for info in detect_clis():
        if not info["detected"]:
            continue
        for plug in resolve_plugins(info["name"]):
            scanned += 1
            ir = plugin_to_ir(plug, info["name"])
            h = ir_hash(ir)
            key = f"{info['name']}:{plug}"
            prev = snapshot.get(key)
            if prev == h:
                continue
            snapshot[key] = h
            if key not in pending_by_key:
                pending.append({"cli": info["name"], "path": str(plug), "ir_hash": h})
                pending_by_key[key] = pending[-1]
                enqueued += 1
            else:
                pending_by_key[key]["ir_hash"] = h

    # persistir
    pending_file.parent.mkdir(parents=True, exist_ok=True)
    pending_file.write_text(json.dumps(pending, ensure_ascii=False, indent=2), encoding="utf-8")
    snapshot_file.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"scanned": scanned, "enqueued": enqueued, "pending_total": len(pending)}
