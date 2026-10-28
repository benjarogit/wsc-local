#!/usr/bin/env bash
# Die Workbench ist der Standard; das alte Einzel-Setup bleibt explizit erreichbar.
set -euo pipefail
wsc_root="$(cd "$(dirname "$0")" && pwd)"
if [[ "${1:-}" == "--legacy" ]]; then
    shift
    exec bash "$wsc_root/scripts/legacy/setup.sh" "$@"
fi
exec bash "$wsc_root/panel.sh" --setup "$@"
