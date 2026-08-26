"""Agregación de triples del panel (sin LLM)."""
import re
from collections import defaultdict
import unicodedata


def _norm_claim(s: str) -> str:
    # normaliza para agrupar claims equivalentes (lower, sin tildes, colapsa ws)
    nfkd = unicodedata.normalize("NFD", s.lower())
    t = "".join(c for c in nfkd if not unicodedata.combining(c))
    t = re.sub(r"\s+", " ", t).strip()
    return t[:120]


def aggregate(all_triples: list, threshold: str = "majority") -> dict:
    """all_triples: lista por agente de lista de triples {claim, evidence, confidence}."""
    n_agents = len(all_triples) if all_triples else 0
    if n_agents == 0:
        return {"consensus": [], "contested": []}
    # agrupa por claim normalizado
    buckets: dict[str, list] = defaultdict(list)
    rep: dict[str, dict] = {}
    for triples in all_triples:
        seen_in_agent = set()
        for t in triples or []:
            claim = (t.get("claim") or "").strip()
            if not claim:
                continue
            key = _norm_claim(claim)
            if key in seen_in_agent:
                continue
            seen_in_agent.add(key)
            ev = [str(x)[:200] for x in (t.get("evidence") or [])[:3]]
            buckets[key].append(t)
            if key not in rep:
                rep[key] = {"claim": claim, "evidence": ev, "confidence": float(t.get("confidence", 0.5))}
            else:
                # promedia confianza y une evidencia
                prev = rep[key]
                prev["confidence"] = (prev["confidence"] + float(t.get("confidence", 0.5))) / 2
                merged = list(dict.fromkeys(prev["evidence"] + ev))[:3]
                prev["evidence"] = merged

    need = n_agents if threshold == "strict" else (n_agents // 2 + 1)
    consensus, contested = [], []
    for key, members in buckets.items():
        # cuenta cuántos agentes distintos aportaron ese claim
        count = len(members)
        target = rep[key]
        if count >= need:
            consensus.append(target)
        else:
            contested.append(target)
    # ordena por confianza desc
    consensus.sort(key=lambda x: x["confidence"], reverse=True)
    contested.sort(key=lambda x: x["confidence"], reverse=True)
    return {"consensus": consensus, "contested": contested}


def parse_llm_output(text: str) -> list:
    """Extrae lista de triples desde texto del modelo (JSON array o NDJSON). ponytail: si no es JSON, intenta extraer ```json blocks."""
    import json

    text = text.strip()
    for cand in [text, text.strip("`")]:
        try:
            data = json.loads(cand)
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict) and d.get("claim")]
        except Exception:
            pass
    # buscar bloques ```json ... ```
    for m in re.finditer(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL):
        try:
            data = json.loads(m.group(1))
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict) and d.get("claim")]
        except Exception:
            continue
    return []
