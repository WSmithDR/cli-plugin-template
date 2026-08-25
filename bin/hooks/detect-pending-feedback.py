#!/usr/bin/env python3
"""Stop hook (entrypoint directo, sin wrapper .sh): (1) detecta feedbacks de plugins sin
aplicar y sugiere plugin-hotpatch; (2) escanea el tramo NUEVO del transcript buscando
fricción con plugins registrados — queja del usuario O fallo observado del plugin — y
sugiere delegar la cosecha al subagente feedback-harvester, fuera del hilo principal;
(3) si el repo actual es un plugin registrado con cambios sin commitear en su infra,
sugiere promover al catálogo; (4) drift: pendientes que commits del repo ya resolvieron.

Lee el input del hook (JSON con transcript_path) por stdin. Emite JSON con
`systemMessage` (misma convención que el Stop hook de ankify) si hay algo que
reportar; nada si no.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

# ponytail: heurística por keywords — el análisis real lo hace el subagente feedback-harvester.
# Ruta absoluta resuelta de __file__, no $CLAUDE_PLUGIN_ROOT — OpenCode ejecuta este
# mismo script y no tiene esa variable.
_CPT = str(Path(__file__).resolve().parents[1] / "cpt")

FRICTION_KEYWORDS = (
    "no me gusta", "prefiero", "está mal", "esta mal", "estuvo mal",
    "no funciona", "no sirve", "incompleto", "no lo cubre", "no lo contempla",
)

# El usuario corrige mucho más seguido con imperativos de re-trabajo y juicios blandos
# que con las frases literales de arriba («corrígelo también», «le falta coherencia»).
# Todo se matchea sobre texto NORMALIZADO (minúsculas y sin tildes), así una sola forma
# cubre voseo/tuteo y las dos ortografías del usuario.
#
# Regla anti-falso-positivo: solo formas IMPERATIVAS/enclíticas, nunca infinitivos.
# «hay que corregir el import», «vamos a cambiar el path» es prosa de trabajo normal;
# «corregilo», «cambialo» es el usuario rechazando lo que se hizo.
FRICTION_PATTERNS = tuple(re.compile(p) for p in (
    # corregí / corrige / corregilo / corrígelo / corregime  (no: corregir, corrección)
    r"\bcorr[ie]g[ie](?:lo|la|los|las|me|melo)?\b",
    # rehacé / rehace / rehacelo / rehazlo / rehazme  (no: rehacer)
    r"\breha(?:ce|z)(?:lo|la|los|las|me|melo)?\b",
    # cambiá / cambia / cambialo / cámbialo / cambiaselo  (no: cambiar, cambios)
    r"\bcambia(?:lo|la|los|las|me|melo|selo)?\b",
    # arreglá / arregla / arreglalo / arréglalo  (no: arreglar, arreglo)
    r"\barregla(?:lo|la|los|las|me|melo)?\b",
    # re-trabajo explícito: hacelo de nuevo, otra vez, volvé a / vuelve a hacerlo
    r"\bde nuevo\b", r"\botra vez\b", r"\b(?:volve|volves|vuelve|vuelves) a\b",
    # juicios blandos: le falta X, no está bien, quedó raro, no cuadra, incoherente
    r"\b(?:le|les) falta\b", r"\bfalta(?:n)? (?:coherencia|contexto|consistencia)\b",
    r"\bno esta bien\b", r"\bno quedo bien\b",
    r"\bquedo (?:raro|rara|feo|fea|mal|cualquier cosa)\b",
    r"\bno cuadra\b", r"\bincoheren(?:te|tes|cia|cias)\b",
    r"\bno es (?:lo que|eso)\b", r"\bno era (?:lo que|eso)\b",
))

# Ruido que viaja DENTRO de entradas type=user pero que el usuario no tipeó:
# recordatorios de sistema, comandos slash y su stdout. Con la heurística ampliada,
# matchear contra eso haría disparar el hook en casi cualquier sesión.
_NOISE_RE = re.compile(
    r"<system-reminder>.*?</system-reminder>"
    r"|<command-(?:name|message|args)>.*?</command-(?:name|message|args)>"
    r"|<local-command-(?:stdout|stderr)>.*?</local-command-(?:stdout|stderr)>",
    re.DOTALL | re.IGNORECASE,
)


def _normalize(text: str) -> str:
    """Minúsculas y sin tildes: «corrígelo» y «corregilo» caen en la misma forma."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))

