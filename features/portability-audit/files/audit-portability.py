#!/usr/bin/env python3
"""Audita un plugin contra patrones que rompen portabilidad y agnosticismo.

Escanea un directorio de plugin (por defecto la cwd) y reporta hallazgos que
hacen que el plugin solo funcione "en la máquina del autor" o "solo en Claude
Code". Es determinista: mismo árbol de archivos → mismo reporte (encaja con el
principio de `bundled-scripts`). El LLM solo interpreta y prioriza la salida.

Categorías de hallazgo (severidad):
  CRITICAL  absolute-path     ruta absoluta atada a una máquina (/home/x, /Users/x, C:\\…)
  CRITICAL  possible-secret   credencial/clave hardcodeada
  WARNING   unrooted-ref      skill/command referencia un dir del plugin sin ${CLAUDE_PLUGIN_ROOT}
  WARNING   claude-only-path  acopla a Claude Code con un path .claude/ hardcodeado
  WARNING   model-inherit     `model: inherit` en frontmatter (rompe OpenCode y otros CLIs)
  INFO      portable-shebang  shebang/intérprete no portable (python en vez de python3, etc.)

Excluir falsos positivos (docs con ejemplos, fixtures, esqueletos):
  - Archivo `.portabilityignore` en la raíz escaneada: un glob por línea
    (estilo .gitignore, `#` comenta). Ej: `docs/**`, `tests/fixtures/**`.
  - Marcador inline: cualquier línea que contenga el literal `audit-ignore`
    se omite (como `# noqa`).

Uso:
    audit-portability.py [RUTA] [--json] [--quiet]

Salida:
    Reporte agrupado por severidad. Exit 1 si hay hallazgos CRITICAL (para CI),
    exit 0 en caso contrario. WARNING/INFO no cambian el exit code.
    Con --quiet, no imprime nada si no hay CRITICAL (ideal para pre-commit).
"""
from __future__ import annotations

import fnmatch
import json
import re
import sys
from pathlib import Path

IGNORE_FILE = ".portabilityignore"
IGNORE_MARKER = "audit-ignore"

# Directorios que nunca se escanean (ruido, no son código del plugin).
SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__",
    "vendor", ".next", "target", "coverage", ".pytest_cache", ".mypy_cache",
}
# Solo se escanean estos tipos de archivo de texto.
TEXT_SUFFIXES = {
    ".md", ".py", ".sh", ".bash", ".js", ".mjs", ".cjs", ".ts", ".json",
    ".yml", ".yaml", ".toml", ".txt", ".cfg", ".ini", "",
}
# Dirs de primer nivel del plugin que, referenciados desde una skill/command,
# deberían ir prefijados con ${CLAUDE_PLUGIN_ROOT} (si no, resuelven contra la
# cwd del usuario, no contra el plugin instalado).
PLUGIN_DIRS = ("features", "skills", "commands", "config", "bin", "scripts",
               "hooks", "agents", "lib", "assets", "templates")

# --- Patrones ---------------------------------------------------------------

# Rutas absolutas atadas a una máquina concreta. Se excluyen shebangs / paths
# de sistema legítimos (se filtran abajo por contexto).
ABSOLUTE_PATH = re.compile(
    r"""(?P<path>
        /home/[A-Za-z0-9._-]+        # Linux home
      | /Users/[A-Za-z0-9._-]+       # macOS home
      | /root/[A-Za-z0-9._-]+        # root home
      | /mnt/[a-z]/[A-Za-z0-9._/-]+  # WSL mount
      | [A-Za-z]:\\\\[A-Za-z0-9._\\\\ -]+  # Windows drive
    )""",
    re.VERBOSE,
)
# Shebangs e intérpretes de sistema que NO son hallazgos (son portables).
SHEBANG_OK = re.compile(r"^#!\s*/usr/bin/env\s")

