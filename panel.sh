#!/usr/bin/env bash
# Gemeinsamer Einstieg: Linux/macOS sowie Windows innerhalb von WSL2.
set -euo pipefail
wsc_root="$(cd "$(dirname "$0")" && pwd)"
if [[ "$(uname -s)" == Darwin ]]; then
    for wsc_prefix in /opt/homebrew/bin /usr/local/bin; do
        if [[ -d "$wsc_prefix" ]]; then export PATH="$wsc_prefix:$PATH"; fi
    done
fi
if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys; sys.exit(sys.version_info < (3,10))' 2>/dev/null; then
    echo 'Automatische Einrichtung: bash ./setup.sh --install-deps. Python 3.10+ fehlt. macOS: brew install python; Ubuntu/WSL: sudo apt install python3.' >&2
    exit 1
fi
exec python3 "$wsc_root/workbench/launcher.py" "$@"
