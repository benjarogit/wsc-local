#!/usr/bin/env bash
# One-Shot-Setup für wsc-local
set -euo pipefail
# shellcheck source=/dev/null
source "$(cd "$(dirname "$0")" && pwd)/scripts/lib.sh"

YES=0
DO_RESET=0
ZIP_PATH=""
ZIP_URL=""
SKIP_PWA=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --yes|-y) YES=1; export YES; shift ;;
        --reset) DO_RESET=1; shift ;;
        --zip) ZIP_PATH="$2"; shift 2 ;;
        --zip-url) ZIP_URL="$2"; shift 2 ;;
        --skip-pwa) SKIP_PWA=1; shift ;;
        --en) LANG_UI=en; export LANG_UI; shift ;;
        --de) LANG_UI=de; export LANG_UI; shift ;;
        -h|--help)
            cat <<EOF
Usage: ./setup.sh [options]

  --yes              Non-interactive (ADMIN_PASSWORD als Env)
  --reset            Vorher reset.sh --purge-all
  --zip PATH         Lokales WoltLab-ZIP
  --zip-url URL      WoltLab-ZIP-URL
  --skip-pwa         Keinen Browser öffnen am Ende
  --de / --en        Sprache

Danach:
  ./start.sh         Stack starten
  ./tools.sh         Terminal-Menü
  ./panel.sh         Browser-Steuerung (AdminLTE)

Beispiel:
  ./setup.sh
  ADMIN_PASSWORD='geheim' ./setup.sh --yes
EOF
            exit 0
            ;;
        *) die "Unbekannt: $1" ;;
    esac
done

SECONDS=0
ui_header "wsc-local – Easy Setup"

require_docker
require_mkcert

if [[ "$DO_RESET" == "1" ]]; then
    "$ROOT/reset.sh" --purge-all --yes
fi

NAME_PREFIX="${NAME_PREFIX:-woltlab}"

if [[ "$YES" == "1" ]]; then
    ADMIN_USER="${ADMIN_USER:-admin}"
    ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"
    [[ -n "$ADMIN_PASSWORD" ]] || die "Mit --yes: ADMIN_PASSWORD setzen (nicht leer)."
else
    echo -e "  ${DIM}Ein Login für WoltLab, MySQL und phpMyAdmin.${RESET}"
    echo -e "  ${DIM}Empfehlung: mind. 12 Zeichen (nicht Pflicht).${RESET}"
    echo
    read -rp "$(echo -e "  ${BOLD}Benutzername${RESET} [admin]: ")" u
    ADMIN_USER="${u:-admin}"
    while true; do
        read -rsp "$(echo -e "  ${BOLD}Passwort${RESET}: ")" ADMIN_PASSWORD
        echo
        read -rsp "$(echo -e "  ${BOLD}Wiederholen${RESET}: ")" p2
        echo
        if [[ -z "$ADMIN_PASSWORD" ]]; then
            ui_warn "Passwort darf nicht leer sein."
            continue
        fi
        if [[ "$ADMIN_PASSWORD" != "$p2" ]]; then
            ui_warn "Stimmt nicht überein."
            continue
        fi
        if [[ "${#ADMIN_PASSWORD}" -lt 12 ]]; then
            ui_dim "Kürzer als 12 Zeichen – für lokal ok."
        fi
        break
    done
    read -rp "$(echo -e "  ${BOLD}Name-Prefix${RESET} [${NAME_PREFIX}]: ")" np
    NAME_PREFIX="${np:-$NAME_PREFIX}"
    echo
fi

[[ -n "$ADMIN_PASSWORD" ]] || die "Passwort darf nicht leer sein."
[[ "$ADMIN_USER" =~ ^[a-zA-Z0-9_]+$ ]] || die "ADMIN_USER nur Buchstaben/Zahlen/Unterstrich."
[[ "$NAME_PREFIX" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]*$ ]] || die "NAME_PREFIX nur Buchstaben/Zahlen/-/_ (Container-Namen)."

cat >"$ROOT/.env" <<EOF
ADMIN_USER=${ADMIN_USER}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
ADMIN_EMAIL=${ADMIN_USER}@wsc.local

WSC_VERSION=${WSC_VERSION:-6.2.5}
WSC_SHA256=${WSC_SHA256:-a6727fa7e95f84737cda6fbcfcf72ba691fdb4be965281197d1cae7011c6ee19}

NAME_PREFIX=${NAME_PREFIX}
COMPOSE_PROJECT_NAME=wsc-local

MYSQL_ROOT_PASSWORD=${ADMIN_PASSWORD}
MYSQL_DATABASE=woltlab
MYSQL_USER=${ADMIN_USER}
MYSQL_PASSWORD=${ADMIN_PASSWORD}

HTTP_PORT=${HTTP_PORT:-8080}
HTTPS_PORT=${HTTPS_PORT:-443}
MYSQL_PORT=${MYSQL_PORT:-3307}
PHPMYADMIN_PORT=${PHPMYADMIN_PORT:-8081}
MAILHOG_UI_PORT=${MAILHOG_UI_PORT:-8025}
MAILHOG_SMTP_PORT=${MAILHOG_SMTP_PORT:-1025}
PANEL_PORT=${PANEL_PORT:-9099}

LANG_UI=${LANG_UI:-de}
EOF
chmod 600 "$ROOT/.env"
load_env