SECRET = re.compile(
    r"""(?ix)
    ( aws_secret_access_key\s*[:=]
    | -----BEGIN\ (?:RSA\ |EC\ |OPENSSH\ |DSA\ |PGP\ )?PRIVATE\ KEY-----
    | \bAKIA[0-9A-Z]{16}\b                       # AWS access key id
    | \bgh[pousr]_[A-Za-z0-9]{30,}\b             # GitHub token
    | \bxox[baprs]-[A-Za-z0-9-]{10,}\b           # Slack token
    | \bsk-[A-Za-z0-9]{20,}\b                    # OpenAI-style key
    | (?:api[_-]?key|secret|token|password|passwd)\s*[:=]\s*["'][^"'\s]{12,}["']
    )""",
)
# Asignaciones que parecen secretos pero son placeholders → no son hallazgo.
SECRET_PLACEHOLDER = re.compile(
    r"(?i)(your[_-]?|example|placeholder|dummy|changeme|xxxx|<[^>]+>|\$\{?[A-Z_]+\}?|\benv\b|process\.env|os\.environ)"
)

MODEL_INHERIT = re.compile(r"^\s*model:\s*inherit\s*$")
CLAUDE_ONLY_PATH = re.compile(r"(?<![\w/.])\.claude/(?!plugin)[A-Za-z0-9._/-]+")
# Intérprete no portable: python/python2 directo, o shebang absoluto a python.
NON_PORTABLE_PY = re.compile(
    r"(^#!\s*/usr/bin/python\b)|(?<![\w.-])python2?(?![\w.-])(?!3)"
)


def is_text(path: Path) -> bool:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    try:
        if path.stat().st_size > 1_000_000:  # >1MB: probablemente no es fuente
            return False
    except OSError:
        return False
    return True


def load_ignore(root: Path) -> list[str]:
    f = root / IGNORE_FILE
    if not f.exists():
        return []
    out = []
    for raw in f.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def is_ignored(rel_posix: str, patterns: list[str]) -> bool:
    for pat in patterns:
        cands = {pat}
        if pat.endswith("/"):
            cands.add(pat + "**")
        if pat.endswith("/**"):
            cands.add(pat[:-3])  # el dir en sí
        for c in cands:
            if fnmatch.fnmatch(rel_posix, c):
                return True
        base = pat.rstrip("/").removesuffix("/**")
        if rel_posix == base or rel_posix.startswith(base + "/"):
            return True
    return False


def walk(root: Path, ignore: list[str]):
    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not (path.is_file() and is_text(path)):
            continue
        rel = path.relative_to(root).as_posix()
        if rel == IGNORE_FILE or is_ignored(rel, ignore):
            continue
        yield path


def is_skill_or_command(rel: Path) -> bool:
    parts = rel.parts
    return (
        (len(parts) >= 1 and parts[0] in ("skills", "commands"))
        or rel.name in ("SKILL.md",)
    )


def scan_file(path: Path, root: Path) -> list[dict]:
    rel = path.relative_to(root)
    findings: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return findings

    skill_ctx = is_skill_or_command(rel)
    for n, line in enumerate(text.splitlines(), 1):
        if IGNORE_MARKER in line:
            continue
        stripped = line.strip()

        # absolute-path (excluye shebangs env y comentarios de doc que citan el patrón)
        if not SHEBANG_OK.match(stripped):
            for m in ABSOLUTE_PATH.finditer(line):
                findings.append(_f("CRITICAL", "absolute-path", rel, n,
                                   m.group("path"),
                                   "Reemplazá por ${CLAUDE_PLUGIN_ROOT}, una ruta relativa, o $HOME."))

        # possible-secret (descarta placeholders y referencias a env vars)
        if SECRET.search(line) and not SECRET_PLACEHOLDER.search(line):
            findings.append(_f("CRITICAL", "possible-secret", rel, n, stripped[:80],
                               "Leé el secreto desde una env var; nunca lo hardcodees en el repo."))

        # model: inherit (rompe OpenCode y otros)
        if MODEL_INHERIT.match(line):
            findings.append(_f("WARNING", "model-inherit", rel, n, stripped,
                               "Omití el campo `model:`; `inherit` es exclusivo de Claude Code."))

        # claude-only-path
        for m in CLAUDE_ONLY_PATH.finditer(line):
            findings.append(_f("WARNING", "claude-only-path", rel, n, m.group(0),
                               "Path acoplado a Claude Code; ver feature multi-cli-compat para hacerlo agnóstico."))

        # portable-shebang / intérprete (solo shebangs o líneas que parecen comando)
        if (NON_PORTABLE_PY.search(line) and "python3" not in line
                and (stripped.startswith("#!") or _looks_like_command(line))):
            findings.append(_f("INFO", "portable-shebang", rel, n, stripped[:80],
                               "Usá `python3` (o el shim de hook-python-bootstrap) en vez de `python`/`python2`."))

        # unrooted-ref: skill/command que referencia un dir del plugin sin rootear
        if skill_ctx:
            for d in PLUGIN_DIRS:
                # comando que toca "<dir>/..." al inicio de un token, sin ${CLAUDE_PLUGIN_ROOT} ni ./ relativo claro
                pat = re.compile(rf"(?<![\w/.$]){d}/")
                if pat.search(line) and "CLAUDE_PLUGIN_ROOT" not in line and _looks_like_command(line):
                    findings.append(_f("WARNING", "unrooted-ref", rel, n,
                                       _excerpt(line, f"{d}/"),
                                       f"Prefijá con ${{CLAUDE_PLUGIN_ROOT}}/: resuelve contra el plugin, no la cwd del usuario."))
                    break
    return findings


