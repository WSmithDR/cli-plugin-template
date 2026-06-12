# Feature: versioning

## Qué hace

Bumpea la versión del plugin automáticamente en cada commit, según el prefijo del
mensaje (conventional commits), e incluye el cambio en el **mismo** commit.

| Prefijo | Bump |
|---|---|
| `feat:` | minor |
| `fix:`, `chore:`, `docs:`, `refactor:`, `style:`, `test:`, `ci:` | patch |
| `feat!:` o `BREAKING CHANGE` en el cuerpo | major |

## Por qué

Mantener la versión a mano se olvida, y un plugin desactualizado en el manifiesto
hace imposible verificar si un `update` tomó efecto. Atar el bump al prefijo del
commit lo vuelve automático y consistente.

**Por qué `post-commit` y no `commit-msg`/`prepare-commit-msg`**: git congela el
índice antes de esos hooks, así que un `git add` ahí entra en el *siguiente* commit,
no en el actual. `post-commit` corre después de que el commit existe: lee el mensaje,
bumpea el manifiesto, y hace `git commit --amend --no-edit --no-verify` para meter el
cambio en el mismo commit. El `--no-verify` es seguro porque los tests ya corrieron
en `pre-commit`.

**Recursión (importante)**: `--no-verify` **NO** saltea el hook `post-commit`. El
`git commit --amend` re-dispara post-commit y, sin protección, bumpea dos veces. El
hook usa un **sentinel file** (`.git/.version-bump-in-progress`): se crea antes del
amend; la invocación re-disparada lo detecta y sale, garantizando un único bump. No
confíes en inspeccionar HEAD para frenar la recursión —resulta poco fiable bajo amend.

## Integración

1. Requiere el feature [`git-hooks`](../git-hooks/README.md) (el `setup.sh` que
   instala los symlinks). Integralo primero.
2. Copiá el hook:
   ```
   files/post-commit → bin/dev/git-hooks/post-commit
   ```
3. **Adaptá el path del manifiesto** dentro de `post-commit`. Por defecto apunta a
   `.claude-plugin/plugin.json` (Claude Code). Cambialo si tu CLI usa otro archivo
   de versión. Si publicás por marketplace, el hook también sincroniza
   `.claude-plugin/marketplace.json` (cuando existe): bumpea `metadata.version` y la
   entry cuyo `name` matchee el del plugin. Sin esto, el marketplace queda atrasado y
   `/plugin install` saltea el update por "misma versión".
4. Asegurate de que `setup.sh` instale el hook (incluye `install_hook "post-commit"`).
5. `chmod +x bin/dev/git-hooks/post-commit && bash bin/dev/setup.sh`

### Bump manual (sin el hook)

Si no querés el bump automático en cada commit, podés bumpear a demanda con un script que
sincroniza **todos** los manifiestos a la vez (plugin.json como fuente de verdad). En este
repo es `bin/bump-version.py` (`major|minor|patch`, `--set X.Y.Z`, `--sync`, `--check`).
Útil cuando el plugin publica por marketplace y tiene manifiestos por CLI: el hook solo
toca `plugin.json`/`marketplace.json`, el script cubre también gemini/codex/cursor/copilot.

### Seguridad

El hook lee la versión actual con Python. **No interpoles variables de shell dentro
del código Python** (`python3 -c "... $VAR ..."`) — un valor malicioso en el
manifiesto ejecutaría código arbitrario. Pasá los valores por variables de entorno
con el `-c` en comillas simples, y validá el formato de versión con regex
(`^\d+\.\d+\.\d+$`) antes de usarlo. El `post-commit` provisto ya lo hace así.

## Tests

```bash
# en un repo temporal con un manifiesto:
git commit -m "feat: algo"      # versión sube minor, queda en el commit
git show --name-only HEAD | grep plugin.json   # confirma que entró
git status                       # árbol limpio, nada staged colgando
```
El arnés `test-hooks.sh` del feature `git-hooks` incluye casos parametrizados para
cada tipo de bump — copialos y adaptá el path del manifiesto.

## Changelog

- **1.2.0** — el hook sincroniza `marketplace.json` además de `plugin.json` (bumpea
  `metadata.version` y la entry del plugin por `name`). Evita el drift que dejaba el
  marketplace atrasado respecto del manifiesto.
- **1.1.0** — guard de recursión con sentinel file (`--no-verify` no saltea
  post-commit; el amend re-disparaba y bumpeaba dos veces).
- **1.0.0** — versión inicial migrada desde `todo-plugin`. Usa `post-commit` con
  amend; reemplaza intentos previos con `commit-msg`/`prepare-commit-msg`.
