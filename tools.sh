#!/usr/bin/env bash
# WoltLab – lokaler Dev-Stack (Start/Stop, Snapshots, Doctor)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

UI_SH="${SCRIPT_DIR}/scripts/ui.sh"
if [ -f "$UI_SH" ]; then
    # shellcheck source=/dev/null
    source "$UI_SH"
else
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
    BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'; BLUE='\033[0;34m'
    OK="✓"; FAIL="✗"; WARN="⚠"; INFO="ℹ"
    ui_header() { echo ""; echo -e "${CYAN}$1${RESET}"; echo ""; }
    ui_section() { echo ""; echo -e "${BOLD}${CYAN}─── $1 ───${RESET}"; echo ""; }
    ui_step() { echo ""; echo -e "  ${BLUE}${BOLD}[$1/$2]${RESET} ${BOLD}$3${RESET}"; }
    ui_ok()   { echo -e "  ${GREEN}${OK}${RESET} $1"; }
    ui_fail() { echo -e "${RED}${FAIL}${RESET} $1" >&2; }
    ui_warn() { echo -e "  ${YELLOW}${WARN}${RESET} $1"; }
    ui_info() { echo -e "  ${CYAN}${INFO}${RESET} $1"; }
fi

SNAPSHOT_DIR="./snapshots"
COMPOSE=(docker compose)

load_env() {
    if [ -f .env ]; then
        set -a
        # shellcheck disable=SC1091
        source .env
        set +a
    fi
    MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-root}"
    MYSQL_DATABASE="${MYSQL_DATABASE:-woltlab}"
}

print_urls() {
    ui_ok "WoltLab:     https://wsc.local"
    ui_ok "HTTP:        http://localhost:${HTTP_PORT:-8080}"
    ui_ok "phpMyAdmin:  http://localhost:${PHPMYADMIN_PORT:-8081}"
    ui_ok "MailHog:     http://localhost:${MAILHOG_UI_PORT:-8025}"
}

container_running() {
    docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$1"
}

stack_running() {
    container_running woltlab-web
}

status_dot() {
    if stack_running; then
        echo -e "${GREEN}● läuft${RESET}"
    else
        echo -e "${DIM}○ gestoppt${RESET}"
    fi
}

woltlab_network_name() {
    docker network ls --format '{{.Name}}' 2>/dev/null | grep -E '_woltlab-network$' | head -n1
}

veth_available() {
    [ -d /sys/module/veth ] && return 0
    command -v modinfo >/dev/null 2>&1 && modinfo veth >/dev/null 2>&1
}

docker_bridge_up() {
    local net_id br net_name
    net_name="$(woltlab_network_name)"
    [ -n "$net_name" ] || return 1
    net_id=$(docker network inspect "$net_name" --format '{{.Id}}' 2>/dev/null) || return 1
    br="br-${net_id:0:12}"
    ip link show "$br" 2>/dev/null | grep -q 'state UP'
}

woltlab_reachable() {
    local code
    code=$(curl -sk -o /dev/null -w '%{http_code}' --connect-timeout 3 --max-time 6 https://wsc.local/ 2>/dev/null || echo "000")
    case "$code" in
        200|301|302|303|401|403) return 0 ;;
        *) return 1 ;;
    esac
}

wait_for_mysql() {
    local i=0
    ui_info "Warte auf MySQL…"
    until docker exec woltlab-mysql mysqladmin ping -h 127.0.0.1 -uroot -p"${MYSQL_ROOT_PASSWORD}" --silent 2>/dev/null; do
        i=$((i + 1))
        if [ "$i" -gt 40 ]; then
            ui_fail "MySQL antwortet nicht rechtzeitig."
            return 1
        fi
        sleep 1
    done
    ui_ok "MySQL bereit."
}

repair_docker_network() {
    local net_name
    ui_warn "Docker-Bridge wird neu aufgebaut…"
    "${COMPOSE[@]}" down --remove-orphans >/dev/null 2>&1 || true
    net_name="$(woltlab_network_name)"
    [ -n "$net_name" ] && docker network rm "$net_name" >/dev/null 2>&1 || true
    sleep 1
    "${COMPOSE[@]}" up -d
}

