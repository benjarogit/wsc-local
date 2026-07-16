#!/usr/bin/env bash
# WoltLab – lokaler Dev-Stack (Start/Stop, Snapshots, Doctor)
set -euo pipefail
# shellcheck source=/dev/null
source "$(cd "$(dirname "$0")" && pwd)/scripts/lib.sh"
load_env

SNAPSHOT_DIR="$ROOT/snapshots"

print_urls() {
    ui_ok "WoltLab:     https://wsc.local"
    ui_ok "HTTP:        http://localhost:${HTTP_PORT:-8080}"
    ui_ok "phpMyAdmin:  http://localhost:${PHPMYADMIN_PORT:-8081}"
    ui_ok "MailHog:     http://localhost:${MAILHOG_UI_PORT:-8025}"
}

stack_running() { container_running "$(cname web)"; }

status_dot() {
    if stack_running; then echo -e "${GREEN:-}● läuft${RESET:-}"
    else echo -e "${DIM:-}○ gestoppt${RESET:-}"; fi
}

woltlab_network_name() {
    docker network ls --format '{{.Name}}' 2>/dev/null | grep -E "_net$" | grep -E "${COMPOSE_PROJECT_NAME}|woltlab|wsc" | head -n1
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
    case "$code" in 200|301|302|303|401|403) return 0 ;; *) return 1 ;; esac
}

wait_for_mysql() {
    local i=0
    ui_info "Warte auf MySQL…"
    until docker exec "$(cname mysql)" mysqladmin ping -h 127.0.0.1 -uroot -p"${MYSQL_ROOT_PASSWORD}" --silent 2>/dev/null; do
        i=$((i + 1))
        [ "$i" -gt 40 ] && { ui_fail "MySQL antwortet nicht."; return 1; }
        sleep 1
    done
    ui_ok "MySQL bereit."
}

repair_docker_network() {
    ui_warn "Docker-Bridge wird neu aufgebaut…"
    compose down --remove-orphans >/dev/null 2>&1 || true
    local net_name; net_name="$(woltlab_network_name)"
    [ -n "$net_name" ] && docker network rm "$net_name" >/dev/null 2>&1 || true
    sleep 1
    compose up -d
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
    if [ -d "$ROOT/woltlab" ] && [ -n "$(ls -A "$ROOT/woltlab" 2>/dev/null | grep -v gitkeep || true)" ]; then
        tar -czf "${path}/woltlab_files.tar.gz" -C "$ROOT/woltlab" .
        ui_ok "Dateien gesichert."
    else
        ui_warn "Kein Inhalt in ./woltlab"
        : > "${path}/woltlab_files.tar.gz"
    fi
    ui_step 2 3 "Datenbank exportieren"
    if ! container_running "$(cname mysql)"; then
        ui_warn "MySQL läuft nicht."
        : > "${path}/database.sql"
    elif ! docker exec "$(cname mysql)" mysqldump -u root -p"${MYSQL_ROOT_PASSWORD}" \
            --single-transaction --routines --triggers \
            "${MYSQL_DATABASE}" > "${path}/database.sql" 2>/dev/null; then
        ui_warn "Dump fehlgeschlagen."
        : > "${path}/database.sql"
    else
        ui_ok "DB exportiert."
    fi
    ui_step 3 3 "Metadaten"
    { echo "Snapshot: ${name}"; echo "Erstellt: $(date -Iseconds)"; } > "${path}/info.txt"
    ui_ok "Snapshot: ${path}"
}

