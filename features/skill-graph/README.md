# Feature: skill-graph

## Qué hace

Genera, **del código**, el grafo de delegación entre las skills de un plugin (quién invoca
a quién) más un inventario, y lo mantiene fresco automáticamente:

- `docs/SKILL-GRAPH.md` — diagrama Mermaid + tabla de **reutilización** (skills delegadas por
  ≥2 orquestadoras) + **skills grandes** (>250 líneas, candidatas a extraer) + huérfanas.
- `README.md` — el diagrama y/o el inventario, inyectados entre marcadores.

Lo regenera un git **pre-commit** y hace `git add`, así nunca se desincroniza del código.

## Por qué

En un plugin con muchas skills, el diagrama de arquitectura escrito a mano **siempre miente**:
alguien agrega una skill, mueve una delegación, y la doc queda vieja. Acá el grafo se **parsea**
de las referencias reales (`Read('skills/x/SKILL.md')`, `Skill('y')`, y `skill:` en el
frontmatter de archivos de routing), no de la memoria de quien edita. El inventario sale del
`name`/`description`/`disable-model-invocation` de cada `SKILL.md`.

Sirve además como herramienta de **modularización**: la tabla de reutilización muestra qué skills
son compartidas; la de "skills grandes" marca orquestadoras gordas para extraer en privadas. Es
el complemento determinístico de un análisis semántico (ver `discipline-skills` / una skill de
"modularize" que detecte duplicados — eso lo razona el LLM, esto lo mide el script).

Supone dos convenciones (las de un plugin con skills modulares):
- las skills viven en `skills/<modulo>/<nombre>/SKILL.md` (o `skills/<nombre>/SKILL.md`);
- las orquestadoras delegan en sub-skills **privadas** con `Read('skills/.../SKILL.md')` y en
  públicas con `Skill('nombre')`; las privadas se marcan con `disable-model-invocation: true`.

## Integración

1. Copiá el script:
   ```
   files/skill-graph.py → bin/dev/skill-graph.py
   ```
2. Adaptá lo específico de tu plugin dentro del script:
   - `_MODULE_TITLES` — títulos de los grupos del inventario (por módulo). Default genérico.
   - Si **no** usás archivos de routing con `skill:` en el frontmatter, ignoralo: el bloque no matchea nada.
3. Agregá los marcadores en `README.md` donde quieras el diagrama y/o el inventario:
   ```markdown
   ## Arquitectura

   <!-- SKILL-GRAPH:START -->
   <!-- SKILL-GRAPH:END -->

   ### Inventario

   <!-- SKILL-LIST:START -->
   <!-- SKILL-LIST:END -->
   ```
   (Ambas secciones son opcionales — poné solo los marcadores que quieras.)
4. Generá la primera vez:
   ```bash
   python3 bin/dev/skill-graph.py
   ```
5. Cableá la regeneración en el `pre-commit` (feature [`git-hooks`](../git-hooks/README.md)),
   antes del `exit 0`:
   ```bash
   echo "--- Regenerando skill graph..."
   python3 "$PLUGIN_ROOT/bin/dev/skill-graph.py" "$PLUGIN_ROOT" \
     && git add "$PLUGIN_ROOT/docs/SKILL-GRAPH.md" "$PLUGIN_ROOT/README.md" 2>/dev/null \
     || echo "--- ⚠ skill-graph falló (no bloquea el commit)."
   ```
   Opcional: si `skills/` cambió en el commit, recordá correr tu análisis de modularización:
   ```bash
   if git diff --cached --name-only | grep -q '^skills/'; then
     echo "--- ⚠ skills/ cambió → revisá duplicados / orquestadoras gordas (ver SKILL-GRAPH)."
   fi
   ```

## Tests

```bash
# Genera sin error y produce el diagrama:
python3 bin/dev/skill-graph.py

# Modo CI: falla (exit 1) si el README/docs quedaron desactualizados respecto al código:
python3 bin/dev/skill-graph.py --check
```
Verificá que `docs/SKILL-GRAPH.md` y la sección del `README` muestren tus skills y las aristas
reales. Si agregás una delegación nueva y corrés `--check` sin regenerar, debe fallar.

## Changelog

- **1.0.0** — versión inicial migrada desde `ankify` (grafo + inventario + reutilización +
  skills grandes, inyectados en README/docs por el pre-commit).
