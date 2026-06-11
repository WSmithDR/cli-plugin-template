# Diseño: meta-plugin de desarrollo de plugins

**Fecha**: 2026-06-11
**Estado**: aprobado, pendiente de plan de implementación

## Problema

El catálogo `cli-plugin-template` es hoy un repo pasivo: hay que leerlo a mano. Queremos
que, instalado en cualquier proyecto de plugin, **entregue las pautas de desarrollo en el
momento justo** — descubrir features faltantes, integrarlos, y promover mejoras de vuelta.

## Concepto

El repo se vuelve **a la vez el catálogo y un plugin instalable**. Al instalarlo en otro
proyecto, sus skills leen el catálogo localmente vía `${CLAUDE_PLUGIN_ROOT}/features/` — el
plugin **empaqueta** los 32 features, no los descarga. Es dogfooding: usa sus propios
patrones (`entry-point-router`, `claude-code-hooks`, `project-config`, `health-check`,
`skill-authoring`).

## Activación

Modelo: **proactivo gentil + on-demand**.

- **On-demand** (núcleo): skills y un comando que el usuario invoca.
- **Proactivo gentil**: un hook `SessionStart` que corre **una sola vez por proyecto** y
  sugiere una auditoría, sin bloquear.

## Componentes — skills

Siguiendo `entry-point-router`: un skill de entrada que enruta a 4 capacidades.

| Skill | Responsabilidad |
|---|---|
| `plugin-dev` (router) | Punto de entrada único. Lee la intención del usuario y enruta. Nunca se invocan las sub-skills directamente como respuesta al usuario. |
| `plugin-audit` | Compara el plugin actual contra el catálogo: lista features faltantes y desactualizados (lee `meta.yml` de cada feature y verifica señales en el proyecto). |
| `plugin-feature <nombre>` | Lee `features/<nombre>/README.md` + `files/` y adapta los archivos al plugin actual (rutas, idioma, datadir). |
| `plugin-recommend` | Recibe una necesidad en lenguaje natural y sugiere el/los feature(s) que la resuelven, citando el README. |
| `plugin-promote` | Toma una mejora nacida en el plugin actual y crea `features/<nuevo>/` en el catálogo siguiendo `CONTRIBUTING.md`. **Deja el resultado en working tree, sin commitear.** |

Más un comando atajo **`/plugin`** que invoca el router `plugin-dev`.

## Activación proactiva — detalle

Hook `SessionStart` (`hooks/hooks.json` → `bin/hooks/session-start.sh`):

1. Si la cwd contiene `.catalog-root` → es el repo del catálogo mismo → **salir** (guard de
   auto-referencia).
2. Si la cwd NO tiene `.claude-plugin/` → no es un proyecto de plugin → salir.
3. Si ya existe el marcador de "visto" (`.claude-plugin/.cli-template-seen`) → salir.
4. Caso contrario: crear el marcador y emitir (exit 0, informativo):
   > "Esto parece un proyecto de plugin. El catálogo cli-plugin-template está disponible —
   > corré `/plugin-audit` para ver qué features te faltan."

El marcador hace que el aviso aparezca una sola vez por proyecto. Después, todo es on-demand.

## Guard de auto-referencia

Archivo `.catalog-root` (vacío) en la raíz del catálogo, commiteado. Es el marcador
inequívoco de "este repo ES el catálogo, no un consumidor". Más robusto que heurísticas
(un consumidor podría tener `features/` copiado).

## Flujo de datos

```
SessionStart (1ª vez en proyecto-plugin) → sugiere /plugin-audit
/plugin → plugin-dev (router) → audit | feature | recommend | promote
plugin-audit       → lee ${CLAUDE_PLUGIN_ROOT}/features/*/meta.yml + señales del proyecto
plugin-feature <x> → lee features/x/README.md + files/ → adapta al proyecto
plugin-recommend   → matchea necesidad contra CATALOG.md + descriptions
plugin-promote     → crea features/<nuevo>/ en working tree del catálogo (sin commit)
```

## Estructura nueva en el repo

```
.catalog-root                ← NUEVO: guard de auto-referencia
.claude-plugin/plugin.json   ← NUEVO: convierte el repo en plugin instalable
skills/
  plugin-dev/SKILL.md        ← router (entry-point-router)
  plugin-audit/SKILL.md
  plugin-feature/SKILL.md
  plugin-recommend/SKILL.md
  plugin-promote/SKILL.md
commands/plugin.md           ← atajo /plugin
hooks/hooks.json             ← SessionStart gentil
bin/hooks/session-start.sh
features/                    ← (ya existe) catálogo que las skills leen
```

## Unidades y límites

- **Router** (`plugin-dev`): solo decide a qué capacidad enrutar. No implementa ninguna.
- Cada capacidad (`audit`/`feature`/`recommend`/`promote`) es independiente y se entiende
  sola: entrada (intención + cwd del plugin consumidor), salida (reporte o cambios en
  working tree).
- El hook `session-start.sh` solo detecta contexto y avisa una vez; no hace cambios.
- Las skills **leen** el catálogo (`features/`); no lo modifican, salvo `plugin-promote`.

## Fuera de alcance (fase 2)

- Aplicar `multi-cli-compat` al propio meta-plugin (manifiestos por CLI). Esta versión
  apunta a Claude Code; los demás CLIs leen `features/` igual al consultar.
- Renombrar el repo (hoy "template" es algo engañoso, pero renombrar rompe remotes/links).

## Testing

- `plugin-audit`: en un proyecto con `.claude-plugin/` y sin health-check ni versioning,
  debe listarlos como faltantes; con todo presente, reportar OK.
- `plugin-feature`: integrar `versioning` en un plugin de prueba y verificar que copia/adapta
  los archivos correctos.
- `session-start.sh`: en el repo del catálogo (`.catalog-root`) → sin output; en un proyecto
  plugin nuevo → avisa una vez; segunda sesión → sin output (marcador presente).
- Guard: un repo sin `.claude-plugin/` → el hook no hace nada.
