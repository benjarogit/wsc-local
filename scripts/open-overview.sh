#!/usr/bin/env bash
# Öffnet Portainer als App-Fenster (Chrome) oder Browser.
set -euo pipefail
# shellcheck source=/dev/null
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
load_env

URL="https://localhost:${PORTAINER_PORT}"
PREF="${WSC_BROWSER:-}"
ours="$(cname portainer)"

if ! container_running "$ours" && ! foreign_portainer_running; then
    if [[ -f "$ROOT/var/portainer-admin-password" ]]; then
        compose --profile overview up -d portainer 2>/dev/null || true
        sleep 2
    fi
fi

# Fremdes Portainer auf Standard-Port?
if ! container_running "$ours" && foreign_portainer_running; then
    URL="https://localhost:9443"
fi

if [[ -z "$PREF" ]]; then
    if command -v google-chrome-stable >/dev/null 2>&1 || command -v chromium >/dev/null 2>&1; then
        PREF=chrome
    elif command -v firefox >/dev/null 2>&1; then
        PREF=firefox
    fi
fi

case "$PREF" in
    chrome)
        if command -v google-chrome-stable >/dev/null 2>&1; then
            exec google-chrome-stable --app="$URL" --window-size=1400,900
        elif command -v chromium >/dev/null 2>&1; then
            exec chromium --app="$URL" --window-size=1400,900
        fi
        ;;
    firefox)
        exec firefox --new-window "$URL"
        ;;
esac
xdg-open "$URL"