create_snapshot() {
    load_env
    mkdir -p "${SNAPSHOT_DIR}"
    local stamp name path
    stamp=$(date +"%Y%m%d_%H%M%S")
    name="snapshot_${stamp}"
    path="${SNAPSHOT_DIR}/${name}"
    mkdir -p "${path}"

    ui_section "Snapshot erstellen"
    ui_step 1 3 "WoltLab-Dateien sichern"
    if [ -d ./woltlab ] && [ -n "$(ls -A ./woltlab 2>/dev/null || true)" ]; then
        tar -czf "${path}/woltlab_files.tar.gz" -C ./woltlab .
        ui_ok "Dateien gesichert."
    else
        ui_warn "Kein Inhalt in ./woltlab – leerer Snapshot-Teil."
        touch "${path}/woltlab_files.tar.gz"
    fi

    ui_step 2 3 "Datenbank exportieren"
    if ! container_running woltlab-mysql; then
        ui_warn "MySQL läuft nicht – starte zuerst den Stack (1 / ./tools.sh start)."
        : > "${path}/database.sql"
    elif ! docker exec woltlab-mysql mysqldump -u root -p"${MYSQL_ROOT_PASSWORD}" \
            --single-transaction --routines --triggers \
            "${MYSQL_DATABASE}" > "${path}/database.sql" 2>/dev/null; then
        ui_warn "Dump fehlgeschlagen (DB noch leer / Installation unvollständig?)."
        : > "${path}/database.sql"
    else
        ui_ok "Datenbank exportiert (${MYSQL_DATABASE})."
    fi

    ui_step 3 3 "Metadaten"
    {
        echo "Snapshot: ${name}"
        echo "Erstellt: $(date -Iseconds)"
        echo "Datenbank: ${MYSQL_DATABASE}"
        echo "Container:"
        docker ps --format '  - {{.Names}} ({{.Status}})' | grep woltlab || true
    } > "${path}/info.txt"

    ui_ok "Snapshot: ${path}"
}

