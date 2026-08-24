#!/usr/bin/env python3
"""PreCompact / session.compacted: antes de compactar contexto, deja un snapshot mínimo del estado del repo
(branch, status, commits recientes) en el store, para que la sesión post-compacto no arranque ciega.
Dual-CLI: Claude Code lo dispara con PreCompact; OpenCode vía event session.compacted (.opencode/hooks/compact-event/)."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


def main() -> None:
    try:
        json.load(sys.stdin)
    except Exception:
        pass
    from paths import data_dir  # bin/lib/paths.py ya resuelve CLI_PLUGIN_TEMPLATE_DATA_DIR
    wip = data_dir() / "wip"
    wip.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    body = (
        f"## Branch\n{git('rev-parse', '--abbrev-ref', 'HEAD')}\n\n"
        f"## Status\n{git('status', '--short')}\n\n"
        f"## Últimos commits\n{git('log', '--oneline', '-3')}\n"
    )
    path = wip / f"{stamp}.txt"
    path.write_text(body)
    print(f"WIP snapshot → {path}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # ponytail: PreCompact no puede romper la compactación; snapshot es best-effort
