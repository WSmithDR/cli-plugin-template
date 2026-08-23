#!/usr/bin/env python3
"""UserPromptSubmit: si el usuario expresa intención de desarrollo de plugin y está
parado en un plugin registrado (o en el propio catálogo), sugiere la skill router
plugin-dev. Grep puro — corre en TODOS los turnos, tiene que ser barato y callarse."""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

INTENT_RE = re.compile(
    r"\b(integr[áa]|agreg[áa]|sum[áe]|promov[ée]|audit[áa]|revis[áa])\b.*plugin\b"
    r"|\bqu[eé] (me )?falta\b.*plugin\b|\bplugin[- ]dev\b", re.IGNORECASE)


def data_dir() -> Path:
    override = os.environ.get("CLI_PLUGIN_TEMPLATE_DATA_DIR")
    return Path(override) if override else Path.home() / ".local/share/cli-plugin-template"


def registered_cwd() -> bool:
    try:
        registry = json.loads((data_dir() / "registry.json").read_text())
    except Exception:
        return False
    cwd = os.getcwd()
    for entry in registry:
        lp = (entry.get("local_path") or "").rstrip("/")
        if lp and cwd.startswith(lp):
            return True
    return False


def main() -> None:
    try:
        prompt = (json.load(sys.stdin).get("prompt") or "")
    except Exception:
        return
    if not INTENT_RE.search(prompt):
        return
    sentinel = Path(".catalog-root")
    if sentinel.exists() or not registered_cwd():
        return
    print("Intención de desarrollo de plugin detectada — cargá la skill router plugin-dev.")


if __name__ == "__main__":
    main()
