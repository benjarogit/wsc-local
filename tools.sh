#!/usr/bin/env bash
# wsc-local – Steuerung (Start/Stop, Snapshots, Doctor, Logs, …)
# Nur dieses Projekt (COMPOSE_PROJECT_NAME / NAME_PREFIX) – nie fremdes Docker.
set -euo pipefail
# shellcheck source=/dev/null
source "$(cd "$(dirname "$0")" && pwd)/scripts/lib.sh"
load_env

SNAPSHOT_DIR="$ROOT/snapshots"

print_urls() {
    ui_ok "WoltLab:     https://wsc.local"
    ui_ok "phpMyAdmin:  http://localhost:${PHPMYADMIN_PORT:-8081}"
    ui_ok "MailHog:     http://localhost:${MAILHOG_UI_PORT:-8025}"
    ui_dim "Panel:       ./panel.sh  →  http://127.0.0.1:${PANEL_PORT:-9099}"
    [[ -f "$ROOT/var/credentials.txt" ]] && ui_dim "Login:       var/credentials.txt"
}

stack_running() { container_running "$(cname web)"; }

# Alle Dienste dieses Projekts (nicht nur web)
all_services_running() {
    local s
    for s in web mysql phpmyadmin mailhog; do
        container_running "$(cname "$s")" || return 1
    done
    return 0
}

ensure_all_services_up() {
    # Fehlende Begleit-Dienste nachziehen (z. B. nach Rebuild/Repair)
    if ! all_services_running; then
        ui_info "Starte fehlende Dienste (phpMyAdmin, MailHog, …)…"
        compose_stack_up
        sleep 2
    fi
}

status_dot() {
    if all_services_running; then echo -e "${GREEN:-}● läuft${RESET:-}"
    elif stack_running; then echo -e "${YELLOW:-}● teilweise${RESET:-}"
    else echo -e "${DIM:-}○ gestoppt${RESET:-}"; fi
}

woltlab_network_name() {
    # Immer Exit 0 – sonst killt set -o pipefail den Repair, wenn grep nichts findet
    docker network ls --format '{{.Name}}' 2>/dev/null \
        | grep -E "_net$" | grep -E "${COMPOSE_PROJECT_NAME}|woltlab|wsc" | head -n1 || true
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
    until docker exec "$(cname mysql)" mysqladmin ping -h 127.0.0.1 -uroot -p"${MYSQL_ROOT_PASSWORD}" --silent >/dev/null 2>&1; do
        i=$((i + 1))
        [ "$i" -gt 40 ] && { ui_fail "MySQL antwortet nicht."; return 1; }
        sleep 1
    done
    ui_ok "MySQL bereit."
}

# Nur unser Compose-Projekt – nie docker system prune / fremde Container
compose_stack_up() { compose up -d; }
compose_stack_down() { compose down; }

repair_docker_network() {
    # Laien: „Verbindung reparieren“ – Stack kurz neu starten, wenn Site/Netz hakt
    ui_section "Verbindung reparieren"
    ui_warn "Container dieses Projekts werden kurz neu gestartet (Website kurz offline)."
    ui_dim "Fremdes Docker bleibt unberührt."
    compose_stack_down >/dev/null 2>&1 || true
    local net_name; net_name="$(woltlab_network_name)"
    if [ -n "$net_name" ]; then
        ui_info "Projekt-Netzwerk neu: ${net_name}"
        docker network rm "$net_name" >/dev/null 2>&1 || true
    fi
    sleep 1
    compose_stack_up || { ui_fail "Start nach Repair fehlgeschlagen."; return 1; }
    wait_for_mysql
    ensure_all_services_up
    local i
    for i in 1 2 3 4 5 6 7 8 9 10; do
        woltlab_reachable && break
        sleep 2
    done
    if all_services_running && woltlab_reachable; then
        ui_ok "Verbindung OK – alle Dienste laufen, Website erreichbar."
    elif all_services_running; then
        ui_warn "Dienste laufen, Website antwortet noch nicht – kurz warten oder erneut prüfen."
    else
        ui_fail "Nicht alle Dienste sind zurück. Tippe: Starten oder Prüfen."
        return 1
    fi
    print_urls
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
    if [ -n "$(find "$ROOT/woltlab" -mindepth 1 ! -name '.gitkeep' -print -quit 2>/dev/null)" ]; then
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
    {
        echo "Snapshot: ${name}"
        echo "Erstellt: $(date -Iseconds)"
        echo "Prefix: ${NAME_PREFIX}"
    } > "${path}/info.txt"
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
    local snap_name="${snaps[$((snapshot_num - 1))]}"
    local snap_path="${SNAPSHOT_DIR}/${snap_name}"
    ui_warn "Überschreibt aktuelle WoltLab-Dateien + DB dieses Projekts!"
    read -rp "$(echo -e "${YELLOW}→ Fortfahren? (ja/nein):${RESET} ")" confirm
    [ "${confirm}" = "ja" ] || { ui_info "Abgebrochen."; return 0; }
    _restore_snapshot_path "$snap_path"
}

