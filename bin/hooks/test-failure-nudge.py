#!/usr/bin/env python3
"""PostToolUseFailure: si un comando Bash corrió una suite del repo y terminó con
exit code distinto de cero, sugiere registrar la fricción vía cpt feedback save
(el ciclo growth-engine cerrando en caliente, no al final de sesión como el Stop
hook). stdout = contexto inyectado; siempre exit 0."""
import json
import re
import sys

SUITE_RE = re.compile(r"(bin/test-[\w./-]+\.sh|\bpytest\b|\bnpm (run )?test\b)")
EXIT_CODE_RE = re.compile(r"^Exit code ([1-9]\d*)")


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not SUITE_RE.search(cmd):
        return
    # ponytail: la doc de CC fija la primera línea de `error` como "Exit code N";
    # si ese formato deja de ser estable, este es el único punto a ajustar.
    if not EXIT_CODE_RE.match(data.get("error") or ""):
        return
    plugin = "cli-plugin-template"  # este repo; generalizar con registry si crece
    print(f"Suite fallida — ¿fricción del plugin? Registrála: bin/cpt feedback save "
          f"{plugin} '<síntoma>' --status pending")


if __name__ == "__main__":
    main()
