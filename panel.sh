#!/usr/bin/env bash
# Gemeinsamer Einstieg: Linux/macOS sowie Windows innerhalb von WSL2.
set -euo pipefail
wsc_root="$(cd "$(dirname "$0")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
    echo 'Python 3.10+ fehlt. macOS: brew install python; Ubuntu/WSL: sudo apt install python3.' >&2
    exit 1
fi
exec python3 "$wsc_root/workbench/launcher.py" "$@"
