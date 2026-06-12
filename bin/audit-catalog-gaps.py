#!/usr/bin/env python3
"""Audita un plugin contra el catálogo: qué features detectables faltan.

Reemplaza la "Parte A" del skill plugin-audit, donde el LLM adivinaba a ojo
qué features del catálogo estaban presentes. Eso contradecía el principio
`bundled-scripts` ("lo determinista → script"). Acá se hace de forma
determinista: mismo árbol de archivos → mismo reporte. El LLM solo interpreta
y prioriza la salida; no enumera a mano.

Recibe una RUTA al plugin a auditar (por defecto la cwd) y, para cada feature
"detectable por señales de archivo", marca:
  ✓ presente   — la señal aparece en el árbol
  ✗ falta      — no aparece (candidato a integrar)
  n/d          — no se detecta de forma confiable con señales de archivo
                 (requiere juicio humano/LLM)

Señales implementadas (criterio: baja tasa de falsos positivos):
  versioning          un hook `post-commit` (en cualquier dir) que mencione
                      "version"/"bump" → lógica de auto-bump.
  git-hooks           un `setup.sh` que instale hooks (menciona `.git/hooks`
                      o `hooks/`) + algún `test*.sh` en el repo.
  health-check        una skill cuyo dir matchee `*health*` (p.ej. `*-health`).
  claude-code-hooks   existe `hooks/hooks.json`.
  docs-conventions    el README principal tiene headings de install + update +
                      versionado (los tres conceptos presentes).
  multi-cli-compat    existe alguno de: `gemini-extension.json`, `opencode.json`,
                      `.codex-plugin/`, `.cursor-plugin/`, `.copilot-plugin/`,
                      `codex-plugin.json`, `cursor-plugin.json`, `GEMINI.md`,
                      `AGENTS.md`.
  externalized-config existe `config/*.json` (reglas/umbrales externalizados).
  vocabulary-guardian existe `config/vocabulary.json` (o un `vocabulary.json`).
  data-gateway        existe un `cli.py`/`gateway.py` bajo un dir `bin`/`lib`/
                      `scripts` (punto único de persistencia).
  bundled-scripts     existe `bin/` o `scripts/` con al menos un script
                      (`.py`/`.sh`).
  entry-point-router  una skill cuyo dir/nombre sugiera router (`*router*`,
                      `*-dev`, `*-entry*`, `*context*`).  → marcada n/d si la
                      heurística es ambigua (ver abajo).
  proposal-gate       una skill cuyo dir matchee `*propos*` (propuesta).

Features marcados n/d (requieren juicio, señal de archivo poco confiable):
  entry-point-router  un "router" es semántico (una skill que enruta), no una
                      forma de archivo distinguible; se reporta n/d.

Salida:
  Tabla legible `Feature | Estado | Cómo integrarlo`. Con `--json`, lista de
  objetos. Exit 0 SIEMPRE (es un reporte informativo, no un gate). Si la RUTA
  no es un plugin (`.claude-plugin/plugin.json` ausente) → mensaje + exit 2.

Cero rutas absolutas: todo se resuelve relativo a la RUTA recibida.

Uso:
    audit-catalog-gaps.py [RUTA] [--json]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Directorios que nunca se inspeccionan (ruido / no son código del plugin).
SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__",
    "vendor", ".next", "target", "coverage", ".pytest_cache", ".mypy_cache",
}

# Estados posibles.
PRESENT = "present"
MISSING = "missing"
NA = "na"  # n/d — requiere juicio


def _iter_files(root: Path):
    """Genera todos los archivos del árbol, saltando SKIP_DIRS."""
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path


def _iter_dirs(root: Path):
    """Genera todos los directorios del árbol, saltando SKIP_DIRS."""
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_dir():
            yield path


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


# --- Detectores (cada uno devuelve True/False de forma determinista) ---------


def detect_versioning(files: list[Path], root: Path) -> bool:
    """Hook post-commit con lógica de bump (menciona version/bump)."""
    for f in files:
        if f.name == "post-commit":
            text = _read(f).lower()
            if "version" in text or "bump" in text:
                return True
    return False


def detect_git_hooks(files: list[Path], root: Path) -> bool:
    """`setup.sh` que instala hooks + algún test*.sh en el repo."""
    has_setup = False
    for f in files:
        if f.name == "setup.sh":
            text = _read(f)
            if ".git/hooks" in text or "git-hooks" in text or "/hooks/" in text:
                has_setup = True
                break
    has_test = any(
        re.fullmatch(r"test.*\.sh", f.name) for f in files
    )
    return has_setup and has_test


def detect_health_check(dirs: list[Path], root: Path) -> bool:
    """Skill cuyo dir matchee *health* (p.ej. *-health)."""
    for d in dirs:
        if "health" in d.name.lower() and "skills" in d.parts:
            return True
    # Permitir también skills sueltas sin un dir "skills/" explícito.
    return any("health" in d.name.lower() and (d / "SKILL.md").exists()
               for d in dirs)


def detect_claude_code_hooks(root: Path) -> bool:
    """Existe hooks/hooks.json."""
    return (root / "hooks" / "hooks.json").is_file()


def detect_docs_conventions(root: Path) -> bool:
    """README principal con headings de install + update + versionado."""
    readme = None
    for name in ("README.md", "Readme.md", "readme.md"):
        if (root / name).is_file():
            readme = root / name
            break
    if readme is None:
        return False
    headings = [
        line.lower()
        for line in _read(readme).splitlines()
        if line.lstrip().startswith("#")
    ]
    blob = "\n".join(headings)
    has_install = bool(re.search(r"instal", blob))
    has_update = bool(re.search(r"updat|actualiz", blob))
    has_version = bool(re.search(r"versio", blob))
    return has_install and has_update and has_version


def detect_multi_cli_compat(files: list[Path], dirs: list[Path], root: Path) -> bool:
    """Manifiestos/marcadores de otros CLIs además de Claude Code."""
    file_markers = {
        "gemini-extension.json", "opencode.json", "codex-plugin.json",
        "cursor-plugin.json", "copilot-plugin.json", "GEMINI.md", "AGENTS.md",
    }
    dir_markers = {".codex-plugin", ".cursor-plugin", ".copilot-plugin"}
    if any(f.name in file_markers for f in files):
        return True
    if any(d.name in dir_markers for d in dirs):
        return True
    return False


def detect_externalized_config(files: list[Path], root: Path) -> bool:
    """Algún config/*.json (reglas/umbrales externalizados)."""
    for f in files:
        if f.suffix == ".json" and "config" in f.parts:
            return True
    return False


def detect_vocabulary_guardian(files: list[Path], root: Path) -> bool:
    """Un vocabulary.json (idealmente bajo config/)."""
    return any(f.name == "vocabulary.json" for f in files)


def detect_data_gateway(files: list[Path], root: Path) -> bool:
    """Un cli.py/gateway.py bajo bin/lib/scripts (punto único de persistencia)."""
    holders = {"bin", "lib", "scripts"}
    for f in files:
        if f.name in ("gateway.py", "cli.py") and holders & set(f.parts):
            return True
    return False


def detect_bundled_scripts(root: Path) -> bool:
    """bin/ o scripts/ con al menos un script .py/.sh."""
    for sub in ("bin", "scripts"):
        d = root / sub
        if d.is_dir():
            for f in d.rglob("*"):
                if f.is_file() and f.suffix in (".py", ".sh"):
                    return True
    return False


def detect_proposal_gate(dirs: list[Path], root: Path) -> bool:
    """Skill cuyo dir matchee *propos* (gate de propuesta)."""
    for d in dirs:
        if "propos" in d.name.lower() and (
            "skills" in d.parts or (d / "SKILL.md").exists()
        ):
            return True
    return False


# --- Definición de las features auditadas ------------------------------------
# Cada entrada: (clave-feature, función-detectora). Las marcadas con None en el
# detector se reportan como n/d (requieren juicio).

def build_report(root: Path) -> list[dict]:
    files = list(_iter_files(root))
    dirs = list(_iter_dirs(root))

    checks: list[tuple[str, object]] = [
        ("versioning", detect_versioning(files, root)),
        ("git-hooks", detect_git_hooks(files, root)),
        ("health-check", detect_health_check(dirs, root)),
        ("claude-code-hooks", detect_claude_code_hooks(root)),
        ("docs-conventions", detect_docs_conventions(root)),
        ("multi-cli-compat", detect_multi_cli_compat(files, dirs, root)),
        ("externalized-config", detect_externalized_config(files, root)),
        ("vocabulary-guardian", detect_vocabulary_guardian(files, root)),
        ("data-gateway", detect_data_gateway(files, root)),
        ("bundled-scripts", detect_bundled_scripts(root)),
        ("proposal-gate", detect_proposal_gate(dirs, root)),
        # Semánticas: una "skill que enruta" no tiene forma de archivo
        # distinguible con baja tasa de falsos positivos → n/d.
        ("entry-point-router", None),
    ]

    report: list[dict] = []
    for name, result in checks:
        if result is None:
            status = NA
        else:
            status = PRESENT if result else MISSING
        report.append({"feature": name, "status": status})
    return report


# --- Salida ------------------------------------------------------------------

ICON = {PRESENT: "✓", MISSING: "✗", NA: "·"}
LABEL = {PRESENT: "presente", MISSING: "falta", NA: "n/d"}


def render_table(report: list[dict]) -> str:
    rows = []
    for r in report:
        feat, status = r["feature"], r["status"]
        if status == MISSING:
            how = f"/plugin-feature {feat}"
        elif status == NA:
            how = "requiere juicio (no detectable por archivo)"
        else:
            how = "—"
        rows.append((f"{ICON[status]} {LABEL[status]}", feat, how))

    w_feat = max((len(f) for _, f, _ in rows), default=7)
    w_state = max((len(s) for s, _, _ in rows), default=6)
    w_feat = max(w_feat, len("Feature"))
    w_state = max(w_state, len("Estado"))

    out = []
    out.append(
        f"{'Feature'.ljust(w_feat)}  {'Estado'.ljust(w_state)}  Cómo integrarlo"
    )
    out.append(f"{'-' * w_feat}  {'-' * w_state}  {'-' * 15}")
    for state, feat, how in rows:
        out.append(f"{feat.ljust(w_feat)}  {state.ljust(w_state)}  {how}")

    present = sum(1 for r in report if r["status"] == PRESENT)
    missing = sum(1 for r in report if r["status"] == MISSING)
    na = sum(1 for r in report if r["status"] == NA)
    out.append("")
    out.append(f"Total: {present} presentes · {missing} faltan · {na} n/d")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    as_json = "--json" in argv
    root = Path(args[0]).resolve() if args else Path.cwd()

    if not root.is_dir():
        print(f"✗ no es un directorio: {root}", file=sys.stderr)
        return 2

    manifest = root / ".claude-plugin" / "plugin.json"
    if not manifest.is_file():
        print(
            f"✗ {root.name}/ no parece un plugin: falta "
            f".claude-plugin/plugin.json",
            file=sys.stderr,
        )
        return 2

    report = build_report(root)

    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f"Gap de catálogo — {root.name}/\n")
    print(render_table(report))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
