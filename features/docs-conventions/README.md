# Feature: docs-conventions

## Qué hace

Provee secciones de documentación estándar para el README (y `CLAUDE.md`) de un
plugin, para que install/update/versionado se documenten igual en todos.

## Por qué

Hoy las instrucciones de instalación, actualización y versionado están repartidas y
divergen entre plugins. Unificarlas reduce fricción: cualquiera sabe dónde mirar y
las instrucciones son consistentes.

## Integración

Copiá las secciones relevantes al README del plugin, reemplazando `<plugin>` y
`<marketplace>` por los valores reales.

### Sección: Instalación

```markdown
## Instalación

**1. Registrar el marketplace (una sola vez, global):**
\```bash
claude plugin marketplace add <owner>/<marketplace>
\```

**2. Instalar en el proyecto:**
\```bash
claude plugin install <plugin>@<marketplace> --scope project
\```

**Global (todos los proyectos):**
\```bash
claude plugin install <plugin>@<marketplace>
\```
```

### Sección: Actualización + verificación de versión

> El CLI cachea una copia del plugin: **refrescá el marketplace y reinstalá**. No alcanza
> con que cambie el repo, y `claude plugin update` sin refrescar puede saltear el update
> por "misma versión".

```markdown
## Actualizar

**Scope project:**
\```bash
/plugin marketplace update <marketplace>
/plugin install <plugin>@<marketplace> --scope project
\```

**Global (todos los proyectos):**
\```bash
/plugin marketplace update <marketplace>
/plugin install <plugin>@<marketplace>
\```

En una sesión activa, aplicá sin reiniciar con `/reload-plugins`. Para verificar que el
update tomó efecto, ejecutar `/<plugin>-health` — la versión mostrada debe coincidir con
la última publicada.
```

### Sección: Convención de versionado

Incluí esta tabla (coincide con el feature `versioning`):

```markdown
El plugin sigue semver (`MAJOR.MINOR.PATCH`); la versión se incrementa
automáticamente en cada commit según el prefijo:

| Prefijo | Bump |
|---|---|
| `feat:` | minor |
| `fix:`, `chore:`, `docs:`, `refactor:`, `style:`, `test:`, `ci:` | patch |
| `feat!:` o `BREAKING CHANGE` en el cuerpo | major |
```

### Sección: Desarrollo (si usás `git-hooks`)

```markdown
## Desarrollo

Tras clonar, instalá los git hooks (una vez):
\```bash
bash bin/dev/setup.sh
\```
Corre los tests antes de cada commit y versiona automáticamente.
```

## Tests

Verificá que el README integrado tenga las secciones de **install**, **update +
verificación de versión** y **versionado**, y que `<plugin>`/`<marketplace>` estén
reemplazados por los valores reales (sin placeholders colgando). Como prueba de humo,
seguí literalmente los comandos de la sección Instalación en una máquina limpia y
confirmá que el plugin queda instalado y que `/<plugin>-health` reporta la versión
publicada.

## Changelog

- **1.1.1** — la sección de Actualización usa el flujo confiable (`/plugin marketplace
  update` + reinstalar) en vez de `claude plugin update`, que puede saltear el update por
  "misma versión" sin refrescar el cache.
- **1.1.0** — agregada la sección `## Tests` (verificación de la integración de los
  docs), para cumplir el contrato de secciones requeridas del catálogo.
- **1.0.0** — versión inicial, consolidada desde `todo-plugin`.
