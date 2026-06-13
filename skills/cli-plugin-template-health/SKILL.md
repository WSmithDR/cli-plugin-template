---
name: cli-plugin-template-health
description: Use when the cli-plugin-template meta-plugin was just installed/updated, or its skills/command don't fire, or /plugin-audit can't read the catalog — diagnoses version, the catalog skills + /plugin command, catalog readability, the SessionStart hook, and incomplete-install / unresolved CLAUDE_PLUGIN_ROOT.
---

# cli-plugin-template — Health Check

Auto-diagnóstico del meta-plugin. Corré cada chequeo, reportá ✓/✗, y para cada ✗
dá una remediación concreta. No modifiques nada: solo reportás.

> **Gotcha `CLAUDE_PLUGIN_ROOT`.** Todos los chequeos usan `${CLAUDE_PLUGIN_ROOT}`.
> Si esa variable está vacía, el plugin no fue instalado via `claude plugin install`
> (estás corriendo desde el repo a mano, o el plugin no cargó). En ese caso casi todo
> da ✗ con "archivo no encontrado": reportá **primero** este gotcha y su fix antes de
> seguir, porque es la causa raíz.
>
> ```bash
> [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && echo "✓ CLAUDE_PLUGIN_ROOT=$CLAUDE_PLUGIN_ROOT" \
>   || echo "✗ CLAUDE_PLUGIN_ROOT vacío — instalá con: claude plugin install cli-plugin-template"
> ```

## 1. Versión instalada (y vs. marketplace)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/cli-plugin-template-health/scripts/check-version.py" "$CLAUDE_PLUGIN_ROOT"
```
- ✗ leer `plugin.json` → instalación incompleta o `CLAUDE_PLUGIN_ROOT` mal resuelto (ver gotcha).
- ✗ desync con marketplace → reinstalá/actualizá: `claude plugin update cli-plugin-template`.

## 2. Skills del catálogo (10) + la propia health

Deben existir las 10 skills del catálogo y esta misma:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/cli-plugin-template-health/scripts/check-skills.sh"
```
- ✗ falta una skill → instalación incompleta; reinstalá. `plugin-dev` es el router de
  entrada: sin él, el ruteo del catálogo no funciona. (No hay comando slash: el router
  es una skill que se invoca al expresar la intención.)

## 3. Catálogo legible

El catálogo es el corazón del meta-plugin: `plugin-audit`/`plugin-feature` lo leen.
Debe existir `CATALOG.md` y el validador debe pasar.

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/cli-plugin-template-health/scripts/check-catalog.sh"
```
- ✗ falta `CATALOG.md` o `features/` → instalación incompleta: el catálogo no llegó.
  Reinstalá; si persiste, el paquete está corrupto.
- ✗ `validate-catalog` falla → reportá las líneas que imprimió (feature sin meta.yml,
  desync CATALOG↔features, etc.). Es un problema del catálogo, no del entorno.

## 4. Hook SessionStart

El hook debe estar registrado en `hooks/hooks.json` y su script debe existir.

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/cli-plugin-template-health/scripts/check-hook.sh"
```
- ✗ falta el registro o el script → el aviso proactivo en proyectos de plugin no
  dispara. Reinstalá; si editaste a mano, restaurá `hooks/hooks.json` y el script.

## Salida sugerida

Un checklist con una remediación por cada ✗:

```
cli-plugin-template — health check

✓ CLAUDE_PLUGIN_ROOT=/path/to/plugin
✓ cli-plugin-template v1.1.0
✓ marketplace v1.1.0
✓ Skills: 10/10 (9 catálogo + health)
✓ CATALOG.md + features/ + validate-catalog OK
✓ Hook SessionStart registrado + script presente

Todo OK.
```

Con fallos, listá solo los ✗ con su fix, por ejemplo:

```
✗ CLAUDE_PLUGIN_ROOT vacío   → claude plugin install cli-plugin-template
✗ falta skill plugin-recommend → instalación incompleta, reinstalá el plugin
✗ desync plugin v1.1.0 ≠ marketplace v1.0.0 → claude plugin update cli-plugin-template
```
