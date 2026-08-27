"""Scorecard de modelos gratuitos + health-check + degradación de laggards."""
import json
import os
import subprocess
import time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

# Allowlist dura: solo estos marcadores se consideran gratuitos/ilimitados
FREE_MARKERS = ("free", "alpha", "unlimited", "ox-", "gpt-oss", "gemini-flash")
# Si el listado no trae marker, se asume de pago y se descarta
LAGGARD_THRESHOLD = 0.35  # acuerdo útil <35% durante N corridas
LAGGARD_WINDOW = 5

def scorecard_load() -> dict:
    p = paths.harvest_scorecard_file()
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}

def scorecard_save(d: dict) -> None:
    p = paths.harvest_scorecard_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(p))

def discover_free_models() -> list[str]:
    """Ejecuta `opencode models` y filtra solo gratuitos. Sin hardcodear lista."""
    try:
        out = subprocess.run(["opencode", "models", "--json"], capture_output=True, text=True, timeout=20)
        # ponytail: si el flag --json no existe, probar sin flag y parsear líneas
        raw = out.stdout.strip()
        models = []
        if raw.startswith("[") or raw.startswith("{"):
            data = json.loads(raw)
            if isinstance(data, dict) and "models" in data:
                data = data["models"]
            for m in (data if isinstance(data, list) else []):
                name = m.get("id") or m.get("name") or str(m)
                if any(marker in name.lower() for marker in FREE_MARKERS):
                    models.append(name)
        else:
            for line in raw.splitlines():
                name = line.strip().split()[0] if line.strip() else ""
                if name and any(marker in name.lower() for marker in FREE_MARKERS):
                    models.append(name)
        return sorted(set(models))
    except Exception:
        return []

def health_check(model: str) -> bool:
    """Prompt mínimo: si el modelo no responde, es fallo."""
    try:
        out = subprocess.run(["opencode", "run", "--model", model, "--prompt", "ping: responde pong"],
                             capture_output=True, text=True, timeout=30)
        return out.returncode == 0 and "pong" in out.stdout.lower()
    except Exception:
        return False

def scorecard_update(model: str, agreed: int, latency_ms: int, failed: bool) -> None:
    sc = scorecard_load()
    entry = sc.get(model, {"runs": 0, "agreed": 0, "total": 0, "failures": 0, "lat_ms": []})
    entry["runs"] += 1
    entry["total"] += agreed  # ponytail: total = triples efectivamente producidos (antes hardcode 10)
    entry["agreed"] += agreed
    if failed:
        entry["failures"] += 1
    entry["lat_ms"] = (entry["lat_ms"][-20:] + [latency_ms])[-20:]
    # marca laggard si acuerdo < threshold en ventana
    window_agree = entry["agreed"] / max(1, entry["total"])
    entry["laggard"] = entry["runs"] >= LAGGARD_WINDOW and window_agree < LAGGARD_THRESHOLD
    sc[model] = entry
    scorecard_save(sc)

def pick_models(pool_size: int = 3) -> list[str]:
    sc = scorecard_load()
    free = discover_free_models()
    # si no hay descubrimiento (sin opencode), usar los del scorecard que no sean laggard
    if not free:
        free = [m for m, v in sc.items() if not v.get("laggard")]
        # sin historial: devolver vacío y que el runner aborte con aviso (nunca degradar a pago)
        return free[:pool_size]
    # filtra laggards
    candidates = [m for m in free if not sc.get(m, {}).get("laggard")]
    if not candidates:
        candidates = [m for m in free if sc.get(m, {}).get("runs", 0) < LAGGARD_WINDOW]
    # ordena por score (agreed/total) desc, luego latencia asc
    def _score(m):
        v = sc.get(m, {})
        agree = v.get("agreed", 0) / max(1, v.get("total", 0)) if v else 0.5
        lat = sum(v.get("lat_ms", [2000])) / max(1, len(v.get("lat_ms", [2000]))) if v else 2000
        return (-agree, lat)
    candidates.sort(key=_score)
    return candidates[:pool_size]
