#!/usr/bin/env python3
"""Genera un grafo de delegación entre skills + inventario, DETERMINÍSTICO.

Parsea las referencias reales entre skills (`Read('skills/x/SKILL.md')`,
`Skill('y')`, y el campo `skill:` del frontmatter de archivos de routing) y produce:
  - docs/SKILL-GRAPH.md : diagrama Mermaid + reutilización + skills grandes.
  - README.md           : el diagrama y/o el inventario, inyectados entre marcadores
                          <!-- SKILL-GRAPH:START/END --> y <!-- SKILL-LIST:START/END -->.

Como sale del código (no de que alguien lo actualice a mano), el diagrama nunca miente.
Pensado para correr desde un git pre-commit (regenera + `git add`).

Uso:
  skill-graph.py [PLUGIN_ROOT]            # regenera docs + README
  skill-graph.py [PLUGIN_ROOT] --check    # exit 1 si quedaron desactualizados (CI)

Adaptar al integrar: `_MODULE_TITLES` (títulos de los grupos del inventario) y, si tu
plugin no usa archivos de routing con `skill:` en el frontmatter, el bloque de escenarios
es inofensivo (no matchea nada).
"""
import re
import sys
from pathlib import Path

_args = [a for a in sys.argv[1:] if not a.startswith("--")]
CHECK = "--check" in sys.argv
ROOT = Path(_args[0]).resolve() if _args else Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"
OUT = ROOT / "docs" / "SKILL-GRAPH.md"
README = ROOT / "README.md"
_MARK_START = "<!-- SKILL-GRAPH:START -->"
_MARK_END = "<!-- SKILL-GRAPH:END -->"
_LIST_START = "<!-- SKILL-LIST:START -->"
_LIST_END = "<!-- SKILL-LIST:END -->"

_READ_REF = re.compile(r"Read\(\s*['\"]skills/([^'\"]+)/SKILL\.md['\"]\s*\)")
_SKILL_REF = re.compile(r"[Ss]kill\(\s*['\"]([^'\"]+)['\"]\s*\)")
_NAME = re.compile(r"^name:\s*(\S+)", re.M)
_FM_SKILL = re.compile(r"^skill:\s*(\S+)", re.M)
_DESC = re.compile(r'^description:\s*["\']?(.+?)["\']?\s*$', re.M)

# Títulos de los grupos del inventario (por módulo = primer segmento del path).
# `core` = skills en la raíz de skills/. Adaptá a los módulos de tu plugin.
_MODULE_TITLES = {"core": "Skills raíz (entry points)"}


def _node_id(path: str) -> str:
    return path.replace("/", "_").replace("-", "_")


def _skill_dirs():
    """relpath -> {name, private, desc, lines} para cada skills/**/SKILL.md."""
    out = {}
    for md in sorted(SKILLS.rglob("SKILL.md")):
        rel = md.parent.relative_to(SKILLS).as_posix()
        head = md.read_text(encoding="utf-8")
        name = (_NAME.search(head) or [None, rel])[1]
        desc = _DESC.search(head)
        out[rel] = {
            "name": name,
            "private": "disable-model-invocation: true" in head,
            "desc": (desc.group(1) if desc else ""),
            "lines": len(head.splitlines()),
        }
    return out


def _edges(dirs):
    """(origen_rel, destino_rel) por cada delegación. Origen = skill que contiene la ref."""
    name_to_rel = {v["name"]: k for k, v in dirs.items()}
    edges = set()

    def add(src, target_path):
        if target_path in dirs:
            edges.add((src, target_path))

    for md in sorted(SKILLS.rglob("*.md")):
        # El "dueño" de las refs es el directorio-skill que contiene este .md
        # (archivos auxiliares como scenarios/*.md cuentan para su skill padre).
        owner = None
        p = md.parent
        while p != SKILLS and p != p.parent:
            if (p / "SKILL.md").exists():
                owner = p.relative_to(SKILLS).as_posix()
                break
            p = p.parent
        if owner is None:
            continue
        text = md.read_text(encoding="utf-8")

        def _negated(pos):
            # Ignora refs dentro de advertencias ("NUNCA usar Skill('x')", "NO invocar…")
            a, b = text.rfind("\n", 0, pos), text.find("\n", pos)
            ln = text[(a + 1 if a >= 0 else 0):(b if b >= 0 else len(text))].lower()
            return any(k in ln for k in ("nunca", "no usar", "no invocar", "never", "❌"))

        for m in _READ_REF.finditer(text):
            if not _negated(m.start()):
                add(owner, m.group(1))
        for m in _SKILL_REF.finditer(text):
            if _negated(m.start()):
                continue
            ref = m.group(1)
            if "/" in ref:
                add(owner, ref)
            elif ref in name_to_rel:
                add(owner, name_to_rel[ref])
        # Archivos de routing con `skill:` en el frontmatter → owner delega ahí.
        fm = _FM_SKILL.search(text)
        if fm and md.name != "SKILL.md":
            tgt = fm.group(1)
            tgt_rel = tgt if tgt in dirs else name_to_rel.get(tgt)
            if tgt_rel:
                add(owner, tgt_rel)
    return sorted(edges)