restore_snapshot() {
    load_env
    mkdir -p "${SNAPSHOT_DIR}"

    ui_section "Snapshot wiederherstellen"
    mapfile -t snaps < <(find "${SNAPSHOT_DIR}" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
    if [ "${#snaps[@]}" -eq 0 ]; then
        ui_fail "Keine Snapshots vorhanden."
        return 1
    fi

    local i=1
    for s in "${snaps[@]}"; do
        echo -e "  ${GREEN}${i}${RESET}) ${s}"
        i=$((i + 1))
    done
    echo ""
    read -rp "$(echo -e "${YELLOW}→ Nummer:${RESET} ")" snapshot_num

    if ! [[ "${snapshot_num}" =~ ^[0-9]+$ ]] \
        || [ "${snapshot_num}" -lt 1 ] \
        || [ "${snapshot_num}" -gt "${#snaps[@]}" ]; then
        ui_fail "Ungültige Auswahl."
        return 1
    fi

    local snap_name snap_path
    snap_name="${snaps[$((snapshot_num - 1))]}"
    snap_path="${SNAPSHOT_DIR}/${snap_name}"

    ui_warn "Aktuelle Dateien und Datenbank werden überschrieben."
    read -rp "$(echo -e "${YELLOW}→ Fortfahren? (ja/nein):${RESET} ")" confirm
    if [ "${confirm}" != "ja" ]; then
        ui_info "Abgebrochen."
        return 0
    fi

    ui_step 1 4 "Container stoppen"
    "${COMPOSE[@]}" down

    ui_step 2 4 "Dateien wiederherstellen"
    mkdir -p ./woltlab
    find ./woltlab -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    if [ -s "${snap_path}/woltlab_files.tar.gz" ]; then
        tar -xzf "${snap_path}/woltlab_files.tar.gz" -C ./woltlab
        ui_ok "Dateien aus ${snap_name}"
    else
        ui_warn "Keine Dateien im Snapshot."
    fi

    ui_step 3 4 "Container starten"
    "${COMPOSE[@]}" up -d
    wait_for_mysql

    ui_step 4 4 "Datenbank wiederherstellen"
    if [ -s "${snap_path}/database.sql" ]; then
        docker exec woltlab-mysql mysql -u root -p"${MYSQL_ROOT_PASSWORD}" \
            -e "DROP DATABASE IF EXISTS \`${MYSQL_DATABASE}\`; CREATE DATABASE \`${MYSQL_DATABASE}\`;"
        docker exec -i woltlab-mysql mysql -u root -p"${MYSQL_ROOT_PASSWORD}" \
            "${MYSQL_DATABASE}" < "${snap_path}/database.sql"
        ui_ok "Datenbank wiederhergestellt."
    else
        ui_warn "Kein DB-Dump – Datenbank unverändert/leer."
    fi

    ui_ok "Fertig. ${snap_name}"
    print_urls
}

start_webserver() {
    load_env
    ui_section "Webserver starten"

    if [ ! -f certs/fullchain.pem ] || [ ! -f certs/privkey.pem ]; then
        ui_fail "HTTPS-Zertifikate fehlen (certs/fullchain.pem, certs/privkey.pem)."
        ui_info "Mit mkcert: ./scripts/generate-certs.sh"
        return 1
    fi

    if stack_running; then
        if ! docker_bridge_up || ! woltlab_reachable; then
            repair_docker_network
            sleep 4
            if woltlab_reachable; then
                ui_ok "Netzwerk repariert."
                print_urls
                return 0
            fi
            ui_warn "Reparatur gelaufen – prüfe Logs falls wsc.local weiter hängt."
            print_urls
            return 0
        fi
        ui_ok "Bereits gestartet."
        print_urls
        return 0
    fi

    if ! veth_available; then
        ui_fail "Kernel-Modul 'veth' fehlt – Docker-Bridge-Netzwerke gehen nicht."
        ui_info "Fix: Kernel mit veth booten, dann: sudo modprobe veth && sudo systemctl restart docker"
        return 1
    fi

    local start_log
    start_log="$(mktemp)"
    if "${COMPOSE[@]}" up -d >"$start_log" 2>&1; then
        ui_ok "Container gestartet."
        print_urls
        rm -f "$start_log"
        return 0
    fi

    ui_warn "Start fehlgeschlagen – versuche Netzwerk-Reparatur…"
    if grep -qi "failed to set up container networking\|network" "$start_log"; then
        "${COMPOSE[@]}" down --remove-orphans >/dev/null 2>&1 || true
        local net_name
        net_name="$(woltlab_network_name)"
        [ -n "$net_name" ] && docker network rm "$net_name" >/dev/null 2>&1 || true

        if "${COMPOSE[@]}" up -d >"$start_log" 2>&1; then
            ui_ok "Gestartet nach Netzwerk-Reparatur."
            print_urls
            rm -f "$start_log"
            return 0
        fi

        ui_warn "Fallback: ohne MailHog…"
        if "${COMPOSE[@]}" up -d database webserver phpmyadmin >"$start_log" 2>&1; then
            ui_ok "Core läuft (ohne MailHog)."
            print_urls
            rm -f "$start_log"
            return 0
        fi
    fi

    ui_fail "Start fehlgeschlagen:"
    sed 's/^/  /' "$start_log"
    rm -f "$start_log"
    return 1
}

stop_webserver() {
    ui_section "Webserver stoppen"
    "${COMPOSE[@]}" down
    ui_ok "Gestoppt."
}

status_webserver() {
    load_env
    ui_section "Status"
    echo -e "  Stack: $(status_dot)"
    echo ""
    "${COMPOSE[@]}" ps
    echo ""
    if stack_running; then
        if woltlab_reachable; then
            ui_ok "https://wsc.local erreichbar"
        else
            ui_warn "https://wsc.local nicht erreichbar (Hosts-Eintrag? Zertifikat?)"
        fi
        print_urls
    fi
}

list_snapshots() {
    mkdir -p "${SNAPSHOT_DIR}"
    ui_section "Snapshots"
    mapfile -t snaps < <(find "${SNAPSHOT_DIR}" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
    if [ "${#snaps[@]}" -eq 0 ]; then
        ui_warn "Keine Snapshots."
        return 0
    fi
    local s info size
    for s in "${snaps[@]}"; do
        size=$(du -sh "${SNAPSHOT_DIR}/${s}" 2>/dev/null | awk '{print $1}')
        info=""
        [ -f "${SNAPSHOT_DIR}/${s}/info.txt" ] && info=$(head -n1 "${SNAPSHOT_DIR}/${s}/info.txt")
        printf "  ${GREEN}•${RESET} %-28s  ${DIM}%5s${RESET}  %s\n" "$s" "$size" "$info"
    done
}

rebuild_webserver() {
    ui_section "Image neu bauen"
    ui_info "Nach Dockerfile-Änderungen (z. B. imagick)."
    "${COMPOSE[@]}" build --pull webserver
    "${COMPOSE[@]}" up -d webserver
    ui_ok "webserver neu gebaut und gestartet."
    print_urls
}

doctor() {
    load_env
    ui_section "Doctor"

    ui_step 1 5 "Docker"
    if docker info >/dev/null 2>&1; then
        ui_ok "Docker erreichbar"
    else
        ui_fail "Docker nicht erreichbar"
        return 1
    fi
    if veth_available; then
        ui_ok "veth verfügbar"
    else
        ui_warn "veth fehlt – Bridge-Netzwerke können scheitern"
    fi

    ui_step 2 5 "Dateien"
    [ -f .env ] && ui_ok ".env vorhanden" || ui_warn ".env fehlt – cp .env.example .env"
    [ -f certs/fullchain.pem ] && [ -f certs/privkey.pem ] \
        && ui_ok "TLS-Zertifikate vorhanden" \
        || ui_warn "Zertifikate fehlen – ./scripts/generate-certs.sh"
    [ -d woltlab ] && [ -n "$(ls -A woltlab 2>/dev/null || true)" ] \
        && ui_ok "woltlab/ hat Inhalt" \
        || ui_warn "woltlab/ leer – Suite-Dateien hierhin legen"

    ui_step 3 5 "Container"
    for c in woltlab-web woltlab-mysql woltlab-phpmyadmin woltlab-mailhog; do
        if container_running "$c"; then
            ui_ok "$c läuft"
        else
            ui_warn "$c gestoppt"
        fi
    done

    ui_step 4 5 "PHP-Erweiterungen (WoltLab)"
    if ! container_running woltlab-web; then
        ui_warn "webserver läuft nicht – Start nötig für Extension-Check"
    else
        local required missing
        required="ctype dom exif fileinfo gmp intl mbstring openssl pdo pdo_mysql zlib gd imagick"
        missing=""
        for ext in $required; do
            if docker exec woltlab-web php -m 2>/dev/null | grep -qi "^${ext}$"; then
                ui_ok "php-${ext}"
            else
                ui_fail "fehlt: ${ext}"
                missing=1
            fi
        done
        if docker exec woltlab-web php -r 'exit(function_exists("imagewebp")?0:1);' 2>/dev/null; then
            ui_ok "gd WebP"
        else
            ui_warn "gd ohne WebP (imagick mit WebP reicht laut WoltLab)"
        fi
        if docker exec woltlab-web php -r 'exit(extension_loaded("imagick") && count(Imagick::queryFormats("WEBP"))?0:1);' 2>/dev/null; then
            ui_ok "imagick WebP"
        else
            ui_warn "imagick ohne WebP oder nicht geladen"
        fi
        [ -z "${missing:-}" ] || ui_warn "Nach Dockerfile-Änderung: ./tools.sh rebuild"
    fi

    ui_step 5 5 "Erreichbarkeit"
    if stack_running && woltlab_reachable; then
        ui_ok "https://wsc.local antwortet"
    elif stack_running; then
        ui_warn "Stack läuft, wsc.local nicht erreichbar (Hosts: 127.0.0.1 wsc.local)"
    else
        ui_info "Stack gestoppt – Start mit ./tools.sh start"
    fi
}

run_menu_loop() {
    load_env
    while true; do
        ui_header "WoltLab lokal  $(status_dot)"

        echo -e "${BOLD}${CYAN}─── Stack ───${RESET}"
        echo -e "  ${GREEN}1${RESET}) Starten"
        echo -e "  ${GREEN}2${RESET}) Stoppen"
        echo -e "  ${GREEN}3${RESET}) Status & Links"
        echo -e "  ${GREEN}4${RESET}) Rebuild (Dockerfile / Extensions)"
        echo -e "  ${GREEN}5${RESET}) Doctor (Health-Check)"
        echo ""
        echo -e "${BOLD}${CYAN}─── Snapshots ───${RESET}"
        echo -e "  ${GREEN}6${RESET}) Erstellen"
        echo -e "  ${GREEN}7${RESET}) Wiederherstellen"
        echo -e "  ${GREEN}8${RESET}) Auflisten"
        echo ""
        echo -e "  ${GREEN}0${RESET}) Beenden"
        echo ""
        read -rp "$(echo -e "${YELLOW}→ Auswahl:${RESET} ")" choice

        case "$choice" in
            1) start_webserver ;;
            2) stop_webserver ;;
            3) status_webserver ;;
            4) rebuild_webserver ;;
            5) doctor ;;
            6) create_snapshot ;;
            7) restore_snapshot ;;
            8) list_snapshots ;;
            0|q|Q) echo ""; ui_ok "Tschüss."; exit 0 ;;
            *) ui_fail "Ungültige Auswahl." ;;
        esac

        echo ""
        read -rp "$(echo -e "${DIM}Enter für Menü…${RESET}")" _
    done
}

load_env

case "${1:-}" in
    start)   start_webserver ;;
    stop)    stop_webserver ;;
    status)  status_webserver ;;
    rebuild) rebuild_webserver ;;
    doctor)  doctor ;;
    repair)  repair_docker_network; sleep 4; status_webserver ;;
    create)  create_snapshot ;;
    restore) restore_snapshot ;;
    list)    list_snapshots ;;
    *)       run_menu_loop ;;
esac
