#!/usr/bin/env bash
# Stack starten (nach erfolgreichem ./setup.sh) – öffnet das Panel für Laien
set -euo pipefail
# shellcheck source=/dev/null
source "$(cd "$(dirname "$0")" && pwd)/scripts/lib.sh"
load_env

[[ -f "$ROOT/.env" ]] || die "Noch kein Setup – zuerst: ./setup.sh"

PORT="${PANEL_PORT:-9099}"
URL="http://127.0.0.1:${PORT}"

ui_header "wsc-local – Start"
"$ROOT/tools.sh" start

# Desktop-Eintrag (einmalig / aktualisieren) – still bei Fehler
"$ROOT/scripts/install-desktop.sh" >/dev/null 2>&1 || true

BROWSER_OK=0
if [[ "${YES:-0}" != "1" && "${WSC_NO_PANEL:-0}" != "1" ]]; then
    if "$ROOT/panel.sh" --quiet; then
        # Browser öffnen (panel.sh --quiet unterdrückt xdg-open → hier bewusst)
        if xdg-open "$URL" >/dev/null 2>&1; then
            BROWSER_OK=1
        fi
    else
        ui_warn "Panel konnte nicht starten – siehe: ./panel.sh"
    fi
fi

echo
if [[ "$BROWSER_OK" == "1" ]]; then
    ui_box_start
    echo -e "  ${BOLD}Fertig – schau in den Browser${RESET}"
    echo
    ui_kv "Steuerung" "$URL"
    ui_kv "Website" "https://wsc.local"
    echo
    echo -e "  ${GREEN}✓${RESET} Das Panel wurde geöffnet."
    echo -e "  ${DIM}Dieses Terminal brauchst du nicht mehr – Fenster schließen ist ok.${RESET}"
    echo -e "  ${DIM}Später wieder: Anwendungsmenü „wsc-local“ oder ./start.sh${RESET}"
    ui_box_end
else
    ui_ok "Umgebung läuft."
    ui_dim "Panel öffnen: ./panel.sh  →  $URL"
    ui_dim "Oder: Anwendungsmenü → „wsc-local“"
fi
echo

# Sauber beenden – bei Desktop-„Im Terminal ausführen“ schließt sich das Fenster oft danach
exit 0
