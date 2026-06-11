#!/usr/bin/env python3
"""CLI unificado del plugin. Punto de entrada para TODAS las operaciones de datos.

Renombrar a `bin/<plugin>` y hacer ejecutable. Las skills lo invocan:
    python3 "$PLUGIN_ROOT/bin/<plugin>" data <entity> <op> [args...]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
import argparse

import gateway


def main() -> int:
    parser = argparse.ArgumentParser(prog="<plugin>")
    sub = parser.add_subparsers(dest="cmd", required=True)

    data = sub.add_parser("data", help="operaciones de persistencia")
    data.add_argument("entity")
    data.add_argument("op", choices=["save", "load", "list", "delete"])
    data.add_argument("args", nargs="*")

    ns = parser.parse_args()

    if ns.cmd == "data":
        if ns.op == "save":
            key, content = ns.args[0], ns.args[1]
            print(gateway.save(ns.entity, key, content))
        elif ns.op == "load":
            out = gateway.load(ns.entity, ns.args[0])
            print(out if out is not None else "", end="")
        elif ns.op == "list":
            print("\n".join(gateway.list_keys(ns.entity)))
        elif ns.op == "delete":
            print("deleted" if gateway.delete(ns.entity, ns.args[0]) else "not found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
