#!/usr/bin/env bash
# Shell-UI: Farben, Schritte, Spinner (TTY)
# Einbinden: source …/scripts/ui.sh

if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    BOLD='\033[1m'
    DIM='\033[2m'
    RESET='\033[0m'
    _UI_TTY=1
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; CYAN=''
    BOLD=''; DIM=''; RESET=''
    _UI_TTY=0
fi

OK="✓"
FAIL="✗"
WARN="⚠"
INFO="→"

_UI_SPIN_PID=""
_UI_SPIN_MSG=""

ui_header() {
    local title="$1"
    # Anzeige-Breite (Multibyte-sicher via wc -L), Rahmen dynamisch
    local w pad line
    w=$(printf '%s' "$title" | wc -L)
    pad=$((w + 4))
    line=$(printf '═%.0s' $(seq 1 "$pad"))
    echo ""
    echo -e "${CYAN}${BOLD}╔${line}╗${RESET}"
    echo -e "${CYAN}${BOLD}║${RESET}  ${BOLD}${title}${RESET}  ${CYAN}${BOLD}║${RESET}"
    echo -e "${CYAN}${BOLD}╚${line}╝${RESET}"
    echo ""
}

ui_section() {
    echo ""
    echo -e "${BOLD}${CYAN}─── $1 ───${RESET}"
    echo ""
}

ui_step() {
    local n="$1" total="$2" title="$3"
    echo ""
    echo -e "  ${BLUE}${BOLD}[${n}/${total}]${RESET} ${BOLD}${title}${RESET}"
}

ui_ok()   { echo -e "  ${GREEN}${OK}${RESET} $1"; }
ui_fail() { echo -e "  ${RED}${FAIL}${RESET} $1" >&2; }
ui_warn() { echo -e "  ${YELLOW}${WARN}${RESET} $1"; }
ui_info() { echo -e "  ${CYAN}${INFO}${RESET} $1"; }
ui_dim()  { echo -e "  ${DIM}$1${RESET}"; }

ui_kv() {
    local key="$1" val="$2"
    printf "  ${DIM}%-12s${RESET} %s\n" "$key" "$val"
}

ui_box_start() {
    echo -e "${GREEN}${BOLD}════════════════════════════════════════${RESET}"
}
ui_box_end() {
    echo -e "${GREEN}${BOLD}════════════════════════════════════════${RESET}"
}

# Spinner sauber beenden bei Ctrl+C / Exit
ui_cleanup() {
    if [[ -n "${_UI_SPIN_PID:-}" ]]; then
        kill "$_UI_SPIN_PID" 2>/dev/null || true
        _UI_SPIN_PID=""
        printf "\r\033[K" 2>/dev/null || true
    fi
}
trap ui_cleanup EXIT INT TERM

# Spinner: ui_spin_start "Text" … ui_spin_done "ok|fail" "Text"
ui_spin_start() {
    _UI_SPIN_MSG="$1"
    if [[ "$_UI_TTY" != "1" ]]; then
        echo -e "  ${CYAN}${INFO}${RESET} ${_UI_SPIN_MSG}"
        return 0
    fi
    (
        local frames=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏') i=0
        while true; do
            printf "\r  ${CYAN}%s${RESET} %s" "${frames[i]}" "$_UI_SPIN_MSG"
            i=$(( (i + 1) % ${#frames[@]} ))
            sleep 0.08
        done
    ) &
    _UI_SPIN_PID=$!
    disown "$_UI_SPIN_PID" 2>/dev/null || true
}

ui_spin_done() {
    local status="${1:-ok}" text="${2:-$_UI_SPIN_MSG}"
    if [[ -n "${_UI_SPIN_PID:-}" ]]; then
        kill "$_UI_SPIN_PID" 2>/dev/null || true
        wait "$_UI_SPIN_PID" 2>/dev/null || true
        _UI_SPIN_PID=""
        printf "\r\033[K"
    fi
    case "$status" in
        ok|OK) ui_ok "$text" ;;
        fail|FAIL) ui_fail "$text" ;;
        warn|WARN) ui_warn "$text" ;;
        *) ui_info "$text" ;;
    esac
}

# Lange Befehle mit Spinner: ui_run "Label" cmd args…
ui_run() {
    local label="$1"
    shift
    ui_spin_start "$label"
    local tmp rc
    tmp="$(mktemp)"
    set +e
    "$@" >"$tmp" 2>&1
    rc=$?
    set -e
    if [[ $rc -eq 0 ]]; then
        ui_spin_done ok "$label"
    else
        ui_spin_done fail "$label"
        [[ -s "$tmp" ]] && sed 's/^/    /' "$tmp" >&2
    fi
    rm -f "$tmp"
    return "$rc"
}
