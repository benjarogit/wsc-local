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
SKIP_PORTAINER=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --yes|-y) YES=1; export YES; shift ;;
        --reset) DO_RESET=1; shift ;;
        --zip) ZIP_PATH="$2"; shift 2 ;;
        --zip-url) ZIP_URL="$2"; shift 2 ;;
        --skip-pwa) SKIP_PWA=1; shift ;;
        --skip-portainer) SKIP_PORTAINER=1; shift ;;
        --en) LANG_UI=en; export LANG_UI; shift ;;
        --de) LANG_UI=de; export LANG_UI; shift ;;
        -h|--help)
            cat <<EOF
Usage: ./setup.sh [options]
  --yes              Non-interactive (ADMIN_PASSWORD Pflicht als Env)
  --reset            Vorher reset.sh --purge-all
  --zip PATH         Lokales WoltLab-ZIP
  --zip-url URL      WoltLab-ZIP-URL
  --skip-pwa         Kein Desktop/PWA
  --skip-portainer   Portainer nicht starten
  --de / --en        Sprache
EOF
            exit 0
            ;;
        *) die "Unbekannt: $1" ;;
    esac
done

msg "╔══════════════════════════════════════════╗" "╔══════════════════════════════════════════╗"
msg "║   wsc-local – Easy Setup                 ║" "║   wsc-local – Easy Setup                 ║"
msg "╚══════════════════════════════════════════╝" "╚══════════════════════════════════════════╝"

require_docker
require_mkcert

if [[ "$DO_RESET" == "1" ]]; then
    "$ROOT/reset.sh" --purge-all --yes
fi

# --- Credentials ---
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"
NAME_PREFIX="${NAME_PREFIX:-woltlab}"

if [[ -z "$ADMIN_PASSWORD" ]]; then
    if [[ "$YES" == "1" ]]; then
        die "ADMIN_PASSWORD muss gesetzt sein (min. 12 Zeichen): ADMIN_PASSWORD='…' ./setup.sh --yes"
    fi
    msg "Ein Login für WoltLab, MySQL, phpMyAdmin und Portainer (neu)." \
        "One login for WoltLab, MySQL, phpMyAdmin and Portainer (new)."
    read -rp "$(msg 'Benutzername [admin]: ' 'Username [admin]: ')" u
    ADMIN_USER="${u:-admin}"
    while true; do
        read -rsp "$(msg 'Passwort (min. 12 Zeichen): ' 'Password (min. 12 chars): ')" ADMIN_PASSWORD
        echo
        read -rsp "$(msg 'Passwort wiederholen: ' 'Confirm password: ')" p2
        echo
        if [[ "${#ADMIN_PASSWORD}" -lt 12 ]]; then
            msg "Zu kurz." "Too short."
            continue
        fi
        [[ "$ADMIN_PASSWORD" == "$p2" ]] && break
        msg "Stimmt nicht überein." "Mismatch."
    done
    read -rp "$(msg "Name-Prefix [${NAME_PREFIX}]: " "Name prefix [${NAME_PREFIX}]: ")" np
    NAME_PREFIX="${np:-$NAME_PREFIX}"
fi

[[ "${#ADMIN_PASSWORD}" -ge 12 ]] || die "Passwort muss mindestens 12 Zeichen haben."
[[ "$ADMIN_USER" =~ ^[a-zA-Z0-9_]+$ ]] || die "ADMIN_USER nur Buchstaben/Zahlen/Unterstrich."

# --- .env schreiben ---
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
PORTAINER_PORT=${PORTAINER_PORT:-9443}

LANG_UI=${LANG_UI:-de}
EOF
chmod 600 "$ROOT/.env"
load_env

# --- Konflikt-Check ---
check_conflict() {
    local label="$1" port="$2" name="$3"
    if container_exists "$name" && ! docker inspect -f '{{.Config.Labels}}' "$name" 2>/dev/null | grep -q "com.docker.compose.project=${COMPOSE_PROJECT_NAME}"; then
        die "Container-Name belegt: $name – setze NAME_PREFIX anders (z.B. wsc2) und starte neu."
    fi
    if port_in_use "$port"; then
        # eigener Container ok
        if container_running "$name"; then
            return 0
        fi
        die "Port $port ($label) belegt – in .env ändern oder Konflikt beheben. Vorschlag: NAME_PREFIX=wsc2"
    fi
}

