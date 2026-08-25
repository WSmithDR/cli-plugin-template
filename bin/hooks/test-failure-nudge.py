#!/usr/bin/env python3
"""PostToolUseFailure: si un comando Bash corrió una suite del repo y terminó con
exit code distinto de cero, (1) sugiere registrar la fricción vía cpt feedback save
y (2) si el output contradice un aprendizaje vigente, sugiere corregirlo también.
stdout = contexto inyectado; siempre exit 0."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

SUITE_RE = re.compile(r"(bin/test-[\w./-]+\.sh|\bpytest\b|\bnpm (run )?test\b)")
EXIT_CODE_RE = re.compile(r"^Exit code ([1-9]\d*)")


def _normalize(text: str) -> str:
    import unicodedata
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _check_learnings(error_text: str, plugin: str) -> str:
    """Si el output de fallo menciona keywords de algun aprendizaje, devuelve un
    mensaje sugiriendo corregirlo. Si no, cadena vacia."""
    try:
        from gateway import learning_list, learning_load
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
            words = re.findall(r"\b\w{4,}\b", _normalize(body))
            kw = list(dict.fromkeys(w[:8] for w in words))[:10]
            hits = sum(1 for k in kw if k in norm_error)
            if hits >= 2:
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
    if not EXIT_CODE_RE.match(data.get("error") or ""):
        return
    plugin = "cli-plugin-template"  # este repo; generalizar con registry si crece
    msg = (f"Suite fallida — ¿fricción del plugin? Registrala: bin/cpt feedback save "
           f"{plugin} '<síntoma>' --status pending")
    learnings_hint = _check_learnings(data.get("error") or "", plugin)
    if learnings_hint:
        msg += learnings_hint
    print(msg)


if __name__ == "__main__":
    main()
