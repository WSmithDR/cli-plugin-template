#!/usr/bin/env bash
# Instalador idempotente del scheduler harvest (systemd timer + path fallback).
set -euo pipefail
DRY=0; UNINSTALL=0
for a in "$@"; do case "$a" in --dry-run) DRY=1;; --uninstall) UNINSTALL=1;; esac; done

UNIT_DIR="${SYSTEMD_USER_DIR:-$HOME/.config/systemd/user}"
UNIT_PREFIX="cli-plugin-template-harvest"

if [ "$UNINSTALL" = 1 ]; then
  rm -f "$UNIT_DIR/$UNIT_PREFIX."{service,timer,path}
  rm -f "$UNIT_DIR/$UNIT_PREFIX-"*.path
  systemctl --user daemon-reload 2>/dev/null || true
  echo "harvest scheduler desinstalado"
  exit 0
fi

SCHEDULE="${HARVEST_SCHEDULE:-0 9 * * *}"
# mapeo cron-like -> systemd OnCalendar (simplificado para "HH MM * * *")
read -r _MIN _HOUR _DOM _MON _DOW <<< "$SCHEDULE"
ONCAL="*-*-* ${_HOUR}:${_MIN}:00"

if [ "$DRY" = 1 ]; then
  echo "harvest scheduler (dry-run):"
  echo "  timer: OnCalendar=$ONCAL Persistent=true"
  echo "  service: scan + run"
  echo "  path units: ~/.claude, ~/.config/opencode, ~/.gemini, ~/.kiro"
  exit 0
fi

mkdir -p "$UNIT_DIR"
CPT="$(cd "$(dirname "$0")" && pwd)/cpt"

cat > "$UNIT_DIR/$UNIT_PREFIX.service" <<EOF
[Unit]
Description=cli-plugin-template harvest (scan+run)
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/env bash -c 'python3 "$CPT" harvest scan && python3 "$CPT" harvest run'
EOF

cat > "$UNIT_DIR/$UNIT_PREFIX.timer" <<EOF
[Unit]
Description=harvest diario

[Timer]
OnCalendar=$ONCAL
Persistent=true

[Install]
WantedBy=timers.target
EOF

# path units para disparo por eventos (instalación de plugins)
for cli_dir in "$HOME/.claude" "$HOME/.config/opencode" "$HOME/.gemini" "$HOME/.kiro"; do
  cli_name="$(basename "$cli_dir" | sed 's/^\.//')"
  cat > "$UNIT_DIR/$UNIT_PREFIX-$cli_name.path" <<EOF
[Unit]
Description=harvest trigger $cli_name

[Path]
PathChanged=$cli_dir
PathModified=$cli_dir

[Install]
WantedBy=paths.target
EOF
done

systemctl --user daemon-reload 2>/dev/null || true
systemctl --user enable --now "$UNIT_PREFIX.timer" 2>/dev/null \
  || echo "timer instalado (activá con: systemctl --user enable --now $UNIT_PREFIX.timer)"

echo "harvest scheduler instalado en $UNIT_DIR"
echo "  - timer: $ONCAL"
echo "  - path triggers: .claude, .config/opencode, .gemini, .kiro"
