#!/usr/bin/env bash
# Install missing local-development prerequisites in an interactive OS terminal.
set -euo pipefail
wsc_root="$(cd "$(dirname "$0")/.." && pwd)"
wsc_status=''
wsc_pause=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --status) wsc_status="$2"; shift 2 ;;
        --pause) wsc_pause=1; shift ;;
        --dry-run) echo 'Linux: native Python/mkcert/NSS packages; missing Docker via get.docker.com (Arch: native packages). macOS: Homebrew Python/mkcert/NSS and Docker Desktop. WSL2: Linux packages plus Windows winget helper. Then HTTPS trust and system check.'; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done
wsc_finish() {
    local code=$?
    trap - EXIT
    if [[ -n "$wsc_status" ]]; then printf '%s\n' "$code" > "$wsc_status"; fi
    if [[ "$wsc_pause" == 1 ]]; then read -r -p 'Terminal mit Eingabe schliessen / Press Enter to close. ' _ || true; fi
    exit "$code"
}
trap wsc_finish EXIT
wsc_sudo=()
if [[ "$EUID" != 0 ]]; then wsc_sudo=(sudo); fi
wsc_temp="$(mktemp -d)"
# Downloads are saved before execution; never pipe remote code into a shell.
wsc_download() { curl --proto '=https' --tlsv1.2 -fLsS "$1" -o "$2"; }
wsc_os="$(uname -s)"
if [[ "$wsc_os" == Darwin ]]; then
    if ! command -v brew >/dev/null; then
        if [[ -x /opt/homebrew/bin/brew ]]; then eval "$(/opt/homebrew/bin/brew shellenv)";
        elif [[ -x /usr/local/bin/brew ]]; then eval "$(/usr/local/bin/brew shellenv)";
        else
            wsc_download https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh "$wsc_temp/brew.sh"
            bash "$wsc_temp/brew.sh"
            if [[ -x /opt/homebrew/bin/brew ]]; then eval "$(/opt/homebrew/bin/brew shellenv)"; else eval "$(/usr/local/bin/brew shellenv)"; fi
        fi
    fi
    if ! python3 -c 'import sys; sys.exit(sys.version_info < (3,10))' 2>/dev/null; then brew install python; PATH="$(brew --prefix)/bin:${PATH}"; export PATH; fi
    command -v mkcert >/dev/null || brew install mkcert
    brew list nss >/dev/null 2>&1 || brew install nss
    if ! command -v docker >/dev/null && [[ ! -d /Applications/Docker.app ]]; then brew install --cask docker; fi
    open -a Docker
elif [[ "$wsc_os" == Linux ]]; then
    wsc_wsl=0
    if [[ -n "${WSL_DISTRO_NAME:-}" && "$(uname -r)" != *microsoft-standard* && "$(uname -r)" != *WSL2* ]]; then echo "WSL2 benoetigt: wsl --set-version NAME 2" >&2; exit 1; fi
    if [[ "$(uname -r)" == *[Mm]icrosoft* || -n "${WSL_DISTRO_NAME:-}" ]]; then wsc_wsl=1; fi
    if command -v apt-get >/dev/null; then
        wsc_packages=()
        for wsc_bin in python3 curl mkcert; do command -v "$wsc_bin" >/dev/null || wsc_packages+=("$wsc_bin"); done
        command -v certutil >/dev/null || wsc_packages+=(libnss3-tools)
        [[ -f /etc/ssl/certs/ca-certificates.crt ]] || wsc_packages+=(ca-certificates)
        if [[ ${#wsc_packages[@]} -gt 0 ]]; then
            "${wsc_sudo[@]}" apt-get update
            "${wsc_sudo[@]}" apt-get install -y "${wsc_packages[@]}"
        fi
    elif command -v dnf >/dev/null; then
        "${wsc_sudo[@]}" dnf install -y python3 curl ca-certificates mkcert nss-tools
    elif command -v pacman >/dev/null; then
        "${wsc_sudo[@]}" pacman -S --needed --noconfirm python curl ca-certificates mkcert nss
    else echo 'Automatische Einrichtung: apt, dnf oder pacman benoetigt. Anleitung: docs/platforms.md' >&2; exit 1; fi
    if [[ "$wsc_wsl" == 1 ]]; then
        command -v powershell.exe >/dev/null || { echo 'Windows-Integration fehlt. Install-wsc-local.ps1 in Windows starten.' >&2; exit 1; }
        wsc_win_script="$(wslpath -w "$wsc_root/Install-wsc-local.ps1")"
        powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$wsc_win_script" -WindowsPackagesOnly
    elif ! command -v docker >/dev/null; then
        if command -v pacman >/dev/null; then "${wsc_sudo[@]}" pacman -S --needed --noconfirm docker docker-compose;
        else wsc_download https://get.docker.com "$wsc_temp/docker.sh"; "${wsc_sudo[@]}" sh "$wsc_temp/docker.sh"; fi
        command -v systemctl >/dev/null && "${wsc_sudo[@]}" systemctl enable --now docker
    elif ! docker compose version >/dev/null 2>&1; then
        if command -v apt-get >/dev/null; then "${wsc_sudo[@]}" apt-get install -y docker-compose-plugin;
        elif command -v dnf >/dev/null; then "${wsc_sudo[@]}" dnf install -y docker-compose-plugin;
        else "${wsc_sudo[@]}" pacman -S --needed --noconfirm docker-compose; fi
    fi
    if [[ "$wsc_wsl" == 0 ]] && command -v systemctl >/dev/null && systemctl cat docker.service >/dev/null 2>&1; then
        "${wsc_sudo[@]}" systemctl start docker
        if [[ "$EUID" != 0 ]] && ! docker info >/dev/null 2>&1 && ! id -nG | tr ' ' '\n' | grep -qx docker; then
            "${wsc_sudo[@]}" usermod -aG docker "$(id -un)"
            echo 'Docker-Gruppe eingerichtet: abmelden und neu anmelden. Diese Gruppe entspricht administrativen Rechten.'
        fi
    fi
else echo 'Windows: Install-wsc-local.ps1 verwenden.' >&2; exit 1; fi
rm -rf "$wsc_temp"
python3 -c 'import sys; sys.exit(sys.version_info < (3,10))' || { echo 'Python 3.10+ fehlt noch. Anleitung: docs/platforms.md' >&2; exit 1; }
# Uses the same CA as Windows when running inside WSL2.
python3 - "$wsc_root" <<'PY'
import sys
sys.path.insert(0, sys.argv[1]+'/workbench')
from host_system import configure_trust, print_report
configure_trust()
print_report()
PY
printf '\nEinrichtung beendet. Systempruefung im Dashboard erneut starten.\nDocker Desktop: erste Freigabe und ggf. WSL-Integration bestaetigen.\n'