msg "→ Prüfe Ports & Namen…" "→ Checking ports & names…"
check_conflict HTTP "$HTTP_PORT" "$(cname web)"
check_conflict HTTPS "$HTTPS_PORT" "$(cname web)"
check_conflict MySQL "$MYSQL_PORT" "$(cname mysql)"
check_conflict phpMyAdmin "$PHPMYADMIN_PORT" "$(cname phpmyadmin)"
check_conflict MailHog "$MAILHOG_UI_PORT" "$(cname mailhog)"

START_PORTAINER=0
if [[ "$SKIP_PORTAINER" != "1" ]]; then
    if foreign_portainer_running; then
        msg "✓ Portainer bereits vorhanden – wird wiederverwendet (kein neues)." \
            "✓ Portainer already present – reusing (not creating a new one)."
    else
        START_PORTAINER=1
        if port_in_use "$PORTAINER_PORT" && ! container_running "$(cname portainer)"; then
            die "Port $PORTAINER_PORT belegt – PORTAINER_PORT in .env ändern."
        fi
    fi
fi

# --- Certs ---
msg "→ TLS-Zertifikate (mkcert)…" "→ TLS certificates (mkcert)…"
"$ROOT/scripts/generate-certs.sh"
ensure_hosts

# --- Download ---
DL_ARGS=()
[[ -n "$ZIP_PATH" ]] && DL_ARGS+=(--zip "$ZIP_PATH")
[[ -n "$ZIP_URL" ]] && DL_ARGS+=(--zip-url "$ZIP_URL")
"$ROOT/scripts/download-woltlab.sh" "${DL_ARGS[@]+"${DL_ARGS[@]}"}"

# --- Portainer Passwort-Datei ---
if [[ "$START_PORTAINER" == "1" ]]; then
    msg "→ Portainer-Admin vorbereiten…" "→ Preparing Portainer admin…"
    gen_portainer_password_file "$ADMIN_PASSWORD" \
        || die "Konnte bcrypt-Hash nicht erzeugen (python3-bcrypt oder htpasswd/docker nötig)."
fi

# --- Compose up ---
msg "→ Images bauen & Container starten…" "→ Building images & starting containers…"
if [[ "$START_PORTAINER" == "1" ]]; then
    compose --profile overview up -d --build
else
    compose up -d --build
fi

msg "→ Warte auf MySQL…" "→ Waiting for MySQL…"
for i in $(seq 1 60); do
    if docker exec "$(cname mysql)" mysqladmin ping -h 127.0.0.1 -uroot -p"${MYSQL_ROOT_PASSWORD}" --silent 2>/dev/null; then
        break
    fi
    sleep 1
done

# --- Install ---
"$ROOT/scripts/install-woltlab.sh"

# --- PWA ---
if [[ "$SKIP_PWA" != "1" ]]; then
    YES="$YES" "$ROOT/scripts/setup-pwa.sh"
fi

# --- Fertig ---
msg "" ""
msg "════════════════════════════════════════" "════════════════════════════════════════"
msg "  Fertig! Ein Login überall:" "  Done! One login everywhere:"
msg "  Benutzer: ${ADMIN_USER}" "  User:     ${ADMIN_USER}"
msg "  Passwort: (das von dir gesetzte)" "  Password: (the one you set)"
msg "" ""
msg "  WoltLab:     https://wsc.local" "  WoltLab:     https://wsc.local"
msg "  phpMyAdmin:  http://localhost:${PHPMYADMIN_PORT}" "  phpMyAdmin:  http://localhost:${PHPMYADMIN_PORT}"
msg "  MailHog:     http://localhost:${MAILHOG_UI_PORT}" "  MailHog:     http://localhost:${MAILHOG_UI_PORT}"
if [[ "$START_PORTAINER" == "1" ]]; then
    msg "  Portainer:   https://localhost:${PORTAINER_PORT}" "  Portainer:   https://localhost:${PORTAINER_PORT}"
    if [[ "$ADMIN_USER" != "admin" ]]; then
        msg "  (Portainer-User heißt technisch immer „admin“, Passwort = deins)" \
            "  (Portainer username is always “admin”, password = yours)"
    fi
else
    msg "  Portainer:   bereits vorhanden" "  Portainer:   already present"
fi
msg "════════════════════════════════════════" "════════════════════════════════════════"
msg "./tools.sh  – Status / Snapshots / Doctor" "./tools.sh  – status / snapshots / doctor"
