#!/usr/bin/env bash
# Browser-Steuerung für wsc-local (nur 127.0.0.1) – Einstieg für Laien
set -euo pipefail
# shellcheck source=/dev/null
source "$(cd "$(dirname "$0")" && pwd)/scripts/lib.sh"
load_env

[[ -f "$ROOT/.env" ]] || die "Noch kein Setup – zuerst: ./setup.sh"

PORT="${PANEL_PORT:-9099}"
URL="http://127.0.0.1:${PORT}"
OPEN_BROWSER=1
QUIET=0
FORCE_RESTART=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-open) OPEN_BROWSER=0; shift ;;
        --quiet|-q) QUIET=1; OPEN_BROWSER=0; shift ;;
        --restart) FORCE_RESTART=1; shift ;;
        *) die "Unbekannt: $1 (erlaubt: --no-open, --quiet, --restart)" ;;
    esac
done

mkdir -p "$ROOT/var"

panel_alive() {
    curl -fsS --connect-timeout 1 "$URL/" >/dev/null 2>&1
}

stop_stale_panel() {
    if [[ -f "$ROOT/var/panel.pid" ]]; then
        local old
        old="$(cat "$ROOT/var/panel.pid" 2>/dev/null || true)"
        if [[ -n "$old" ]] && kill -0 "$old" 2>/dev/null; then
            if tr '\0' ' ' <"/proc/$old/cmdline" 2>/dev/null | grep -q 'panel_server.py'; then
                kill "$old" 2>/dev/null || true
                sleep 0.3
                kill -9 "$old" 2>/dev/null || true
            fi
        fi
        rm -f "$ROOT/var/panel.pid"
    fi
    pkill -f "$ROOT/scripts/panel_server.py" 2>/dev/null || true
    # Port freimachen (verhindert Doppel-Instanzen)
    if command -v fuser >/dev/null 2>&1; then
        fuser -k "${PORT}/tcp" >/dev/null 2>&1 || true
    fi
    sleep 0.3
}

start_panel() {
    stop_stale_panel
    nohup python3 "$ROOT/scripts/panel_server.py" >>"$ROOT/var/panel.log" 2>&1 &
    echo $! >"$ROOT/var/panel.pid"
    sleep 1
}

if [[ "$FORCE_RESTART" == "1" ]] || ! panel_alive; then
    [[ "$QUIET" == "1" ]] || {
        ui_header "wsc-local Panel"
        ui_info "Startet auf $URL (nur localhost)"
        ui_dim "Steuert dasselbe wie ./tools.sh – fremdes Docker bleibt unberührt."
        echo
    }
    start_panel
    if ! panel_alive; then
        ui_fail "Panel startete nicht – siehe var/panel.log"
        tail -20 "$ROOT/var/panel.log" 2>/dev/null || true
        exit 1
    fi
    [[ "$QUIET" == "1" ]] || ui_ok "Panel: $URL"
else
    [[ "$QUIET" == "1" ]] || ui_ok "Panel läuft: $URL"
fi

if [[ "$OPEN_BROWSER" == "1" && "${YES:-0}" != "1" ]]; then
    xdg-open "$URL" >/dev/null 2>&1 || true
fi
