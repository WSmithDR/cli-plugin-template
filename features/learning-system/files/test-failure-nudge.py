#!/usr/bin/env python3
"""PostToolUseFailure (Bash): si una suite falló, sugiere registrar la fricción Y,
si el output contradice un aprendizaje vigente, corregir código y aprendizaje juntos.

Extensión del hook de fallos de growth-engine: la única pieza nueva es
_check_learnings() — integrarla en tu hook existente o usar este como base.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

SUITE_RE = re.compile(r"(bin/test-[\w./-]+\.sh|\bpytest\b|\bnpm (run )?test\b)")
EXIT_CODE_RE = re.compile(r"^Exit code ([1-9]\d*)")


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _check_learnings(error_text: str, plugin: str) -> str:
    """Si el output menciona 2+ keywords del body de un aprendizaje, avisa.
    ponytail: matchea contra el BODY, no contra el slug."""
    try:
        from learning_store import learning_list, learning_load
        slugs = learning_list(plugin=plugin)
        if not slugs:
            return ""
        norm_error = _normalize(error_text)
        for ref in slugs:
            parts = ref.split("/", 1)
            if len(parts) != 2:
                continue
            scope, slug = parts
            body = learning_load(scope, slug)
            kw = list(dict.fromkeys(w[:8] for w in re.findall(r"\b\w{4,}\b", _normalize(body))))[:10]
            if sum(1 for k in kw if k in norm_error) >= 2:
                return (f"\nEsta falla puede contradecir el aprendizaje `{slug}`. "
                        f"Corregí el código Y el aprendizaje juntos.")
        return ""
    except Exception:
        return ""


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not SUITE_RE.search(cmd):
        return
    # ponytail: la doc de CC fija la primera línea de `error` como "Exit code N"
    error = data.get("error") or ""
    if not EXIT_CODE_RE.match(error):
        return
    plugin = "miplugin"  # ← adaptar (o resolver con registry)
    msg = (f"Suite fallida — ¿fricción del plugin? Registrala: "
           f"python3 <tu-cli> feedback save {plugin} '<síntoma>' --status pending")
    hint = _check_learnings(error, plugin)
    print(msg + hint)


if __name__ == "__main__":
    main()
