#!/usr/bin/env bash
# Tear-Down nur für dieses wsc-local-Projekt – nie fremdes Docker.
set -euo pipefail
# shellcheck source=/dev/null
source "$(cd "$(dirname "$0")" && pwd)/scripts/lib.sh"
load_env

PURGE_ALL=0
YES=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --purge-all) PURGE_ALL=1; shift ;;
        --yes|-y) YES=1; shift ;;
        *) die "Unbekannt: $1" ;;
    esac
done

msg "═══ wsc-local Reset ═══" "═══ wsc-local reset ═══"
msg "Projekt: $ROOT" "Project: $ROOT"
msg "Prefix:  $NAME_PREFIX" "Prefix:  $NAME_PREFIX"
if [[ "$PURGE_ALL" == "1" ]]; then
    msg "Modus:  --purge-all (alles weg inkl. Snapshots/Certs)" \
        "Mode:   --purge-all (everything including snapshots/certs)"
else
    msg "Modus:  Standard (Snapshots bleiben)" "Mode:   standard (keep snapshots)"
fi

if [[ "$YES" != "1" ]]; then
    read -rp "$(msg 'Wirklich fortfahren? Tippe ja: ' 'Really continue? Type yes: ')" conf
    [[ "$conf" == "ja" || "$conf" == "yes" ]] || { msg "Abgebrochen." "Aborted."; exit 0; }
fi

require_docker

msg "→ Container stoppen…" "→ Stopping containers…"
compose down -v --remove-orphans 2>/dev/null || true

for s in web mysql phpmyadmin mailhog; do
    docker rm -f "$(cname "$s")" 2>/dev/null || true
done

# Panel-Prozess beenden, falls lokal gestartet
if [[ -f "$ROOT/var/panel.pid" ]]; then
    kill "$(cat "$ROOT/var/panel.pid")" 2>/dev/null || true
    rm -f "$ROOT/var/panel.pid"
fi
pkill -f "$ROOT/scripts/panel_server.py" 2>/dev/null || true

msg "→ woltlab/ leeren…" "→ Clearing woltlab/…"
find "$ROOT/woltlab" -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} + 2>/dev/null || true
if [[ -n "$(find "$ROOT/woltlab" -mindepth 1 ! -name '.gitkeep' 2>/dev/null | head -1)" ]]; then
    docker run --rm -v "$ROOT/woltlab:/mnt" alpine \
        sh -c 'find /mnt -mindepth 1 ! -name .gitkeep -exec rm -rf {} +' 2>/dev/null || true
fi
if [[ -n "$(find "$ROOT/woltlab" -mindepth 1 ! -name '.gitkeep' 2>/dev/null | head -1)" ]]; then
    sudo find "$ROOT/woltlab" -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} + 2>/dev/null || true
fi
if docker info >/dev/null 2>&1; then
    docker run --rm -v "$ROOT/woltlab:/mnt" alpine \
        chown "$(id -u):$(id -g)" /mnt 2>/dev/null || true
fi

rm -f "$ROOT/.env"
find "$ROOT/var" -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} + 2>/dev/null || true

if [[ "$PURGE_ALL" == "1" ]]; then
    msg "→ Snapshots & Certs löschen…" "→ Removing snapshots & certs…"
    find "$ROOT/snapshots" -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} + 2>/dev/null || true
    rm -f "$ROOT/certs/"*.pem 2>/dev/null || true
fi

msg "✓ Reset fertig. Danach: ./setup.sh" "✓ Reset done. Next: ./setup.sh"
