#!/usr/bin/env python3
"""Valida el schema de los archivos de evals de las skills.

Apunta a `skills/<skill>/evals/evals.json` (los evals reales). NO valida el
template `features/skill-evals/files/evals.json`, que tiene placeholders a propósito.

Chequea, para cada evals.json:
  - `skill` es un string no vacío
  - `evals` es una lista no vacía
  - cada eval tiene `id` (str único), `prompt` (str no vacío) y `expectations`
    (lista no vacía de strings no vacíos)
  - campos opcionales bien tipados: `files` (lista de str), `expected_route` (str)
  - `config` opcional: runs_per_config (int>=1), train_test_split (0<x<=1)

La parte semántica (que las expectations no sean tautológicas, que el routing sea
correcto) la hace el grader del feature skill-evals; esto solo valida estructura.

Salida: exit 0 si todo OK, exit 1 con la lista de errores.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

errors: list[str] = []


def eval_files(skills_dir: Path) -> list[Path]:
    if not skills_dir.is_dir():
        return []
    return sorted(skills_dir.glob("*/evals/evals.json"))


def _is_nonempty_str(x) -> bool:
    return isinstance(x, str) and x.strip() != ""


def validate(path: Path) -> None:
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        rel = path
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errors.append(f"{rel}: JSON inválido ({e})")
        return

    if not _is_nonempty_str(data.get("skill")):
        errors.append(f"{rel}: falta 'skill' (string no vacío)")

    evals = data.get("evals")
    if not isinstance(evals, list) or not evals:
        errors.append(f"{rel}: 'evals' debe ser una lista no vacía")
        evals = []

    seen_ids = set()
    for i, ev in enumerate(evals):
        loc = f"{rel} eval[{i}]"
        if not isinstance(ev, dict):
            errors.append(f"{loc}: debe ser un objeto")
            continue
        eid = ev.get("id")
        if not _is_nonempty_str(eid):
            errors.append(f"{loc}: 'id' inválido")
        elif eid in seen_ids:
            errors.append(f"{loc}: 'id' duplicado '{eid}'")
        else:
            seen_ids.add(eid)
        if not _is_nonempty_str(ev.get("prompt")):
            errors.append(f"{loc} ({eid}): 'prompt' vacío")
        exps = ev.get("expectations")
        if not isinstance(exps, list) or not exps:
            errors.append(f"{loc} ({eid}): 'expectations' debe ser lista no vacía")
        elif not all(_is_nonempty_str(e) for e in exps):
            errors.append(f"{loc} ({eid}): 'expectations' con entradas vacías")
        if "files" in ev and not (
            isinstance(ev["files"], list) and all(isinstance(f, str) for f in ev["files"])
        ):
            errors.append(f"{loc} ({eid}): 'files' debe ser lista de strings")
        if "expected_route" in ev and not _is_nonempty_str(ev["expected_route"]):
            errors.append(f"{loc} ({eid}): 'expected_route' debe ser string no vacío")

    cfg = data.get("config")
    if cfg is not None:
        if not isinstance(cfg, dict):
            errors.append(f"{rel}: 'config' debe ser un objeto")
        else:
            rpc = cfg.get("runs_per_config")
            if rpc is not None and not (isinstance(rpc, int) and rpc >= 1):
                errors.append(f"{rel}: config.runs_per_config debe ser int>=1")
            tts = cfg.get("train_test_split")
            if tts is not None and not (isinstance(tts, (int, float)) and 0 < tts <= 1):
                errors.append(f"{rel}: config.train_test_split debe estar en (0, 1]")


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    skills_dir = Path(args[0]).resolve() if args else SKILLS
    files = eval_files(skills_dir)
    for path in files:
        validate(path)
    if errors:
        print("✗ Evals inválidos:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"✓ Evals válidos — {len(files)} archivo(s) verificado(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