restore_snapshot() {
    load_env
    mkdir -p "${SNAPSHOT_DIR}"
    ui_section "Snapshot wiederherstellen"
    mapfile -t snaps < <(find "${SNAPSHOT_DIR}" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
    [ "${#snaps[@]}" -eq 0 ] && { ui_fail "Keine Snapshots."; return 1; }
    local i=1
    for s in "${snaps[@]}"; do echo -e "  ${GREEN}${i}${RESET}) ${s}"; i=$((i + 1)); done
    read -rp "$(echo -e "${YELLOW}→ Nummer:${RESET} ")" snapshot_num
    if ! [[ "${snapshot_num}" =~ ^[0-9]+$ ]] || [ "${snapshot_num}" -lt 1 ] || [ "${snapshot_num}" -gt "${#snaps[@]}" ]; then
        ui_fail "Ungültig."; return 1
    fi
    local snap_name="${snaps[$((snapshot_num - 1))]}" snap_path="${SNAPSHOT_DIR}/${snap_name}"
    ui_warn "Überschreibt aktuelle Daten!"
    read -rp "$(echo -e "${YELLOW}→ Fortfahren? (ja/nein):${RESET} ")" confirm
    [ "${confirm}" = "ja" ] || { ui_info "Abgebrochen."; return 0; }
    ui_step 1 4 "Stoppen"; compose down
    ui_step 2 4 "Dateien"; mkdir -p "$ROOT/woltlab"
    find "$ROOT/woltlab" -mindepth 1 -exec rm -rf {} + 2>/dev/null || true
    [ -s "${snap_path}/woltlab_files.tar.gz" ] && tar -xzf "${snap_path}/woltlab_files.tar.gz" -C "$ROOT/woltlab"
    ui_step 3 4 "Starten"; compose up -d; wait_for_mysql
    ui_step 4 4 "DB"
    if [ -s "${snap_path}/database.sql" ]; then
        docker exec "$(cname mysql)" mysql -u root -p"${MYSQL_ROOT_PASSWORD}" \
            -e "DROP DATABASE IF EXISTS \`${MYSQL_DATABASE}\`; CREATE DATABASE \`${MYSQL_DATABASE}\`;"
        docker exec -i "$(cname mysql)" mysql -u root -p"${MYSQL_ROOT_PASSWORD}" \
            "${MYSQL_DATABASE}" < "${snap_path}/database.sql"
        ui_ok "DB wiederhergestellt."
    fi
    print_urls
}

start_webserver() {
    load_env
    ui_section "Webserver starten"
    [ -f "$ROOT/certs/fullchain.pem" ] || { ui_fail "Zerts fehlen – ./scripts/generate-certs.sh"; return 1; }
    if stack_running; then
        if ! docker_bridge_up || ! woltlab_reachable; then
            repair_docker_network; sleep 4
        fi
        ui_ok "Bereits gestartet / repariert."
        print_urls; return 0
    fi
    veth_available || { ui_fail "veth fehlt."; return 1; }
    compose up -d && ui_ok "Gestartet." && print_urls
}

stop_webserver() {
    ui_section "Webserver stoppen"
    compose down
    ui_ok "Gestoppt."
}

status_webserver() {
    load_env
    ui_section "Status"
    echo -e "  Stack: $(status_dot)"
    compose ps
    stack_running && print_urls
}

list_snapshots() {
    mkdir -p "${SNAPSHOT_DIR}"
    ui_section "Snapshots"
    mapfile -t snaps < <(find "${SNAPSHOT_DIR}" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
    [ "${#snaps[@]}" -eq 0 ] && { ui_warn "Keine Snapshots."; return 0; }
    for s in "${snaps[@]}"; do
        printf "  ${GREEN}•${RESET} %s\n" "$s"
    done
}

rebuild_webserver() {
    ui_section "Image neu bauen"
    compose build --pull webserver
    compose up -d webserver
    ui_ok "Fertig."; print_urls
}

doctor() {
    load_env
    ui_section "Doctor"
    ui_step 1 5 "Docker"
    docker info >/dev/null 2>&1 && ui_ok "Docker OK" || ui_fail "Docker fehlt"
    veth_available && ui_ok "veth" || ui_warn "veth fehlt"
    ui_step 2 5 "Dateien"
    [ -f .env ] && ui_ok ".env" || ui_warn ".env fehlt"
    [ -f certs/fullchain.pem ] && ui_ok "TLS" || ui_warn "TLS fehlt"
    ui_step 3 5 "Container"
    for s in web mysql phpmyadmin mailhog; do
        container_running "$(cname "$s")" && ui_ok "$(cname "$s")" || ui_warn "$(cname "$s") gestoppt"
    done
    ui_step 4 5 "PHP-Extensions"
    if container_running "$(cname web)"; then
        for ext in ctype dom exif fileinfo gmp intl mbstring openssl pdo pdo_mysql zlib gd imagick; do
            docker exec "$(cname web)" php -m 2>/dev/null | grep -qi "^${ext}$" && ui_ok "php-${ext}" || ui_fail "fehlt: ${ext}"
        done
    else
        ui_warn "web gestoppt"
    fi
    ui_step 5 5 "Erreichbarkeit"
    stack_running && woltlab_reachable && ui_ok "https://wsc.local" || ui_warn "nicht erreichbar / gestoppt"
}

run_menu_loop() {
    load_env
    while true; do
        ui_header "WoltLab lokal  $(status_dot)"
        echo -e "${BOLD}${CYAN}─── Stack ───${RESET}"
        echo -e "  ${GREEN}1${RESET}) Starten  ${GREEN}2${RESET}) Stoppen  ${GREEN}3${RESET}) Status"
        echo -e "  ${GREEN}4${RESET}) Rebuild  ${GREEN}5${RESET}) Doctor"
        echo -e "${BOLD}${CYAN}─── Snapshots ───${RESET}"
        echo -e "  ${GREEN}6${RESET}) Erstellen  ${GREEN}7${RESET}) Wiederherstellen  ${GREEN}8${RESET}) Auflisten"
        echo -e "  ${GREEN}0${RESET}) Beenden"
        read -rp "$(echo -e "${YELLOW}→ Auswahl:${RESET} ")" choice
        case "$choice" in
            1) start_webserver ;; 2) stop_webserver ;; 3) status_webserver ;;
            4) rebuild_webserver ;; 5) doctor ;;
            6) create_snapshot ;; 7) restore_snapshot ;; 8) list_snapshots ;;
            0|q|Q) ui_ok "Tschüss."; exit 0 ;;
            *) ui_fail "Ungültig." ;;
        esac
        read -rp "$(echo -e "${DIM}Enter…${RESET}")" _
    done
}

case "${1:-}" in
    start) start_webserver ;;
    stop) stop_webserver ;;
    status) status_webserver ;;
    rebuild) rebuild_webserver ;;
    doctor) doctor ;;
    repair) repair_docker_network; sleep 4; status_webserver ;;
    create) create_snapshot ;;
    restore) restore_snapshot ;;
    list) list_snapshots ;;
    *) run_menu_loop ;;
esac
