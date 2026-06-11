#!/bin/bash
# Encuentra un Python 3 funcional y ejecuta el hook con él.
# Uso: bash py-hook.sh <script.py> [args...]

set -euo pipefail

MIN_MAJOR=3
MIN_MINOR=8

version_ok() {
    local v; v=$("$@" -c 'import sys; print("%d %d" % sys.version_info[:2])' 2>/dev/null) || return 1
    local major minor; read -r major minor <<<"$v"
    [ "$major" -gt "$MIN_MAJOR" ] || { [ "$major" -eq "$MIN_MAJOR" ] && [ "$minor" -ge "$MIN_MINOR" ]; }
}

SCRIPT="$1"; shift
# Convertir ruta POSIX → Windows si estamos en Git-Bash
if command -v cygpath >/dev/null 2>&1; then
    SCRIPT=$(cygpath -w "$SCRIPT")
fi
export PYTHONIOENCODING=utf-8

for cand in "python3" "python" "py -3"; do
    # shellcheck disable=SC2086
    if version_ok $cand; then
        # shellcheck disable=SC2086
        exec $cand "$SCRIPT" "$@"
    fi
done

# Fallback: cualquier python3, aunque sea viejo (los checks deterministas suelen andar)
exec python3 "$SCRIPT" "$@"
