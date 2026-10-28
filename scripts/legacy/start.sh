#!/usr/bin/env bash
# Stack starten (nach erfolgreichem ./setup.sh)
set -euo pipefail
# shellcheck source=/dev/null
source "$(cd "$(dirname "$0")/.." && pwd)/lib.sh"
load_env

[[ -f "$ROOT/.env" ]] || die "Noch kein Setup – zuerst: ./setup.sh"

ui_header "wsc-local – Start"
"$ROOT/tools.sh" start

echo
ui_dim "Steuern:"
ui_dim "  ./tools.sh          → Terminal-Menü (Status, Snapshots, Doctor, …)"
ui_dim "  ./panel.sh          → Browser-Oberfläche (optional)"
ui_dim "  ./tools.sh stop     → Stack stoppen"
echo
