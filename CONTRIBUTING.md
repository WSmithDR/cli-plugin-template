# Promover una mejora al catálogo (loop inverso)

Cuando una mejora nace en un plugin concreto (ej. `todo-plugin`) y sirve para
**cualquier** plugin, se promueve a este catálogo para que el resto la herede.

## Cuándo promover

- ✅ Sirve para cualquier plugin (versionado, hooks, docs, compatibilidad CLI).
- ❌ Es específica de un plugin (su lógica de dominio) → queda en ese plugin.

Ante la duda: si tuvieras que copiar y pegar esto en otro plugin, va al catálogo.

## Setup de desarrollo

Después de clonar, instalá los git hooks:

```bash
bash bin/dev/setup.sh
```

El `pre-commit` valida el catálogo y los evals, corre los tests (hooks, gap de catálogo,
evals, bump-version) y audita portabilidad (`features/portability-audit/`, bloquea ante
rutas absolutas o secretos). Las exclusiones del audit para este repo viven en
`.portabilityignore`.

## Publicar una versión

La versión del plugin vive en varios manifiestos (`.claude-plugin/plugin.json`,
`marketplace.json`, y los manifiestos por CLI). **No la edites a mano** —se desincronizan
y `/plugin install` saltea el update. Usá el script, que trata `plugin.json` como fuente
de verdad y sincroniza el resto:

```bash
python3 bin/bump-version.py minor     # major | minor | patch
python3 bin/bump-version.py --set 2.1.0
python3 bin/bump-version.py --check    # ¿están todos sincronizados?
```

`validate-catalog.py` (y por ende CI) falla si algún manifiesto quedó fuera de sync. Si
instalaste el hook `post-commit` del feature `versioning`, el bump es automático según el
prefijo del commit y no necesitás correr el script a mano. Tras publicar, los usuarios
toman la versión con `/plugin marketplace update` + `/plugin install`.

## Cómo promover un feature nuevo

1. Creá `features/<nombre>/` con esta estructura:
   ```
   features/<nombre>/
     README.md     ← qué · por qué · cómo integrarlo (escrito para un agente)
     files/        ← los archivos reusables (scripts, configs, plantillas)
     meta.yml      ← version: 1.0.0, cli_compat, depends_on
   ```
2. El `README.md` debe incluir, en este orden:
   - **Qué hace** (1–2 líneas)
   - **Por qué** (qué problema resuelve)
   - **Integración** (pasos concretos: qué archivos copiar, qué adaptar, qué comando correr)
   - **Tests** (cómo verificar que quedó bien integrado)
3. Agregá la fila en `CATALOG.md`.
4. Si el feature reemplaza una versión anterior, subí el `version` en `meta.yml`
   y documentá el cambio en la sección "Changelog" de su README.

## Cómo actualizar un feature existente

1. Editá los archivos en `features/<nombre>/files/`.
2. Subí `version` en `meta.yml` siguiendo semver.
3. Anotá el cambio en el "Changelog" del README del feature.
4. Actualizá la versión en la fila de `CATALOG.md`.

Los plugins que ya integraron el feature comparan su versión local contra la del
catálogo para decidir si actualizan.