def mermaid_block(dirs, edges):
    out = ["```mermaid", "flowchart TD"]
    for rel, meta in sorted(dirs.items()):
        nid = _node_id(rel)
        if meta["private"]:
            out.append(f'  {nid}["{rel}"]:::priv')
        else:
            out.append(f'  {nid}(["{rel}"]):::pub')
    for s, t in edges:
        out.append(f"  {_node_id(s)} --> {_node_id(t)}")
    out.append("  classDef pub fill:#1f6feb,color:#fff,stroke:#1f6feb;")
    out.append("  classDef priv fill:#eee,color:#333,stroke:#999;")
    out.append("```")
    return "\n".join(out)


def skill_table(dirs):
    """Inventario agrupado por módulo (primer segmento del path), del frontmatter."""
    groups = {}
    for rel, m in dirs.items():
        mod = rel.split("/")[0] if "/" in rel else "core"
        groups.setdefault(mod, []).append((rel, m))
    out = ["> 🟦 invocable (en el registry) · ⬜ privada (`disable-model-invocation`, se carga "
           "on-demand con `Read`). Generado por `bin/dev/skill-graph.py`.\n"]
    ordered = (["core"] if "core" in groups else []) + sorted(g for g in groups if g != "core")
    for mod in ordered:
        out.append(f"**{_MODULE_TITLES.get(mod, f'`{mod}/`')}**\n")
        out.append("| Skill | | Descripción |")
        out.append("|---|---|---|")
        for rel, m in sorted(groups[mod]):
            badge = "⬜" if m["private"] else "🟦"
            desc = m["desc"].replace("|", "\\|")
            if len(desc) > 130:
                desc = desc[:127].rstrip() + "…"
            out.append(f"| `{rel}` | {badge} | {desc} |")
        out.append("")
    return "\n".join(out)


def render(dirs, edges):
    indeg = {}
    for _, t in edges:
        indeg[t] = indeg.get(t, 0) + 1
    out = ["# Skill graph — grafo de delegación\n",
           "> Generado por `bin/dev/skill-graph.py` (no editar a mano). "
           "Refleja las refs reales `Read('skills/…')` / `Skill('…')`.\n",
           mermaid_block(dirs, edges) + "\n"]

    reused = sorted(((indeg[r], r) for r in indeg if indeg[r] >= 2), reverse=True)
    out.append("## Reutilización (delegada por ≥2 skills)\n")
    if reused:
        out.append("| Skill | Veces |\n|---|---|")
        out += [f"| `{r}` | {n} |" for n, r in reused]
    else:
        out.append("_(ninguna)_")
    out.append("")

    orphans = sorted(r for r in dirs if r not in indeg)
    out.append("## Sin delegación entrante (entry points o huérfanas)\n")
    out.append(", ".join(f"`{o}`" for o in orphans) or "_(ninguna)_")
    out.append("")

    fat = sorted(((m["lines"], r) for r, m in dirs.items() if m["lines"] > 250), reverse=True)
    out.append("## Skills grandes (>250 líneas — candidatas a extraer)\n")
    if fat:
        out.append("| Skill | Líneas |\n|---|---|")
        out += [f"| `{r}` | {n} |" for n, r in fat]
    else:
        out.append("_(ninguna)_")
    out.append("")
    return "\n".join(out) + "\n"


def _inject(txt, start, end, block):
    if start not in txt or end not in txt:
        return txt
    return txt.split(start)[0] + f"{start}\n\n{block}\n\n{end}" + txt.split(end, 1)[1]


def _readme_injected(dirs, edges):
    if not README.exists():
        return None
    txt = README.read_text(encoding="utf-8")
    if not any(m in txt for m in (_MARK_START, _LIST_START)):
        return None
    txt = _inject(txt, _MARK_START, _MARK_END, mermaid_block(dirs, edges))
    txt = _inject(txt, _LIST_START, _LIST_END, skill_table(dirs))
    return txt


def main():
    if not SKILLS.is_dir():
        print(f"no existe {SKILLS} — nada que graficar")
        return
    dirs = _skill_dirs()
    edges = _edges(dirs)
    content = render(dirs, edges)
    readme_new = _readme_injected(dirs, edges)
    if CHECK:
        stale = []
        if (OUT.read_text(encoding="utf-8") if OUT.exists() else "") != content:
            stale.append("docs/SKILL-GRAPH.md")
        if readme_new is not None and README.read_text(encoding="utf-8") != readme_new:
            stale.append("README.md")
        if stale:
            print("desactualizado:", ", ".join(stale), "— corré: python3 bin/dev/skill-graph.py")
            sys.exit(1)
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(content, encoding="utf-8")
    msg = f"escrito: {OUT.relative_to(ROOT)}"
    if readme_new is not None:
        README.write_text(readme_new, encoding="utf-8")
        msg += " + README.md"
    print(f"{msg}  ({len(dirs)} skills, {len(edges)} edges)")


if __name__ == "__main__":
    main()
