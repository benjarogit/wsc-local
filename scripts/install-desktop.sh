#!/usr/bin/env bash
# Desktop-Eintrag: ein Klick → Browser-Panel (für Laien)
set -euo pipefail
# shellcheck source=/dev/null
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
load_env

APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/256x256/apps"
mkdir -p "$APP_DIR" "$ICON_DIR"

ICON_SRC="$ROOT/panel/logo.png"
[[ -f "$ICON_SRC" ]] || ICON_SRC="$ROOT/scripts/icons/wsc-local.png"
if [[ -f "$ICON_SRC" ]]; then
    cp -f "$ICON_SRC" "$ICON_DIR/wsc-local.png"
fi

DESKTOP="$APP_DIR/wsc-local.desktop"
cat >"$DESKTOP" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=wsc-local
GenericName=WoltLab lokal
Comment=WoltLab-Entwicklungsumgebung steuern (Start, Stop, Sicherungen)
Exec=${ROOT}/panel.sh
Icon=wsc-local
Terminal=false
Categories=Development;Network;
Keywords=woltlab;wsc;docker;local;
StartupNotify=true
EOF
chmod 644 "$DESKTOP"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor" >/dev/null 2>&1 || true
fi

ui_ok "Desktop-Eintrag: wsc-local (Anwendungsmenü)"
ui_dim "Pfad: $DESKTOP"
