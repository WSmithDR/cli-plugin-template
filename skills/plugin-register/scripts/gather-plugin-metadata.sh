#!/usr/bin/env bash
set -euo pipefail

NAME=$(python3 -c "import json;print(json.load(open('.claude-plugin/plugin.json'))['name'])")
LOCAL_PATH=$(pwd)
REMOTE=$(git remote get-url origin 2>/dev/null || echo "")

echo "NAME=$NAME"
echo "LOCAL_PATH=$LOCAL_PATH"
echo "REMOTE=$REMOTE"