_restore_snapshot_path() {
    local snap_path="$1"
    ui_step 1 4 "Stoppen"; compose_stack_down
    ui_step 2 4 "Dateien"; mkdir -p "$ROOT/woltlab"
    find "$ROOT/woltlab" -mindepth 1 -exec rm -rf {} + 2>/dev/null || true
    [ -s "${snap_path}/woltlab_files.tar.gz" ] && tar -xzf "${snap_path}/woltlab_files.tar.gz" -C "$ROOT/woltlab"
    ui_step 3 4 "Starten"; compose_stack_up; wait_for_mysql
    ui_step 4 4 "DB"
    if [ -s "${snap_path}/database.sql" ]; then
        docker exec "$(cname mysql)" mysql -u root -p"${MYSQL_ROOT_PASSWORD}" \
            -e "DROP DATABASE IF EXISTS \`${MYSQL_DATABASE}\`; CREATE DATABASE \`${MYSQL_DATABASE}\`;" >/dev/null 2>&1
        docker exec -i "$(cname mysql)" mysql -u root -p"${MYSQL_ROOT_PASSWORD}" \
            "${MYSQL_DATABASE}" < "${snap_path}/database.sql"
        ui_ok "DB wiederhergestellt."
    fi
    print_urls
}

delete_snapshot() {
    mkdir -p "${SNAPSHOT_DIR}"
    ui_section "Snapshot löschen"
    mapfile -t snaps < <(find "${SNAPSHOT_DIR}" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
    [ "${#snaps[@]}" -eq 0 ] && { ui_fail "Keine Snapshots."; return 1; }
    local i=1
    for s in "${snaps[@]}"; do echo -e "  ${GREEN}${i}${RESET}) ${s}"; i=$((i + 1)); done
    read -rp "$(echo -e "${YELLOW}→ Nummer:${RESET} ")" snapshot_num
    if ! [[ "${snapshot_num}" =~ ^[0-9]+$ ]] || [ "${snapshot_num}" -lt 1 ] || [ "${snapshot_num}" -gt "${#snaps[@]}" ]; then
        ui_fail "Ungültig."; return 1
    fi
    local snap_name="${snaps[$((snapshot_num - 1))]}"
    read -rp "$(echo -e "${YELLOW}→ „${snap_name}“ löschen? (ja/nein):${RESET} ")" confirm
    [ "${confirm}" = "ja" ] || { ui_info "Abgebrochen."; return 0; }
    rm -rf "${SNAPSHOT_DIR}/${snap_name}"
    ui_ok "Gelöscht: ${snap_name}"
}

list_snapshots() {
    mkdir -p "${SNAPSHOT_DIR}"
    ui_section "Snapshots"
    mapfile -t snaps < <(find "${SNAPSHOT_DIR}" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
    [ "${#snaps[@]}" -eq 0 ] && { ui_warn "Keine Snapshots."; return 0; }
    for s in "${snaps[@]}"; do
        local sz
        sz=$(du -sh "${SNAPSHOT_DIR}/${s}" 2>/dev/null | awk '{print $1}')
        printf "  ${GREEN}•${RESET} %s  ${DIM}(%s)${RESET}\n" "$s" "${sz:-?}"
    done
}

show_credentials() {
    ui_section "Zugangsdaten"
    if [[ -f "$ROOT/var/credentials.txt" ]]; then
        sed 's/^/  /' "$ROOT/var/credentials.txt"
    elif [[ -n "${ADMIN_USER:-}" ]]; then
        ui_kv "Benutzer" "$ADMIN_USER"
        ui_dim "Passwort steht in .env (ADMIN_PASSWORD)"
    else
        ui_warn "Keine Credentials – Setup ausführen."
    fi
    echo
    print_urls
}

show_logs() {
    ui_section "Logs"
    echo -e "  ${GREEN}1${RESET}) web  ${GREEN}2${RESET}) mysql  ${GREEN}3${RESET}) phpmyadmin  ${GREEN}4${RESET}) mailhog"
    read -rp "$(echo -e "${YELLOW}→ Service:${RESET} ")" n
    local svc=""
    case "$n" in
        1) svc=web ;; 2) svc=mysql ;; 3) svc=phpmyadmin ;; 4) svc=mailhog ;;
        *) ui_fail "Ungültig."; return 1 ;;
    esac
    container_running "$(cname "$svc")" || { ui_fail "$(cname "$svc") läuft nicht."; return 1; }
    ui_info "Letzte 80 Zeilen – Abbruch: Ctrl+C"
    docker logs --tail 80 -f "$(cname "$svc")"
}

