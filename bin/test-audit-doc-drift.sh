#!/bin/bash
# Tests de bin/audit-doc-drift.py. Árbol tmp con fixtures; cuenta hits vía --json.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DETECTOR="$SCRIPT_DIR/audit-doc-drift.py"
PASS=0; FAIL=0
_pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
_fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

TREE=$(mktemp -d)
trap 'rm -rf "$TREE"' EXIT
TODAY=$(date +%F)
OLD=$(date -d "300 days ago" +%F)

hits() { python3 "$DETECTOR" "$TREE" --json | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d), ' '.join(sorted(x['status'] for x in d)))"; }

echo ""
echo "=== audit-doc-drift.py ==="

# claim sin fecha → 1 hit undated
mkdir -p "$TREE/docs" "$TREE/features/x/files" "$TREE/skills/y"
echo 'OpenCode no expone transcript .jsonl.' > "$TREE/docs/a.md"
out=$(hits)
[ "$out" = "1 undated" ] && _pass "claim sin fecha → undated" || _fail "undated: '$out'"

# con fecha fresca en la línea o ±1 → sin hit
printf 'OpenCode no expone transcript .jsonl. (verificado %s, doc)\n' "$TODAY" > "$TREE/docs/b.md"
printf 'no expone X\n(verificado %s, fuente)\n' "$TODAY" > "$TREE/docs/c.md"
[ "$(hits | cut -d' ' -f1)" = "1" ] && _pass "fecha fresca (línea o vecina) → cubre" || _fail "fresca: '$(hits)'"

# fecha vencida (>180 días) → hit stale
printf 'sin equivalente en Gemini. (verificado %s, doc)\n' "$OLD" > "$TREE/docs/d.md"
out=$(hits)
echo "$out" | grep -q "stale" && _pass "fecha vencida → stale" || _fail "stale: '$out'"

# dentro de fence o backticks → ignorado
printf '```\nno expone nada\n```\n`cmd no emite output`\n' > "$TREE/docs/e.md"
[ "$(hits | cut -d' ' -f1)" = "2" ] && _pass "fence y backticks ignorados" || _fail "fence: '$(hits)'"

# docs/plans/, test-*, features/*/files/ → excluidos por diseño
mkdir -p "$TREE/docs/plans"
echo 'no expone nada' > "$TREE/docs/plans/p.md"
echo 'no expone nada' > "$TREE/test-thing.sh"
echo 'no expone nada' > "$TREE/features/x/files/f.md"
[ "$(hits | cut -d' ' -f1)" = "2" ] && _pass "histórico, tests y ejemplos excluidos" || _fail "exclusiones: '$(hits)'"

# report-only: exit 0 incluso con hits
python3 "$DETECTOR" "$TREE" >/dev/null && _pass "siempre exit 0" || _fail "exit != 0"

echo ""
echo "Resultado: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ] && exit 0 || exit 1
