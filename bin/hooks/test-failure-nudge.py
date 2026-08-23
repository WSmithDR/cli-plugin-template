#!/usr/bin/env python3
"""PostToolUse: si un comando Bash corrió una suite del repo y falló, sugiere registrar
la fricción vía cpt feedback save (el ciclo growth-engine cerrando en caliente, no al
final de sesión como el Stop hook). stdout = contexto inyectado; siempre exit 0."""
import json
import re
import sys

SUITE_RE = re.compile(r"(bin/test-[\w./-]+\.sh|\bpytest\b|\bnpm (run )?test\b)")


def failed(resp: dict) -> bool:
    # ponytail: heurística sobre formas variables de tool_response; endurecer con datos reales.
    if resp.get("success") is False:
        return True
    code = resp.get("exit_code", resp.get("code"))
    return isinstance(code, int) and code != 0


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not SUITE_RE.search(cmd):
        return
    if not failed(data.get("tool_response") or {}):
        return
    plugin = "cli-plugin-template"  # este repo; generalizar con registry si crece
    print(f"Suite fallida — ¿fricción del plugin? Registrála: bin/cpt feedback save "
          f"{plugin} '<síntoma>' --status pending")


if __name__ == "__main__":
    main()