start_webserver() {
    load_env
    ui_section "Webserver starten"
    [ -f "$ROOT/certs/fullchain.pem" ] || { ui_fail "Zerts fehlen – ./setup.sh oder ./scripts/generate-certs.sh"; return 1; }
    veth_available || { ui_fail "veth fehlt."; return 1; }

    if stack_running; then
        # web läuft, aber Begleitdienste fehlen oft nach Rebuild/Repair
        if ! all_services_running; then
            ensure_all_services_up
        fi
        if ! docker_bridge_up || ! woltlab_reachable; then
            repair_docker_network || return 1
            print_urls; return 0
        fi
        if all_services_running; then
            ui_ok "Läuft – alle Dienste sind an."
        else
            ui_warn "Teilweise gestartet – prüfe Status."
        fi
        print_urls; return 0
    fi

    compose_stack_up || { ui_fail "Start fehlgeschlagen."; return 1; }
    wait_for_mysql
    ensure_all_services_up
    ui_ok "Gestartet."
    print_urls
}

stop_webserver() {
    ui_section "Webserver stoppen"
    compose_stack_down
    ui_ok "Gestoppt. (Nur dieses Projekt – fremdes Docker unberührt.)"
}

status_webserver() {
    load_env
    ui_section "Status"
    echo -e "  Stack: $(status_dot)"
    echo -e "  Prefix: ${DIM}${NAME_PREFIX}${RESET}  Projekt: ${DIM}${COMPOSE_PROJECT_NAME}${RESET}"
    echo
    for s in web mysql phpmyadmin mailhog; do
        if container_running "$(cname "$s")"; then ui_ok "$(cname "$s")"
        elif container_exists "$(cname "$s")"; then ui_warn "$(cname "$s") gestoppt"
        else ui_dim "$(cname "$s") nicht angelegt"; fi
    done
    echo
    if stack_running; then
        woltlab_reachable && ui_ok "https://wsc.local erreichbar" || ui_warn "https://wsc.local nicht erreichbar"
        print_urls
    fi
}

rebuild_webserver() {
    ui_section "Website neu bauen"
    ui_info "Das kann einige Minuten dauern – bitte warten."
    compose build --pull webserver || { ui_fail "Build fehlgeschlagen."; return 1; }
    compose up -d webserver || { ui_fail "Start nach Build fehlgeschlagen."; return 1; }
    # Begleitdienste oft „vergessen“, wenn vorher nur web neu hochgefahren wurde
    ensure_all_services_up
    wait_for_mysql
    ui_ok "Neu gebaut und gestartet."
    print_urls
}

doctor() {
    load_env
    ui_section "Doctor"
    local issues=0
    ui_step 1 6 "Docker"
    if docker info >/dev/null 2>&1; then ui_ok "Docker OK"; else ui_fail "Docker fehlt"; issues=$((issues+1)); fi
    veth_available && ui_ok "veth" || { ui_warn "veth fehlt"; issues=$((issues+1)); }
    ui_step 2 6 "Projekt-Dateien"
    [ -f .env ] && ui_ok ".env" || { ui_warn ".env fehlt – ./setup.sh"; issues=$((issues+1)); }
    [ -f certs/fullchain.pem ] && ui_ok "TLS" || { ui_warn "TLS fehlt"; issues=$((issues+1)); }
    [ -f woltlab/global.php ] && ui_ok "WoltLab installiert" || ui_warn "WoltLab nicht installiert / incomplete"
    ui_step 3 6 "Container (nur unser Prefix)"
    for s in web mysql phpmyadmin mailhog; do
        if container_running "$(cname "$s")"; then ui_ok "$(cname "$s")"
        else ui_warn "$(cname "$s") gestoppt"; issues=$((issues+1)); fi
    done
    ui_step 4 6 "PHP-Extensions"
    if container_running "$(cname web)"; then
        for ext in ctype dom exif fileinfo gmp intl mbstring openssl pdo pdo_mysql zlib gd imagick; do
            if docker exec "$(cname web)" php -m 2>/dev/null | grep -qi "^${ext}$"; then
                ui_ok "php-${ext}"
            else
                ui_fail "fehlt: ${ext}"; issues=$((issues+1))
            fi
        done
    else
        ui_warn "web gestoppt – PHP-Check übersprungen"
    fi
    ui_step 5 6 "Erreichbarkeit"
    if stack_running && woltlab_reachable; then ui_ok "https://wsc.local"
    else ui_warn "nicht erreichbar / gestoppt"; issues=$((issues+1)); fi
    ui_step 6 6 "Fremdes Docker"
    ui_ok "Aktionen betreffen nur Projekt „${COMPOSE_PROJECT_NAME}“ / Prefix „${NAME_PREFIX}-*“"
    echo
    if [ "$issues" -eq 0 ]; then ui_ok "Keine Probleme gefunden."
    else ui_warn "${issues} Hinweis(e) – siehe oben."; fi
}

