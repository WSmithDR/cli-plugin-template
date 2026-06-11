# Feature: worktree-redirect

## Qué hace

Detecta si el plugin corre dentro de un **git worktree** (una copia de trabajo aparte
del repo principal) y redirige el output de datos del plugin al root del repo principal,
en vez de dejarlo en el worktree.

## Por qué

Los worktrees suelen ser efímeros (se crean para una tarea y se eliminan después). Si el
plugin escribe sus datos dentro del worktree, esos datos se pierden al borrarlo.
Redirigir al repo principal asegura persistencia. Solo relevante si trabajás con worktrees.

## Cómo detectar y redirigir

`git rev-parse --git-dir` apunta al `.git` del worktree; `--git-common-dir` apunta al
`.git` compartido del repo principal. Si difieren, estás en un worktree.

```bash
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null || echo "")
COMMON_DIR=$(git rev-parse --git-common-dir 2>/dev/null || echo "")

if [ -n "$GIT_DIR" ] && [ "$GIT_DIR" != "$COMMON_DIR" ]; then
    # Estamos en un worktree → el repo principal es el padre de git-common-dir
    MAIN_ROOT=$(dirname "$(cd "$COMMON_DIR" && pwd)")
    DATADIR="$MAIN_ROOT/.midata"
else
    DATADIR=".midata"
fi
```

## Integración

1. En el resolver de paths del plugin (ver `data-gateway` → `paths.py`, o el script de
   setup), aplicá la detección antes de fijar el datadir.
2. Usá `DATADIR` resuelto para toda lectura/escritura de datos.

## Tests

Creá un worktree (`git worktree add ../wt`), corré el plugin adentro y verificá que los
datos aparecen en el repo principal, no en el worktree.

## Changelog

- **1.0.0** — patrón de `understand-anything` (worktree redirect en SKILL.md).
