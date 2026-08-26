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

echo ""; echo "=== ir canónico ==="
FIX=$(mktemp -d)
mkdir -p "$FIX/skills/mi-skill" "$FIX/hooks" "$FIX/agents"
printf '{"name":"fake","version":"0.0.1"}' > "$FIX/plugin.json"
printf '# Skill\ncontenido' > "$FIX/skills/mi-skill/SKILL.md"
printf '{"hooks":{}}' > "$FIX/hooks/hooks.json"
out=$(python3 -c "
import sys; sys.path.insert(0,'$SCRIPT_DIR/lib')
from harvest.ir import plugin_to_ir, ir_hash, IR_VERSION
ir = plugin_to_ir('$FIX', 'opencode')
print(IR_VERSION)
print(ir['cli'])
print(ir_hash(ir))
" 2>&1)
echo "$out" | grep -q "^1$" && _pass "IR_VERSION=1" || _fail "version: $out"
echo "$out" | grep -q "opencode" && _pass "cli en IR" || _fail "cli: $out"
# hash determinista
h1=$(python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR/lib'); from harvest.ir import plugin_to_ir, ir_hash; print(ir_hash(plugin_to_ir('$FIX','opencode')))")
h2=$(python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR/lib'); from harvest.ir import plugin_to_ir, ir_hash; print(ir_hash(plugin_to_ir('$FIX','opencode')))")
[ "$h1" = "$h2" ] && _pass "hash determinista" || _fail "hash: $h1 vs $h2"
rm -rf "$FIX"

echo ""; echo "=== consenso ==="
out=$(python3 -c "
import sys; sys.path.insert(0,'$SCRIPT_DIR/lib')
from harvest.consensus import aggregate
a = [{'claim':'usa hook','evidence':['hooks/hooks.json'],'confidence':0.9}]
b = [{'claim':'usa hook','evidence':['hooks/hooks.json'],'confidence':0.8}]
c = [{'claim':'otra idea','evidence':['README.md'],'confidence':0.7}]
res = aggregate([a,b,c], 'majority')
print(res)
assert any(x['claim']=='usa hook' for x in res['consensus']), 'hook debe estar en consenso'
assert any(x['claim']=='otra idea' for x in res['contested']), 'otra idea contested'
print('ok')
" 2>&1)
echo "$out" | grep -q "ok" && _pass "majority agrega bien" || _fail "consenso: $out"
out=$(python3 -c "
import sys; sys.path.insert(0,'$SCRIPT_DIR/lib')
from harvest.consensus import aggregate
a = [{'claim':'x','evidence':['a'],'confidence':0.9}]
b = [{'claim':'y','evidence':['b'],'confidence':0.9}]
res = aggregate([a,b], 'strict')
assert len(res['consensus'])==0, 'strict sin unanimidad -> vacio'
print('ok')
" 2>&1)
echo "$out" | grep -q "ok" && _pass "strict exige unanimidad" || _fail "strict: $out"

echo ""; echo "=== scorecard ==="
out=$(python3 -c "
import sys; sys.path.insert(0,'$SCRIPT_DIR/lib')
from harvest.scorecard import scorecard_load, scorecard_update, pick_models
# simula 2 modelos con historial: uno bueno, uno laggard
scorecard_update('free-a', agreed=8, latency_ms=1200, failed=False)
scorecard_update('free-a', agreed=9, latency_ms=1100, failed=False)
scorecard_update('free-b', agreed=1, latency_ms=5000, failed=True)
scorecard_update('free-b', agreed=0, latency_ms=6000, failed=True)
picked = pick_models(1)
print(picked)
assert 'free-a' in picked, 'debe elegir free-a'
assert 'free-b' not in picked, 'laggard fuera'
print('ok')
" 2>&1)
echo "$out" | grep -q "ok" && _pass "scorecard degrada laggard" || _fail "scorecard: $out"

echo ""; echo "=== harvest scan ==="
# Fake HOME con opencode config y un plugin local declarado
HOME_FIX=$(mktemp -d)
mkdir -p "$HOME_FIX/.config/opencode" "$HOME_FIX/.local/share/opencode"
FAKE_PLUGIN=$(mktemp -d)
printf '{"name":"fake-p","version":"0.1.0"}' > "$FAKE_PLUGIN/plugin.json"
mkdir -p "$FAKE_PLUGIN/skills/s"
printf '# S\nhello' > "$FAKE_PLUGIN/skills/s/SKILL.md"
printf '{"plugin":["%s"]}' "$FAKE_PLUGIN" > "$HOME_FIX/.config/opencode/opencode.json" 2>/dev/null || true
# Test unitario directo del IR+scan sin tocar HOME: solo valida que harvest_scan existe y encola
out=$(HOME="$HOME_FIX" python3 -c "
import sys; sys.path.insert(0,'$SCRIPT_DIR/lib')
from harvest.scan import harvest_scan
res = harvest_scan()
print(res)
" 2>&1)
echo "$out" | grep -q "scanned" && _pass "harvest_scan corre" || _fail "scan: $out"
# segunda corrida sin cambios -> enqueued 0
out2=$(HOME="$HOME_FIX" python3 -c "
import sys; sys.path.insert(0,'$SCRIPT_DIR/lib')
from harvest.scan import harvest_scan
print(harvest_scan())
" 2>&1)
echo "$out2" | grep -q "'enqueued': 0" && _pass "segunda corrida sin cambios -> 0" || _fail "dedupe: $out2"
rm -rf "$HOME_FIX" "$FAKE_PLUGIN"
