#!/usr/bin/env bash
# Erzeugt lokale TLS-Zerts für https://wsc.local (mkcert empfohlen).
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
mkcert -cert-file fullchain.pem -key-file privkey.pem wsc.local localhost 127.0.0.1 ::1

echo "OK: ${CERT_DIR}/fullchain.pem + privkey.pem"
echo "Hosts-Eintrag (falls nötig): 127.0.0.1 wsc.local"
