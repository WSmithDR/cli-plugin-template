#!/usr/bin/env python3
"""audit-doc-drift: las afirmaciones negativas sobre APIs de hosts ("X no expone Y",
"sin equivalente") se pudren cuando el host evoluciona y nadie se entera. Exige que
toda afirmación negativa lleve una fecha de verificación fresca: "(verificado YYYY-MM-DD".
Reporte only — exit 0 siempre (es un hallazgo, no un gate). Soporta --json."""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

MARKERS = re.compile(r"(no expone|no emite|sin equivalente)", re.IGNORECASE)
VERIFIED = re.compile(r"\(verificado (\d{4}-\d{2}-\d{2})")
FRESH_DAYS = 180
# ponytail: marcadores angostos a propósito — la convención (ver Parte D de plugin-audit)
# define qué frases disparan la obligación de fecha; ampliarlos trae falsos positivos
# sobre comportamiento local/test que no es claim sobre un host.
SKIP_DIRS = {"node_modules", ".git", ".todo"}
EXTS = {".md", ".py", ".ts", ".js", ".sh", ".yml", ".yaml", ".json"}


def scan_line(line: str) -> str | None:
    """Ignora lo que esté dentro de backticks: ejemplos y código no son afirmaciones."""
    return MARKERS.search(re.sub(r"`[^`]*`", "", line))


def scan_file(path: Path, today: datetime) -> list[dict]:
    try:
        lines = path.read_text().splitlines()
    except Exception:
        return []
    hits, fenced = [], False
    for i, raw in enumerate(lines, 1):
        if raw.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if not scan_line(raw):
            continue
        window = "\n".join(lines[i - 1 : i + 2])
        m = VERIFIED.search(window)
        if not m:
            hits.append({"file": str(path), "line": i, "status": "undated",
                         "snippet": raw.strip()[:100],
                         "fix": 'agregar "(verificado YYYY-MM-DD, fuente)"'})
        else:
            age = (today - datetime.strptime(m.group(1), "%Y-%m-%d")).days
            if age > FRESH_DAYS:
                hits.append({"file": str(path), "line": i, "status": "stale",
                             "snippet": raw.strip()[:100],
                             "fix": f"re-verificar contra la doc del host ({age} días)"})
    return hits


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else ".")
    today = datetime.now(timezone.utc).replace(tzinfo=None)
    hits: list[dict] = []
    for p in sorted(root.rglob("*")):
        if p.suffix not in EXTS or not p.is_file():
            continue
        parts = p.parts
        # docs/plans y .todo/DONE son archivo histórico point-in-time; test-* describe
        # comportamiento esperado, no claims; features/*/files se re-escanea en cada
        # plugin downstream que los integre (acá son ejemplos ilustrativos).
        if any(part in SKIP_DIRS for part in parts) or p.name == Path(__file__).name:
            continue
        if p.name.startswith("test-") or ("docs" in parts and "plans" in parts):
            continue
        if "features" in parts and "files" in parts:
            continue
        hits.extend(scan_file(p, today))
    if "--json" in sys.argv:
        print(json.dumps(hits, ensure_ascii=False, indent=2))
        return
    for h in hits:
        tag = "SIN FECHA" if h["status"] == "undated" else "FECHA VENCIDA"
        print(f"  ⚠ {tag:<13} {h['file']}:{h['line']}  {h['snippet']}")
        print(f"                  → {h['fix']}")
    print(f"doc-drift: {len(hits)} afirmación(es) negativa(s) sin verificación fresca")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # reporte best-effort: nunca rompe el flujo del audit