open_site() {
    xdg-open "https://wsc.local" >/dev/null 2>&1 &
    ui_ok "Browser: https://wsc.local"
}

run_menu_loop() {
    load_env
    while true; do
        ui_header "wsc-local  $(status_dot)"
        echo -e "${BOLD}${CYAN}─── Alltag ───${RESET}"
        echo -e "  ${GREEN}1${RESET}) Starten     ${GREEN}2${RESET}) Stoppen     ${GREEN}3${RESET}) Status"
        echo -e "  ${GREEN}4${RESET}) Neu bauen   ${GREEN}5${RESET}) Prüfen      ${GREEN}6${RESET}) Protokoll"
        echo -e "  ${GREEN}7${RESET}) Login/URLs  ${GREEN}8${RESET}) Website öffnen  ${GREEN}9${RESET}) Verbindung reparieren"
        echo -e "${BOLD}${CYAN}─── Sicherungen ───${RESET}"
        echo -e "  ${GREEN}10${RESET}) Erstellen  ${GREEN}11${RESET}) Wiederherstellen"
        echo -e "  ${GREEN}12${RESET}) Auflisten  ${GREEN}13${RESET}) Löschen"
        echo -e "${BOLD}${CYAN}─── Einfach ───${RESET}"
        echo -e "  ${GREEN}14${RESET}) Browser-Panel öffnen"
        echo -e "  ${GREEN}15${RESET}) Desktop-Eintrag installieren"
        echo -e "  ${GREEN}0${RESET}) Beenden"
        read -rp "$(echo -e "${YELLOW}→ Auswahl:${RESET} ")" choice
        case "$choice" in
            1) start_webserver ;; 2) stop_webserver ;; 3) status_webserver ;;
            4) rebuild_webserver ;; 5) doctor ;; 6) show_logs ;;
            7) show_credentials ;; 8) open_site ;; 9) repair_docker_network; sleep 2; status_webserver ;;
            10) create_snapshot ;; 11) restore_snapshot ;; 12) list_snapshots ;; 13) delete_snapshot ;;
            14) "$ROOT/panel.sh" ;;
            15) "$ROOT/scripts/install-desktop.sh" ;;
            0|q|Q) ui_ok "Tschüss."; exit 0 ;;
            *) ui_fail "Ungültig." ;;
        esac
        read -rp "$(echo -e "${DIM}Enter…${RESET}")" _
    done
}

usage() {
    cat <<EOF
Usage: ./tools.sh [Befehl]

  start | stop | status | rebuild | doctor | repair
  logs | urls | open
  create | restore | list | delete     (Snapshots)

Ohne Argument: interaktives Menü.
Nur dieses Projekt – fremdes Docker wird nie angefasst.

Für Laien einfacher: ./panel.sh  oder Desktop „wsc-local“
  ./scripts/install-desktop.sh
EOF
}

case "${1:-}" in
    start) start_webserver ;;
    stop) stop_webserver ;;
    status) status_webserver ;;
    rebuild) rebuild_webserver ;;
    doctor) doctor ;;
    repair) repair_docker_network; sleep 4; status_webserver ;;
    logs) show_logs ;;
    urls|credentials) show_credentials ;;
    open) open_site ;;
    create) create_snapshot ;;
    restore) restore_snapshot ;;
    list) list_snapshots ;;
    delete) delete_snapshot ;;
    -h|--help|help) usage ;;
    "") run_menu_loop ;;
    *) usage; exit 1 ;;
esac