_CMD_WORD = r"(cat|ls|bash|sh|python3?|node|source|read|grep|find|head|tail|cd|cp|mv|rm)"


def _looks_like_command(line: str) -> bool:
    """Heurística: la línea parece una invocación de shell, no prosa.

    Requiere un verbo de comando al inicio de la línea o dentro de un span de
    backticks; un backtick suelto (código inline en prosa) no alcanza.
    """
    if re.search(rf"^\s*{_CMD_WORD}\s", line):
        return True
    return any(re.match(rf"\s*{_CMD_WORD}\s", span)
               for span in re.findall(r"`([^`]*)`", line))


def _excerpt(line: str, needle: str) -> str:
    i = line.find(needle)
    start = max(0, i - 12)
    return line[start:i + len(needle) + 28].strip()


def _f(sev, kind, rel, line, snippet, hint) -> dict:
    return {"severity": sev, "kind": kind, "file": str(rel),
            "line": line, "snippet": snippet, "hint": hint}


ORDER = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
ICON = {"CRITICAL": "✗", "WARNING": "⚠", "INFO": "·"}


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    as_json = "--json" in argv
    quiet = "--quiet" in argv
    root = Path(args[0]).resolve() if args else Path.cwd()
    if not root.is_dir():
        print(f"✗ no es un directorio: {root}", file=sys.stderr)
        return 2

    ignore = load_ignore(root)
    findings: list[dict] = []
    for path in walk(root, ignore):
        findings.extend(scan_file(path, root))

    findings.sort(key=lambda f: (ORDER[f["severity"]], f["file"], f["line"]))

    if as_json:
        print(json.dumps(findings, ensure_ascii=False, indent=2))
        return 1 if any(f["severity"] == "CRITICAL" for f in findings) else 0

    counts = {s: sum(1 for f in findings if f["severity"] == s)
              for s in ("CRITICAL", "WARNING", "INFO")}
    has_critical = counts["CRITICAL"] > 0
    if quiet and not has_critical:
        return 0
    if not findings:
        print(f"✓ Auditoría de portabilidad — sin hallazgos en {root.name}/")
        return 0

    print(f"Auditoría de portabilidad — {root.name}/  "
          f"(CRITICAL: {counts['CRITICAL']}  WARNING: {counts['WARNING']}  INFO: {counts['INFO']})\n")
    last_sev = None
    for f in findings:
        if f["severity"] != last_sev:
            print(f"\n{f['severity']}")
            last_sev = f["severity"]
        print(f"  {ICON[f['severity']]} [{f['kind']}] {f['file']}:{f['line']}")
        print(f"      {f['snippet']}")
        print(f"      → {f['hint']}")
    return 1 if counts["CRITICAL"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
