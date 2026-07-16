#!/usr/bin/env bash
# Desktop-Launcher / PWA-Hinweise (Firefox oder Chrome)
set -euo pipefail
# shellcheck source=/dev/null
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
load_env

detect_default_browser() {
    local desktop=""
    if command -v xdg-settings >/dev/null 2>&1; then
        desktop=$(xdg-settings get default-web-browser 2>/dev/null || true)
    fi
    case "$desktop" in
        *firefox*) echo firefox ;;
        *chrom*|*chrome*|*brave*|*edge*) echo chrome ;;
        *)
            if command -v google-chrome-stable >/dev/null 2>&1 || command -v chromium >/dev/null 2>&1; then
                echo chrome
            elif command -v firefox >/dev/null 2>&1; then
                echo firefox
            else
                echo unknown
            fi
            ;;
    esac
}

RECOMMENDED="$(detect_default_browser)"
PORTAINER_URL="https://localhost:${PORTAINER_PORT}"

CHOICE=""
if [[ "${YES:-0}" == "1" ]]; then
    CHOICE="$RECOMMENDED"
    [[ "$CHOICE" == "unknown" ]] && CHOICE="chrome"
else
    msg "" ""
    msg "── Desktop / PWA ──" "── Desktop / PWA ──"
    msg "Erkannter Standardbrowser: ${RECOMMENDED}" "Detected default browser: ${RECOMMENDED}"
    msg "1) Chrome / Chromium (App-Fenster)" "1) Chrome / Chromium (app window)"
    msg "2) Firefox (PWA / Website als App)" "2) Firefox (PWA / site as app)"
    msg "3) Überspringen" "3) Skip"
    read -rp "$(msg "Auswahl [1/2/3, Enter=${RECOMMENDED}]: " "Choice [1/2/3, Enter=${RECOMMENDED}]: ")" ans
    case "${ans:-}" in
        1) CHOICE=chrome ;;
        2) CHOICE=firefox ;;
        3) CHOICE=skip ;;
        "") CHOICE="$RECOMMENDED"; [[ "$CHOICE" == "unknown" ]] && CHOICE=chrome ;;
        *) CHOICE="$RECOMMENDED"; [[ "$CHOICE" == "unknown" ]] && CHOICE=chrome ;;
    esac
fi

[[ "$CHOICE" == "skip" ]] && { msg "PWA übersprungen." "PWA skipped."; exit 0; }

# Präferenz für open-overview.sh
mkdir -p "$ROOT/var"
echo "WSC_BROWSER=${CHOICE}" >"$ROOT/var/browser-pref.env"
# In .env mergen
if grep -q '^WSC_BROWSER=' "$ROOT/.env" 2>/dev/null; then
    sed -i "s/^WSC_BROWSER=.*/WSC_BROWSER=${CHOICE}/" "$ROOT/.env"
else
    echo "WSC_BROWSER=${CHOICE}" >>"$ROOT/.env"
fi

ICON="$ROOT/scripts/icons/portainer.png"
mkdir -p "$ROOT/scripts/icons"
if [[ ! -f "$ICON" ]]; then
    curl -fsSL "https://www.google.com/s2/favicons?domain=portainer.io&sz=128" -o "$ICON" 2>/dev/null || true
fi

DESKTOP="$HOME/.local/share/applications/wsc-local-overview.desktop"
mkdir -p "$HOME/.local/share/applications"
cat >"$DESKTOP" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=WSC Local Übersicht
Name[en]=WSC Local Overview
Comment=Portainer – Container starten/stoppen
Exec=${ROOT}/scripts/open-overview.sh
Icon=${ICON}
Terminal=false
Categories=Development;System;
StartupNotify=true
EOF
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
chmod +x "$ROOT/scripts/open-overview.sh"

case "$CHOICE" in
    chrome)
        msg "✓ Desktop-Launcher (Chrome App-Modus)." "✓ Desktop launcher (Chrome app mode)."
        msg "  App-Menü → „WSC Local Übersicht“" "  App menu → “WSC Local Overview”"
        ;;
    firefox)
        msg "✓ Desktop-Launcher angelegt." "✓ Desktop launcher created."
        msg "Firefox-PWA:" "Firefox PWA:"
        msg "  1) ${PORTAINER_URL} öffnen" "  1) Open ${PORTAINER_URL}"
        msg "  2) Menü → Diese Website als App installieren" \
            "  2) Menu → Install this site as an app"
        if [[ "${YES:-0}" != "1" ]]; then
            read -rp "$(msg 'Firefox jetzt öffnen? [J/n]: ' 'Open Firefox now? [Y/n]: ')" o
            if [[ ! "${o:-}" =~ ^[nN] ]]; then
                firefox --new-window "$PORTAINER_URL" >/dev/null 2>&1 &
            fi
        fi
        ;;
esac
