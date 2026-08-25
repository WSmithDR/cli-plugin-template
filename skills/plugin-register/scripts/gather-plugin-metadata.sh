#!/usr/bin/env bash
# Reúne los datos de alta de un plugin. Con argumento, del repo en esa ruta; sin
# argumento, del cwd (comportamiento histórico). La fricción con un plugin casi nunca
# aparece dentro de su repo, así que el alta tiene que poder hacerse desde cualquier cwd.
set -euo pipefail

TARGET="${1:-$PWD}"

[ -d "$TARGET" ] || { echo "ERROR: no existe la ruta: $TARGET" >&2; exit 1; }
TARGET=$(cd "$TARGET" && pwd -P)

# local_path tiene que ser el repo de DESARROLLO: plugin-hotpatch parchea contra él.
# El cache de plugins es una copia instalada — un patch ahí se pierde en el próximo update.
case "$TARGET" in
    "$HOME"/.claude/plugins/cache/*)
        echo "ERROR: $TARGET está en el cache de plugins, no es el repo de desarrollo." >&2
        echo "       Pasá la ruta del repo (donde editás el plugin)." >&2
        exit 1
        ;;
esac

MANIFEST=""
[ -f "$TARGET/.claude-plugin/plugin.json" ] && MANIFEST="$TARGET/.claude-plugin/plugin.json"
[ -z "$MANIFEST" ] && [ -f "$TARGET/.codex-plugin/plugin.json" ] && MANIFEST="$TARGET/.codex-plugin/plugin.json"
[ -n "$MANIFEST" ] || {
    echo "ERROR: $TARGET no tiene .claude-plugin/plugin.json — no parece un plugin" >&2
    exit 1
}

NAME=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['name'])" "$MANIFEST")
REMOTE=$(git -C "$TARGET" remote get-url origin 2>/dev/null || echo "")

echo "NAME=$NAME"
echo "LOCAL_PATH=$TARGET"
echo "REMOTE=$REMOTE"
