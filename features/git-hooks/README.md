# Feature: git-hooks

## Qué hace

Infraestructura de git hooks para el **desarrollo** de un plugin, editor-agnóstica:
corre la suite de tests antes de cada commit en cualquier CLI o editor, y se instala
con un solo comando tras clonar.

## Por qué

Los hooks en `.git/hooks/` no se versionan (git excluye `.git/` por diseño, y
distribuir hooks ejecutables sería un vector de ataque). La solución estándar es
versionar los hooks dentro del repo y distribuir un `setup.sh` que crea symlinks a
`.git/hooks/`. Así el desarrollador los instala una vez y corren en cualquier editor.

Un hook de Claude Code (`.claude/settings.json`) **no** sirve acá: solo lo lee Claude
Code. Un git hook real corre en Codex, OpenCode, Gemini CLI, o git desde la terminal.

## Integración

1. Copiá los archivos a tu plugin (adaptando idioma/rutas si hace falta):
   ```
   files/setup.sh             → bin/dev/setup.sh
   files/pre-commit           → bin/dev/git-hooks/pre-commit
   files/test-hooks.sh.example → bin/dev/test-hooks.sh   (renombrar, llenar con tus tests)
   files/ci-test.yml          → .github/workflows/test.yml
   ```
2. Escribí tus casos de test reales en `bin/dev/test-hooks.sh` siguiendo el patrón
   del esqueleto (cada caso en un tmpdir aislado, verifica exit code + salida).
3. Hacé ejecutables los scripts y corré el setup:
   ```bash
   chmod +x bin/dev/setup.sh bin/dev/git-hooks/*
   bash bin/dev/setup.sh
   ```
4. `setup.sh` instala los hooks via symlink. Cada desarrollador lo corre una vez
   después de clonar (documentalo en el README del plugin — ver feature
   `docs-conventions`).

> **Nota**: `setup.sh` instala tanto `pre-commit` como `post-commit`. El `post-commit`
> lo aporta el feature [`versioning`](../versioning/README.md). Si no usás versionado
> automático, quitá la línea `install_hook "post-commit"` de `setup.sh`.

## Tests

Después de integrar, verificá que el arnés corre:
```bash
bash bin/dev/test-hooks.sh
```
Y que el pre-commit dispara los tests al commitear:
```bash
git commit -m "test: verificar hook"   # debe correr la suite antes de aceptar
```

## Changelog

- **1.0.0** — versión inicial migrada desde `todo-plugin`.
