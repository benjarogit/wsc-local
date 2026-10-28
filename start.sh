#!/usr/bin/env bash
set -euo pipefail
wsc_root="$(cd "$(dirname "$0")" && pwd)"
if [[ "${1:-}" == "--legacy" ]]; then
    shift
    exec bash "$wsc_root/scripts/legacy/start.sh" "$@"
fi
exec bash "$wsc_root/panel.sh" "$@"
