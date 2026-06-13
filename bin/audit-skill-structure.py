#!/usr/bin/env python3
"""Audita skills/ contra la regla de modularización:

   skills/<name>/
     SKILL.md            # instrucciones (qué y por qué, no el código)
     scripts/             # bash, python, node — lógica reusable
     references/          # tablas de mapeo, schemas, guías complementarias
     files/               # templates que el plugin copia al proyecto downstream

Cada skill debería tener sus scripts y referencias modularizadas, no embebidas
inline en SKILL.md ni tiradas sueltas en la raíz de la skill.

Modos de salida:
  - Por defecto: humano legible (tabla de hallazgos).
  - --json: lista de objetos {"skill", "severity", "message"}.
  - --quiet: solo exit code (0 = sin errores, 1 = al menos un ERROR,
             2 = al menos un WARNING).
  - --threshold WARN|ERROR: mínimo severity para fallar (default WARN en
    pre-commit, ERROR en CI).

Uso:
    audit-skill-structure.py [--json|--quiet|--threshold WARN|ERROR]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SKILLS_DIR = Path("skills")
MAX_INLINE_LINES = 10  # fenced code blocks más grandes que esto → sugerir script/


def iter_skills(root: Path) -> list[Path]:
    skills_dir = root / SKILLS_DIR
    if not skills_dir.is_dir():
        return []
    return sorted([d for d in skills_dir.iterdir() if d.is_dir()])


def findings_for_skill(skill_path: Path) -> list[dict]:
    """Revisa una skill y devuelve una lista de hallazgos."""
    name = skill_path.name
    findings: list[dict] = []
    skill_md = skill_path / "SKILL.md"
    has_files_dir = (skill_path / "files").is_dir()
    has_scripts_dir = (skill_path / "scripts").is_dir()
    has_refs_dir = (skill_path / "references").is_dir()
    has_evals_dir = (skill_path / "evals").is_dir()

    if not skill_md.is_file():
        findings.append({"skill": name, "severity": "ERROR", "message": "Falta SKILL.md"})
        return findings

    # Chequear archivos sueltos en la raíz de la skill (no en subdir)
    for f in sorted(skill_path.iterdir()):
        if not f.is_file():
            continue
        if f.name == "SKILL.md":
            continue

        if f.suffix in (".sh", ".py", ".js", ".ts", ".rb"):
            findings.append({
                "skill": name,
                "severity": "ERROR",
                "message": f"{f.name} suelto en la raíz → mover a scripts/",
            })

        elif f.suffix == ".md":
            findings.append({
                "skill": name,
                "severity": "WARNING",
                "message": f"{f.name} suelto en la raíz → mover a references/",
            })

        elif f.suffix in (".json", ".yml", ".yaml", ".toml", ".cfg", ".ini"):
            findings.append({
                "skill": name,
                "severity": "WARNING",
                "message": f"{f.name} suelto en la raíz → mover a references/ o files/",
            })

    # files/ sin SKILL.md que lo referencie
    if has_files_dir and not has_refs_dir:
        files_content = list((skill_path / "files").iterdir())
        if files_content and "files" not in skill_md.read_text(encoding="utf-8", errors="replace"):
            findings.append({
                "skill": name,
                "severity": "WARNING",
                "message": "files/ tiene contenido pero SKILL.md nunca lo menciona",
            })

    # Fenced code blocks en SKILL.md que excedan MAX_INLINE_LINES
    md_text = skill_md.read_text(encoding="utf-8", errors="replace")
    large_blocks = _find_large_blocks(md_text, name)
    findings.extend(large_blocks)

    return findings


LANG_PATTERN = re.compile(r"```(bash|sh|shell|python|py|node|js|javascript|typescript|ts|ruby|rb|go|perl|php)\s*")


def _find_large_blocks(md_text: str, skill_name: str) -> list[dict]:
    """Detecta fenced code blocks con lenguajes de script que excedan el umbral."""
    findings: list[dict] = []
    lines = md_text.split("\n")
    in_block = False
    block_start = 0
    block_lang = ""
    block_lines: list[str] = []

    for i, line in enumerate(lines):
        if line.startswith("```"):
            if not in_block:
                block_start = i
                block_lang = ""
                m = LANG_PATTERN.match(line)
                if m:
                    block_lang = m.group(1)
                in_block = True
                block_lines = []
            else:
                in_block = False
                if block_lang and len(block_lines) > MAX_INLINE_LINES:
                    findings.append({
                        "skill": skill_name,
                        "severity": "WARNING",
                        "message": (
                            f"Bloque {block_lang} de {len(block_lines)} líneas "
                            f"(lín. {block_start + 1}) → mover a scripts/ o references/"
                        ),
                    })
        elif in_block:
            block_lines.append(line)

    return findings


def main() -> None:
    root = Path.cwd()
    skills = iter_skills(root)

    # Parse args
    args = set(sys.argv[1:])
    as_json = "--json" in args
    quiet = "--quiet" in args
    threshold_str = "WARN"
    argv = list(sys.argv[1:])
    for i, a in enumerate(argv):
        if a.startswith("--threshold="):
            threshold_str = a.split("=", 1)[1].upper()
        elif a == "--threshold" and i + 1 < len(argv):
            threshold_str = argv[i + 1].upper()

    threshold = 0 if threshold_str == "ERROR" else 1  # 0 = ERROR-only, 1 = WARN+

    if not skills:
        findings = [{"skill": "(root)", "severity": "WARNING", "message": "No hay skills/ en el proyecto"}]
    else:
        findings = []
        for s in skills:
            findings.extend(findings_for_skill(s))

    severity_order = {"ERROR": 0, "WARNING": 1}
    has_error = any(f["severity"] == "ERROR" for f in findings)
    has_warning = any(f["severity"] == "WARNING" for f in findings)

    if as_json:
        print(json.dumps(findings, indent=2, ensure_ascii=False))
    elif quiet:
        pass  # solo exit code
    else:
        if not findings:
            print("✓ Todas las skills cumplen la regla de modularización.")
            sys.exit(0)
        print(f"\nAuditoría de estructura de skills ({SKILLS_DIR}/)\n")
        print(f"{'Skill':<30} {'Severidad':<10} Mensaje")
        print("-" * 100)
        for f in sorted(findings, key=lambda x: (severity_order.get(x["severity"], 9), x["skill"])):
            print(f"{f['skill']:<30} {f['severity']:<10} {f['message']}")
        print()
        print(f"Total: {len(findings)} hallazgos "
              f"({sum(1 for f in findings if f['severity']=='ERROR')} ERROR, "
              f"{sum(1 for f in findings if f['severity']=='WARNING')} WARNING)")

    # Exit code según threshold
    if threshold == 0:  # ERROR-only
        sys.exit(1 if has_error else 0)
    else:  # WARN+
        sys.exit(2 if has_warning else (1 if has_error else 0))


if __name__ == "__main__":
    main()
