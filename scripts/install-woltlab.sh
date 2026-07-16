#!/usr/bin/env bash
# Unattended WoltLab-Installation via install.php?dev=1
set -euo pipefail
# shellcheck source=/dev/null
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
load_env

BASE="https://wsc.local"
COOKIE="$ROOT/var/install-cookies.txt"
mkdir -p "$ROOT/var"
rm -f "$COOKIE"

if [[ ! -f "$ROOT/woltlab/install.php" ]]; then
    if [[ -f "$ROOT/woltlab/global.php" ]]; then
        msg "✓ WoltLab scheint bereits installiert." "✓ WoltLab appears already installed."
        exit 0
    fi
    die "install.php fehlt – zuerst download-woltlab.sh ausführen."
fi

"$ROOT/scripts/write-dev-config.sh"

WEB="$(cname webserver)"
# container suffix is "web" not "webserver"
WEB="$(cname web)"
container_running "$WEB" || die "Container $WEB läuft nicht."

msg "⏳ Warte auf https://wsc.local …" "⏳ Waiting for https://wsc.local …"
for _ in $(seq 1 90); do
    code=$(curl -sk -o /dev/null -w '%{http_code}' --connect-timeout 2 "$BASE/" || echo 000)
    case "$code" in
        000|000000) sleep 1 ;;
        *) break ;;
    esac
done

msg "⚙ Starte Unattended-Install (dev=1)…" "⚙ Starting unattended install (dev=1)…"

for _ in $(seq 1 90); do
    [[ -f "$ROOT/woltlab/install.php" ]] || break
    curl -sk -c "$COOKIE" -b "$COOKIE" -L --max-redirs 8 \
        "${BASE}/install.php?dev=1" -o "$ROOT/var/install-last.html" 2>/dev/null || true
    # Worker-Requests (Paketinstallation)
    curl -sk -c "$COOKIE" -b "$COOKIE" -X POST \
        "${BASE}/install.php?dev=1" \
        -H 'X-Requested-With: XMLHttpRequest' \
        --data-urlencode 'dev=1' -o /dev/null 2>/dev/null || true
    if [[ -f "$ROOT/woltlab/global.php" ]] && [[ ! -f "$ROOT/woltlab/install.php" ]]; then
        break
    fi
    if grep -qiE 'acp/index|installation (completed|abgeschlossen)|willkommen bei' \
        "$ROOT/var/install-last.html" 2>/dev/null; then
        [[ ! -f "$ROOT/woltlab/install.php" ]] && break
    fi
    sleep 2
done

sleep 3

if [[ -f "$ROOT/woltlab/install.php" ]] && [[ ! -f "$ROOT/woltlab/global.php" ]]; then
    die "Installation nicht abgeschlossen. Manuell: ${BASE}/install.php?dev=1"
fi

msg "✓ Installer fertig." "✓ Installer finished."

msg "⚙ Setze Admin-Login (${ADMIN_USER})…" "⚙ Setting admin login (${ADMIN_USER})…"
# PHP-Skript in den Container schreiben und ausführen
cat >"$ROOT/var/set-admin.php" <<'PHP'
<?php
$_SERVER['DOCUMENT_ROOT'] = '/var/www/html';
chdir('/var/www/html');
require_once 'global.php';

use wcf\data\user\User;
use wcf\data\user\UserAction;

$username = getenv('ADMIN_USER') ?: 'admin';
$password = getenv('ADMIN_PASSWORD') ?: '';
$email = getenv('ADMIN_EMAIL') ?: ($username . '@wsc.local');
if ($password === '') {
    fwrite(STDERR, "ADMIN_PASSWORD empty\n");
    exit(1);
}

$user = new User(1);
if (!$user->userID) {
    fwrite(STDERR, "user 1 missing\n");
    exit(1);
}

(new UserAction([$user], 'update', [
    'data' => [
        'username' => $username,
        'email' => $email,
        'password' => $password,
    ],
]))->executeAction();

echo "OK\n";
PHP

docker cp "$ROOT/var/set-admin.php" "$WEB:/tmp/set-admin.php"
docker exec \
    -e "ADMIN_USER=${ADMIN_USER}" \
    -e "ADMIN_PASSWORD=${ADMIN_PASSWORD}" \
    -e "ADMIN_EMAIL=${ADMIN_EMAIL:-${ADMIN_USER}@wsc.local}" \
    "$WEB" php /tmp/set-admin.php \
    || msg "⚠ Admin-Update fehlgeschlagen – Login ggf. dev/root oder User aus Dev-Config." \
           "⚠ Admin update failed – try dev/root or Dev-Config user."

rm -f "$ROOT/woltlab/wsc-dev-config-55.json" "$ROOT/var/set-admin.php"
msg "✓ WoltLab bereit." "✓ WoltLab ready."
