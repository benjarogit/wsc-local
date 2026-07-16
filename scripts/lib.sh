#!/usr/bin/env bash
# Gemeinsame Hilfen für setup.sh / reset.sh / tools
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=/dev/null
[[ -f "$ROOT/scripts/ui.sh" ]] && source "$ROOT/scripts/ui.sh"

LANG_UI="${LANG_UI:-de}"

msg() {
    local de="$1" en="${2:-$1}"
    if [[ "${LANG_UI}" == "en" ]]; then echo -e "$en"; else echo -e "$de"; fi
}

die() {
    msg "✗ $1" "✗ $1" >&2
    exit 1
}

load_env() {
    if [[ -f "$ROOT/.env" ]]; then
        set -a
        # shellcheck disable=SC1091
        source "$ROOT/.env"
        set +a
    fi
    NAME_PREFIX="${NAME_PREFIX:-woltlab}"
    COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-wsc-local}"
    ADMIN_USER="${ADMIN_USER:-admin}"
    MYSQL_DATABASE="${MYSQL_DATABASE:-woltlab}"
    WSC_VERSION="${WSC_VERSION:-6.2.5}"
    WSC_SHA256="${WSC_SHA256:-a6727fa7e95f84737cda6fbcfcf72ba691fdb4be965281197d1cae7011c6ee19}"
    HTTP_PORT="${HTTP_PORT:-8080}"
    HTTPS_PORT="${HTTPS_PORT:-443}"
    MYSQL_PORT="${MYSQL_PORT:-3307}"
    PHPMYADMIN_PORT="${PHPMYADMIN_PORT:-8081}"
    MAILHOG_UI_PORT="${MAILHOG_UI_PORT:-8025}"
    MAILHOG_SMTP_PORT="${MAILHOG_SMTP_PORT:-1025}"
    PORTAINER_PORT="${PORTAINER_PORT:-9443}"
}

compose() {
    docker compose --project-directory "$ROOT" "$@"
}

cname() {
    echo "${NAME_PREFIX}-$1"
}

port_in_use() {
    local port="$1"
    if command -v ss >/dev/null 2>&1; then
        ss -ltn "sport = :$port" 2>/dev/null | grep -q ":$port"
    else
        netstat -ltn 2>/dev/null | grep -q ":$port "
    fi
}

container_exists() {
    docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$1"
}

container_running() {
    docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$1"
}

# Fremdes Portainer (nicht unser Prefix-Container)
foreign_portainer_running() {
    local ours
    ours="$(cname portainer)"
    while IFS= read -r name; do
        [[ -z "$name" ]] && continue
        [[ "$name" == "$ours" ]] && continue
        if [[ "$name" == *portainer* ]]; then
            return 0
        fi
    done < <(docker ps --format '{{.Names}}')
    # Port 9443 belegt von etwas anderem?
    if port_in_use "${PORTAINER_PORT:-9443}"; then
        if ! container_running "$ours"; then
            return 0
        fi
    fi
    return 1
}

require_docker() {
    docker info >/dev/null 2>&1 || die "$(msg 'Docker läuft nicht.' 'Docker is not running.')"
    docker compose version >/dev/null 2>&1 || die "$(msg 'docker compose fehlt.' 'docker compose is missing.')"
}

require_mkcert() {
    if ! command -v mkcert >/dev/null 2>&1; then
        msg "mkcert fehlt – Pflicht für https://wsc.local" "mkcert is required for https://wsc.local"
        msg "  Arch/CachyOS: sudo pacman -S mkcert" "  Arch/CachyOS: sudo pacman -S mkcert"
        msg "  siehe: https://github.com/FiloSottile/mkcert" "  see: https://github.com/FiloSottile/mkcert"
        exit 1
    fi
}

ensure_hosts() {
    if grep -qE '[[:space:]]wsc\.local([[:space:]]|$)' /etc/hosts 2>/dev/null; then
        return 0
    fi
    msg "Hinweis: Eintrag fehlt in /etc/hosts:" "Note: missing /etc/hosts entry:"
    msg "  127.0.0.1 wsc.local" "  127.0.0.1 wsc.local"
    if [[ "${YES:-0}" == "1" ]]; then
        return 0
    fi
    read -rp "$(msg 'Jetzt eintragen (sudo)? [j/N]: ' 'Add now (sudo)? [y/N]: ')" ans
    if [[ "$ans" =~ ^[jJyY]$ ]]; then
        echo '127.0.0.1 wsc.local' | sudo tee -a /etc/hosts >/dev/null
    fi
}

gen_portainer_password_file() {
    local pw="$1" out="$ROOT/var/portainer-admin-password"
    mkdir -p "$ROOT/var"
    local hash=""
    if command -v python3 >/dev/null 2>&1; then
        hash=$(ADMIN_PW="$pw" python3 - <<'PY' 2>/dev/null || true
import os
pw = os.environ["ADMIN_PW"]
try:
    import bcrypt
    print(bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=10)).decode(), end="")
except Exception:
    pass
PY
)
    fi
    if [[ -z "$hash" ]] && command -v htpasswd >/dev/null 2>&1; then
        hash=$(htpasswd -nbB admin "$pw" | cut -d: -f2)
    fi
    if [[ -z "$hash" ]]; then
        hash=$(docker run --rm httpd:2.4-alpine htpasswd -nbB admin "$pw" 2>/dev/null | cut -d: -f2)
    fi
    [[ -n "$hash" ]] || return 1
    # Portainer erwartet bcrypt-Hash ohne trailing newline-Probleme
    printf '%s' "$hash" >"$out"
    chmod 600 "$out"
}
