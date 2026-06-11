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

```markdown
## Actualizar

**Scope project:**
\```bash
claude plugin update <plugin>@<marketplace> --scope project
\```

**Scope user (global):**
\```bash
claude plugin update <plugin>@<marketplace>
\```

Para verificar que el update tomó efecto, ejecutar `/<plugin>-health` — la versión
mostrada debe coincidir con la última publicada.
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

## Changelog

- **1.0.0** — versión inicial, consolidada desde `todo-plugin`.