# Señal de fallo: el plugin rompió solo, sin que el usuario se queje. Se exige que el
# nombre del plugin aparezca en la MISMA línea del transcript que el marcador de error
# (una entrada jsonl = una línea), para no cosechar errores del código del usuario.
ERROR_MARKERS = (
    '"is_error":true', '"is_error": true',
    "traceback (most recent call last)", "command not found",
    "no such file or directory", "modulenotfounderror", "permission denied",
)


def _new_chunk(transcript_path: str) -> str:
    """Devuelve solo lo agregado al transcript desde el último Stop (idempotencia por offset)."""
    from gateway import harvest_offset_get, harvest_offset_set
    p = Path(transcript_path)
    if not p.is_file():
        return ""
    text = p.read_text(encoding="utf-8", errors="replace")
    start = harvest_offset_get(str(p))
    chunk = text[start:] if start <= len(text) else text
    try:
        harvest_offset_set(str(p), len(text))
    except Exception:
        pass
    return chunk


def _user_text(chunk: str) -> str:
    """Solo lo que TIPEÓ el usuario, normalizado. En el transcript los tool results
    también son entradas type=user (y traen prosa del asistente citada, stack traces,
    diffs): se descartan por `toolUseResult`/bloques no-texto, igual que las entradas
    meta. Con la heurística ampliada esa poda es lo que evita que dispare siempre."""
    out = []
    for line in chunk.splitlines():
        try:
            entry = json.loads(line)
        except Exception:
            continue
        if entry.get("type") != "user" or entry.get("isMeta") or "toolUseResult" in entry:
            continue
        content = (entry.get("message") or {}).get("content", "")
        if isinstance(content, list):
            content = " ".join(
                b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type", "text") == "text"
            )
        out.append(_NOISE_RE.sub(" ", str(content)))
    return _normalize(" ".join(out))


def _failing_plugins(chunk: str, plugins: list) -> set:
    """Plugins registrados nombrados en una línea del transcript que además trae error."""
    hits = set()
    for line in chunk.splitlines():
        low = line.lower()
        if not any(m in low for m in ERROR_MARKERS):
            continue
        hits.update(n for n in plugins if n.lower() in low)
    return hits


def _keywords() -> tuple:
    """FRICTION_KEYWORDS + frases aprendidas del léxico del store, todas normalizadas
    (el texto del usuario también lo está). Si el store falla, solo las base — el hook
    nunca se rompe por el léxico."""
    base = FRICTION_KEYWORDS
    try:
        from gateway import friction_lexicon
        base = base + tuple(friction_lexicon())
    except Exception:
        pass
    return tuple(dict.fromkeys(_normalize(k) for k in base))


def _has_friction(user_text: str) -> bool:
    """user_text ya viene normalizado por _user_text()."""
    if not user_text:
        return False
    return (any(k in user_text for k in _keywords())
            or any(p.search(user_text) for p in FRICTION_PATTERNS))


def _friction_message(transcript_path: str) -> str:
    if not transcript_path:
        return ""
    try:
        from gateway import registry_list
        plugins = [r.get("name", "") for r in registry_list() if r.get("name")]
    except Exception:
        return ""
    if not plugins:
        return ""
    chunk = _new_chunk(transcript_path)
    if not chunk:
        return ""
    lower = chunk.lower()
    mentioned = [n for n in plugins if n.lower() in lower]
    complained = bool(mentioned) and _has_friction(_user_text(chunk))
    failing = _failing_plugins(chunk, plugins)
    if not complained and not failing:
        return ""
    involved = sorted(set(mentioned) | failing)
    why = "user friction + observed failures" if complained and failing else (
        "user friction" if complained else f"observed failures in: {', '.join(sorted(failing))}")
    return (f"POSSIBLE PLUGIN FRICTION this session ({why}; plugins: {', '.join(involved)}). "
            f"Dispatch the harvest OUTSIDE the main thread: call the Agent tool with "
            f"subagent_type \"cli-plugin-template:feedback-harvester\" and "
            f"run_in_background, passing the transcript path {transcript_path}. It saves "
            f"feedbacks via cpt and replies with a one-line summary.")


