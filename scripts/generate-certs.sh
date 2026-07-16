#!/usr/bin/env bash
# Erzeugt lokale TLS-Zerts für https://wsc.local (mkcert).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CERT_DIR="${ROOT}/certs"
mkdir -p "${CERT_DIR}"

if ! command -v mkcert >/dev/null 2>&1; then
    echo "mkcert fehlt."
    echo "  Arch/CachyOS:  sudo pacman -S mkcert"
    echo "  oder:          https://github.com/FiloSottile/mkcert"
    exit 1
fi

mkcert -install >/dev/null 2>&1 || true
cd "${CERT_DIR}"
# mkcert schreibt Fortschritt nach stderr – komplett schlucken
if ! mkcert -cert-file fullchain.pem -key-file privkey.pem \
    wsc.local localhost 127.0.0.1 ::1 >/dev/null 2>&1; then
    echo "mkcert fehlgeschlagen." >&2
    exit 1
fi

[[ -f fullchain.pem && -f privkey.pem ]] || { echo "Zertifikate fehlen." >&2; exit 1; }
