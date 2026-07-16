#!/usr/bin/env bash
# Browser-Steuerung für wsc-local (optional, nur 127.0.0.1)
set -euo pipefail
# shellcheck source=/dev/null
source "$(cd "$(dirname "$0")" && pwd)/scripts/lib.sh"
load_env

[[ -f "$ROOT/.env" ]] || die "Noch kein Setup – zuerst: ./setup.sh"

PORT="${PANEL_PORT:-9099}"
URL="http://127.0.0.1:${PORT}"

# schon offen?
if curl -fsS --connect-timeout 1 "$URL/" >/dev/null 2>&1; then
    ui_ok "Panel läuft bereits: $URL"
    xdg-open "$URL" >/dev/null 2>&1 || true
    exit 0
fi

ui_header "wsc-local Panel"
ui_info "Startet auf $URL (nur localhost)"
ui_dim "Steuert dasselbe wie ./tools.sh – fremdes Docker bleibt unberührt."
echo

# Hintergrund
nohup python3 "$ROOT/scripts/panel_server.py" >>"$ROOT/var/panel.log" 2>&1 &
echo $! >"$ROOT/var/panel.pid"
sleep 1

if curl -fsS --connect-timeout 2 "$URL/" >/dev/null 2>&1; then
    ui_ok "Panel: $URL"
    if [[ "${YES:-0}" != "1" ]]; then
        xdg-open "$URL" >/dev/null 2>&1 || true
    fi
else
    ui_fail "Panel startete nicht – siehe var/panel.log"
    exit 1
fi