def _promote_message() -> str:
    """Cambios sin commitear en la infra de un plugin registrado (hooks, bin, agents, CI,
    SKILL.md) — no en su dominio — son candidatos a promoverse al catálogo. Avisa una vez
    por set de archivos: si seguís tocando los mismos, no vuelve a molestar."""
    import subprocess
    import zlib
    try:
        from gateway import harvest_offset_get, harvest_offset_set, registry_list
        cwd = Path.cwd().resolve()
        plugin = next((r for r in registry_list()
                       if r.get("local_path") and Path(r["local_path"]).resolve() == cwd), None)
        if not plugin:
            return ""
        out = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=cwd,
                             capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return ""
    files = sorted(f for f in out.split()
                   if f.startswith(("hooks/", "bin/", "agents/", ".github/"))
                   or (f.startswith("skills/") and f.endswith("SKILL.md")))
    if not files:
        return ""
    # ponytail: reusa el store de offsets como state key/valor genérico en vez de una tabla nueva.
    key = f"promote:{plugin['name']}"
    stamp = zlib.crc32("\n".join(files).encode())
    if harvest_offset_get(key) == stamp:
        return ""
    try:
        harvest_offset_set(key, stamp)
    except Exception:
        pass
    return (f"POSSIBLE CATALOG PROMOTION: infra changes in {plugin['name']} "
            f"({', '.join(files[:4])}{'...' if len(files) > 4 else ''}). If any of it is "
            f"reusable by ANY plugin (not this plugin's domain), call "
            f"Skill(\"cli-plugin-template:plugin-promote\") to move it to the catalog.")


def _drift_message() -> str:
    """Feedbacks pendientes que commits del repo ya resolvieron: el store quedó atrás.
    Mismo mecanismo de dedupe que _promote_message: un stamp por conjunto de hallazgos,
    así no repite mientras sea el mismo set."""
    found = []
    try:
        from gateway import feedback_audit, harvest_offset_get, harvest_offset_set, registry_list
        cwd = Path.cwd().resolve()
        plugin = next((r for r in registry_list()
                       if r.get("local_path")
                       and cwd.is_relative_to(Path(r["local_path"]).resolve())), None)
        if not plugin:
            return ""
        found = feedback_audit(plugin["name"])
        if not found:
            return ""
        import zlib
        stamp = zlib.crc32(",".join(sorted(f["slug"] for f in found)).encode())
        key = f"drift:{plugin['name']}"
        if harvest_offset_get(key) == stamp:
            return ""
        harvest_offset_set(key, stamp)
    except Exception:
        return ""
    items = "; ".join(f"{f['slug']} ({','.join(f['commits'])})" for f in found[:3])
    suffix = "..." if len(found) > 3 else ""
    return (f"FEEDBACK DRIFT in {plugin['name']}: {len(found)} feedback(s) still marked "
            f"pending look ALREADY FIXED by commits: [{items}{suffix}]. Run "
            f"'python3 {_CPT} feedback audit {plugin['name']}', "
            f"verify each, close with 'cpt feedback apply' (or discard if obsolete).")


def main() -> int:
    try:
        transcript_path = str(json.load(sys.stdin).get("transcript_path", ""))
    except Exception:
        transcript_path = ""
    msgs = []

    try:
        from gateway import feedback_list
        pending = feedback_list(pending_only=True)
    except Exception:
        pending = []

    if pending:
        by_plugin = {}
        for item in pending:
            by_plugin.setdefault(item.split("/", 1)[0], []).append(item)
        pw = max(len(p) for p in by_plugin)
        filas = "\n".join(f"   • {p:<{pw}} ({len(v)})" for p, v in sorted(by_plugin.items()))
        items = "\n".join(f"   {i}. {s}" for i, s in enumerate(pending[:3], 1))
        resto = len(pending) - 3
        if resto > 0:
            items += f"\n   … y {resto} más"
        msgs.append(
            f"◆ CLI-PLUGIN-TEMPLATE — PENDING PLUGIN FEEDBACK\n"
            f"   {len(pending)} sin aplicar en {len(by_plugin)} plugin(s)\n\n"
            f"{filas}\n\n"
            f"{items}\n\n"
            f"  ▸ procesalos con la skill cli-plugin-template:plugin-hotpatch\n"
            f"  ▸ detalle completo: python3 {_CPT} feedback list --pending")

    friction = _friction_message(transcript_path)
    if friction:
        msgs.append(friction)

    promote = _promote_message()
    if promote:
        msgs.append(promote)

    drift = _drift_message()
    if drift:
        msgs.append(drift)

    if msgs:
        print(json.dumps({"systemMessage": " | ".join(msgs)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