check_conflict() {
    local label="$1" port="$2" name="$3"
    if container_exists "$name" && ! docker inspect -f '{{.Config.Labels}}' "$name" 2>/dev/null | grep -q "com.docker.compose.project=${COMPOSE_PROJECT_NAME}"; then
        die "Container-Name belegt: $name – anderen NAME_PREFIX wählen."
    fi
    if port_in_use "$port"; then
        container_running "$name" && return 0
        die "Port $port ($label) belegt."
    fi
}

ui_info "Prüfe Ports & Namen…"
check_conflict HTTP "$HTTP_PORT" "$(cname web)"
check_conflict HTTPS "$HTTPS_PORT" "$(cname web)"
check_conflict MySQL "$MYSQL_PORT" "$(cname mysql)"
check_conflict phpMyAdmin "$PHPMYADMIN_PORT" "$(cname phpmyadmin)"
check_conflict MailHog "$MAILHOG_UI_PORT" "$(cname mailhog)"
ui_ok "Ports frei"

ui_info "TLS für https://wsc.local + localhost (mkcert)…"
ui_run "TLS-Zertifikate erzeugen" "$ROOT/scripts/generate-certs.sh"
ensure_hosts

DL_ARGS=()
[[ -n "$ZIP_PATH" ]] && DL_ARGS+=(--zip "$ZIP_PATH")
[[ -n "$ZIP_URL" ]] && DL_ARGS+=(--zip-url "$ZIP_URL")

if [[ -n "$ZIP_PATH" ]]; then
    ui_info "WoltLab-ZIP (lokal): $ZIP_PATH"
elif [[ -n "$ZIP_URL" ]]; then
    ui_info "WoltLab-Download: $ZIP_URL"
else
    ui_info "WoltLab-Download: assets.woltlab.com (Suite Core ${WSC_VERSION})"
fi
ui_spin_start "WoltLab laden, prüfen (SHA-256) & entpacken…"
if WSC_QUIET=1 "$ROOT/scripts/download-woltlab.sh" "${DL_ARGS[@]+"${DL_ARGS[@]}"}" >/tmp/wsc-dl.log 2>&1; then
    ui_spin_done ok "WoltLab ${WSC_VERSION} in ./woltlab/"
else
    ui_spin_done fail "WoltLab Download fehlgeschlagen"
    sed 's/^/    /' /tmp/wsc-dl.log >&2 || true
    exit 1
fi

ui_info "Images: web (PHP/Apache), MySQL, phpMyAdmin, MailHog"
ui_spin_start "Container bauen & starten…"
compose_up up -d --build
ui_spin_done ok "Container laufen ($(cname web), mysql, …)"

ui_spin_start "Warte auf MySQL…"
for _ in $(seq 1 60); do
    if docker exec "$(cname mysql)" mysqladmin ping -h 127.0.0.1 -uroot -p"${MYSQL_ROOT_PASSWORD}" --silent >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
ui_spin_done ok "MySQL bereit"

ui_info "WoltLab Unattended-Install (install.php?dev=1 + Kernpaket)…"
"$ROOT/scripts/install-woltlab.sh"
ui_ok "WoltLab bereit unter https://wsc.local"

if [[ "$SKIP_PWA" != "1" ]]; then
    YES="$YES" "$ROOT/scripts/setup-pwa.sh"
fi

mkdir -p "$ROOT/var"
{
    echo "# wsc-local – Ein Login überall (nicht committen)"
    echo "Benutzer: ${ADMIN_USER}"
    echo "Passwort: ${ADMIN_PASSWORD}"
    echo ""
    echo "WoltLab:     https://wsc.local"
    echo "phpMyAdmin:  http://localhost:${PHPMYADMIN_PORT}"
    echo "MailHog:     http://localhost:${MAILHOG_UI_PORT}"
    echo "Panel:       http://127.0.0.1:${PANEL_PORT:-9099}  (./panel.sh)"
} >"$ROOT/var/credentials.txt"
chmod 600 "$ROOT/var/credentials.txt"

echo
ui_box_start
echo -e "  ${BOLD}Fertig! Ein Login überall${RESET}"
echo
ui_kv "Benutzer" "$ADMIN_USER"
ui_kv "Passwort" "$ADMIN_PASSWORD"
echo
ui_kv "WoltLab" "https://wsc.local"
ui_kv "phpMyAdmin" "http://localhost:${PHPMYADMIN_PORT}"
ui_kv "MailHog" "http://localhost:${MAILHOG_UI_PORT}"
ui_kv "Panel" "http://127.0.0.1:${PANEL_PORT:-9099}"
ui_box_end
ui_dim "Dauer: $((SECONDS / 60))m $((SECONDS % 60))s"
ui_dim "Kopie: var/credentials.txt"
echo

# Desktop-Launcher + Panel für Laien
"$ROOT/scripts/install-desktop.sh" 2>/dev/null || true
echo
ui_dim "Alltag (einfach):"
ui_dim "  Anwendungsmenü → „wsc-local“  (Browser-Steuerung)"
ui_dim "  oder: ./panel.sh"
ui_dim "  Terminal: ./start.sh  ·  ./tools.sh  ·  ./tools.sh stop"
echo
ui_dim "Fremdes Docker wird nie angefasst – nur dieses Projekt."
echo

if [[ "${YES:-0}" != "1" && "${WSC_NO_PANEL:-0}" != "1" ]]; then
    ui_info "Öffne Steuerungs-Panel…"
    "$ROOT/panel.sh" || true
fi
echo
