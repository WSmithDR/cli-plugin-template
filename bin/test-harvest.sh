#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CPT="$SCRIPT_DIR/cpt"
DATA=$(mktemp -d); export CLI_PLUGIN_TEMPLATE_DATA_DIR="$DATA"
FAIL=0; _pass(){ echo "PASS $1"; }; _fail(){ echo "FAIL $1"; FAIL=1; }

echo "=== paths harvest ==="
out=$(python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR/lib'); import paths; print(paths.harvest_pending_file())")
echo "$out" | grep -q "harvest/pending.json" && _pass "pending path" || _fail "pending path: $out"
out=$(python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR/lib'); import paths; print(paths.harvest_snapshot_file())")
echo "$out" | grep -q "harvest/snapshot.json" && _pass "snapshot path" || _fail "snapshot: $out"
