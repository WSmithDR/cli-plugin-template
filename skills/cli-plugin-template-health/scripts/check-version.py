#!/usr/bin/env python3
import json, sys, pathlib
root = pathlib.Path(sys.argv[1] or ".")
p = root / ".claude-plugin" / "plugin.json"
m = root / ".claude-plugin" / "marketplace.json"
try:
    pv = json.loads(p.read_text())["version"]
    print(f"✓ cli-plugin-template v{pv}")
except Exception as e:
    print(f"✗ no pude leer plugin.json ({e})")
    pv = None
if m.exists() and pv:
    try:
        mv = json.loads(m.read_text())["metadata"]["version"]
        print(f"✓ marketplace v{mv}" if mv == pv
              else f"✗ desync: plugin v{pv} ≠ marketplace v{mv}")
    except Exception as e:
        print(f"✗ no pude leer marketplace.json ({e})")
