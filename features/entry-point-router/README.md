# Feature: entry-point-router

## Qué hace

Define un **único skill de entrada** que lee el contexto disponible (estado de git,
archivos, mensaje del usuario, historial) y decide qué escenario aplicar, delegando a
sub-skills privadas. El usuario invoca uno solo y el router resuelve el resto.

## Por qué

Si el usuario tiene que conocer 5–10 skills distintas y cuál usar cuándo, la fricción
es alta y los errores frecuentes. Centralizar el routing en un skill:
- Da un solo punto de entrada memorable.
- Hace la decisión de routing auditable y depurable en un solo lugar.
- Permite agregar escenarios sin romper los existentes.

## Integración

1. Creá el skill router `skills/<plugin>-context/SKILL.md` con pasos:
   - **Step 0**: revisá si hay sesión/estado activo (fast-path: reutilizá contexto).
   - **Step 1**: recopilá señales (git repo, branch, diffs, archivos, mensaje).
   - **Step 2**: consultá historial relevante si aplica.
   - **Step 3**: **detectá el escenario** leyendo los triggers de cada archivo en
     `scenarios/` y evaluándolos contra las señales.
   - **Step 4+**: delegá al escenario correspondiente.
2. Definí los escenarios como archivos en `skills/<plugin>-context/scenarios/`:
   ```
   scenarios/
     01-<caso-a>.md   ← trigger + qué hacer
     02-<caso-b>.md
   ```
3. Regla para el agente (en `AGENTS.md`/`CLAUDE.md`):
   > El escenario se elige DESPUÉS de recopilar señales, nunca antes. Nunca invocar
   > una sub-skill privada directamente como respuesta al usuario: el entry point es
   > el router.
4. Persistí estado de sesión (ej. `<datadir>/session-state.json`) para el fast-path.

## Enforcement duro: token de delegación hook-set (patrón rígido)

La convención escrita (paso 3 arriba) **no basta**: un agente puede ignorar la regla
y llamar skills privadas directamente (`Skill("anki-capture")`), saltándose el router
y todo el pipeline (clasificación, proposal gate, vocabulario). Para **forzar** el
router a nivel de runtime:

1. **Token de delegación** — el router emite un token efímero (turn-scoped,
   no-forgeable) que identifica: `delegated_from=<router>`, `delegated_to=<skill>`,
   `turn_id=<N>`, `scenario=<nombre>`.
2. **PreToolUse hook (delegation-guard)** — intercepta `Skill` invocations:
   - Si el caller NO es el router → **bloquea** y emite mensaje que obliga a volver
     al router (`"Debés ir por <plugin>-context"`).
   - Si el caller ES el router pero **no pasó token válido** → bloquea.
   - Skills privadas: `build/*`, `review/*`, `meta/*`, `utils/*` → sólo invocables
     con token.
   - Skills públicas (entry points): location top-level `skills/<name>/` → token
     opcional (pueden invocarse directo por el usuario).
3. **Clasificación por ubicación, no por prefijo de nombre** — una skill es
   "pública" si vive en `skills/<nombre>/` (top-level). Los prefijos `anki-*` que
   comparten habilidades públicas y privadas **no** definen publicidad. Esto evita el
   bypass real: una skill pública con prefijo `anki-*` (ej. `anki-capture`) NO forja
   token y no queda atrapada.

Archivos provistos como patrón:
- `hooks/pre-tool-use/delegation-guard.py` — lógica de clasificación + guardia runtime.

### Pitfalls de seguridad (revisión whole-branch)

| # | Hallazgo | Por qué importa | Mitigación |
|---|----------|----------------|------------|
| 1 | **Publicidad por prefijo = bypass** | Si `is_entrypoint` chequea `name.startswith("anki-")`, `anki-capture` (pública) forja token y salta router | Clasificar por **ubicación en FS** (top-level vs build/review/meta/utils) |
| 2 | **Regex read-private-skill sin ancla** | `Read("skills/build/.../SKILL.md")` (path relativo, posible bajo OpenCode) se escapaba porque el regex exigía slash líder | Anclar regex con `(^|/)` |
| 3 | **Anti-forgery en Bash por substring** | El token en filename incluye `delegated_to=X`; un `Read` a `X.md` puede falsificar el match substring | Defense-in-depth: write real sin token respaldado la bloquea el firewall de hooks |

## Tests

Simulá distintos contextos (repo con diffs, mensaje "enseñame X", rama existente) y
verificá que el router selecciona el escenario correcto.

Test de enforcement: intentá invocar `Skill("privada-build")` directo → debe bloquear;
via router con token → debe permitir.

## Changelog

- **1.1.0** — enforcement duro añadido: token de delegación hook-set (unforgeable,
  turn-scoped) + PreToolUse guard `delegation-guard.py`. 3 pitfalls de seguridad
  documentados (publicidad por prefijo = bypass, regex sin ancla, anti-forgery por
  substring). Patrón extraído y verificado en `ankify` (feature/rigid-router-delegation-token).
- **1.0.0** — patrón extraído de `ankify` (anki-context + scenarios/).
