#!/usr/bin/env bash
# Desktop-Eintrag + optional Browser öffnen (Panel bevorzugt)
set -euo pipefail
# shellcheck source=/dev/null
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
load_env

PANEL_URL="http://127.0.0.1:${PANEL_PORT:-9099}"
SITE_URL="https://wsc.local"

ICON="$ROOT/scripts/icons/wsc-local.png"
mkdir -p "$ROOT/scripts/icons" "$HOME/.local/share/applications"
if [[ ! -f "$ICON" && -f "$ROOT/panel/logo.png" ]]; then
    cp -f "$ROOT/panel/logo.png" "$ICON"
fi

DESKTOP="$HOME/.local/share/applications/wsc-local.desktop"
cat >"$DESKTOP" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=WSC Local
Comment=Lokaler WoltLab-Stack – Panel öffnen
Exec=${ROOT}/panel.sh
Icon=${ICON}
Terminal=false
Categories=Development;System;
StartupNotify=true
EOF
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
chmod +x "$ROOT/panel.sh" "$ROOT/start.sh" "$ROOT/tools.sh" 2>/dev/null || true

ui_ok "Desktop-Eintrag: „WSC Local“ → Panel"
ui_dim "CLI: ./start.sh · ./tools.sh · ./panel.sh"

if [[ "${YES:-0}" == "1" ]]; then
    exit 0
fi

echo
read -rp "$(echo -e "  ${BOLD}Panel jetzt öffnen?${RESET} [j/N]: ")" o
if [[ "${o:-}" =~ ^[jJyY]$ ]]; then
    "$ROOT/panel.sh" || xdg-open "$SITE_URL" >/dev/null 2>&1 &
fi
