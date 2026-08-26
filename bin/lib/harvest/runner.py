"""Orquestador harvest_run: cola -> dossier -> homologación exacta -> panel LLM -> consenso -> persistencia."""
import json
import subprocess
import time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths
import gateway
from harvest.ir import plugin_to_ir, ir_hash
from harvest.dossier import build_dossier
from harvest.consensus import aggregate, parse_llm_output
from harvest.scorecard import pick_models, health_check, scorecard_update, discover_free_models

def _homology_exact(pending: list) -> list:
    """Agrupa plugins con IR idéntico (hash igual) — homologación gratis sin LLM."""
    from collections import defaultdict
    by_hash = defaultdict(list)
    for p in pending:
        try:
            ir = plugin_to_ir(p["path"], p["cli"])
            by_hash[ir_hash(ir)].append(p)
        except Exception:
            pass
    homologies = []
    for h, group in by_hash.items():
        if len(group) > 1:
            for i in range(len(group)):
                for j in range(i+1, len(group)):
                    homologies.append({"a": group[i], "b": group[j], "hash": h, "type": "exact"})
    return homologies

def _run_panel(dossier: dict, models: list) -> list:
    """Despacha N agentes en paralelo vía opencode run, recoge triples."""
    if not models:
        return []
    # prompt canónico del panel (corto, exige triples JSON)
    prompt = (
        "Analiza este plugin (dossier adjunto) y emite SOLO un JSON array de triples "
        "{claim, evidence (<=3 citas exactas), confidence 0-1}. "
        "Dos tipos: hallazgos generales y homologaciones vs otros CLIs (hooks<->powers<->agents). "
        "Evidencia = citas literales de manifests/código, no resúmenes.\n"
        f"Dossier: {json.dumps(dossier, ensure_ascii=False)[:8000]}"
    )
    results = []
    procs = []
    for m in models:
        procs.append(subprocess.Popen(
            ["opencode", "run", "--model", m, "--prompt", prompt],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
    for proc, model in zip(procs, models):
        try:
            out, err = proc.communicate(timeout=120)
            triples = parse_llm_output(out or "")
            results.append(triples)
            scorecard_update(model, agreed=len(triples), latency_ms=1000, failed=len(triples)==0)
        except subprocess.TimeoutExpired:
            proc.kill()
            scorecard_update(model, agreed=0, latency_ms=120000, failed=True)
            results.append([])
        except Exception:
            results.append([])
    return results

def harvest_run(panel_size: int = 3, max_plugins: int = 3, threshold: str = "majority", dry_run: bool = False) -> dict:
    pending_file = paths.harvest_pending_file()
    homologies_file = paths.harvest_homologies_file()
    contested_file = paths.harvest_contested_file()
    try:
        pending = json.loads(pending_file.read_text(encoding="utf-8")) if pending_file.exists() else []
    except Exception:
        pending = []
    if not pending:
        return {"processed": 0, "consensus_saved": 0, "homologies": [], "contested": []}

    # homologación exacta primero (gratis)
    exact = _homology_exact(pending)
    # persistir homologías exactas
    try:
        existing = json.loads(homologies_file.read_text(encoding="utf-8")) if homologies_file.exists() else []
    except Exception:
        existing = []
    existing.extend(exact)
    homologies_file.parent.mkdir(parents=True, exist_ok=True)
    homologies_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    # presupuesto por corrida
    batch = pending[:max_plugins]
    remaining = pending[max_plugins:]

    if dry_run:
        # en dry-run no hay LLM: solo dossier + homologación exacta
        for p in batch:
            build_dossier(p["path"], p["cli"])
        pending_file.write_text(json.dumps(remaining, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"processed": len(batch), "consensus_saved": 0, "homologies": exact, "contested": []}

    models = pick_models(panel_size)
    if not models:
        # sin modelos gratuitos disponibles -> aborta dejando cola intacta (nunca degrada a pago)
        return {"processed": 0, "consensus_saved": 0, "homologies": exact, "contested": [], "error": "sin modelos gratuitos disponibles (opencode models vacío o sin auth)"}

    # health-check y reemplazo
    live = []
    for m in models:
        if health_check(m):
            live.append(m)
        else:
            scorecard_update(m, agreed=0, latency_ms=0, failed=True)
    if len(live) < 2:
        return {"processed": 0, "consensus_saved": 0, "homologies": exact, "contested": [], "error": "menos de 2 modelos sanos, abortando pasada"}

    total_saved = 0
    all_contested = []
    for p in batch:
        dossier = build_dossier(p["path"], p["cli"])
        all_triples = _run_panel(dossier, live)
        res = aggregate(all_triples, threshold=threshold)
        # persistir consenso como learnings
        for t in res["consensus"]:
            ev = "; ".join(t.get("evidence", []))
            body = f"{t['claim']}\n\nEvidencia: {ev}\nConfianza: {t['confidence']}"
            # ponytail: slug a partir del claim (40 chars) — colisión improbable en este dominio
            slug = t["claim"][:40]
            try:
                gateway.learning_save(slug, body, plugin=None, category=None)
                total_saved += 1
            except Exception:
                pass
        all_contested.extend(res["contested"])

    # contested a disco
    try:
        prev_c = json.loads(contested_file.read_text(encoding="utf-8")) if contested_file.exists() else []
    except Exception:
        prev_c = []
    prev_c.extend(all_contested)
    contested_file.write_text(json.dumps(prev_c, ensure_ascii=False, indent=2), encoding="utf-8")
    pending_file.write_text(json.dumps(remaining, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"processed": len(batch), "consensus_saved": total_saved, "homologies": exact, "contested": all_contested}
