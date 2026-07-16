#!/usr/bin/env bash
# Unattended WoltLab-Installation via install.php?dev=1
set -euo pipefail
# shellcheck source=/dev/null
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
load_env

BASE="https://wsc.local"
[[ "${HTTPS_PORT:-443}" != "443" ]] && BASE="https://wsc.local:${HTTPS_PORT}"
mkdir -p "$ROOT/var"

if [[ ! -f "$ROOT/woltlab/install.php" ]]; then
    if [[ -f "$ROOT/woltlab/global.php" ]]; then
        ui_ok "WoltLab bereits installiert."
        exit 0
    fi
    die "install.php fehlt – zuerst download-woltlab.sh ausführen."
fi

WEB="$(cname web)"
container_running "$WEB" || die "Container $WEB läuft nicht."

"$ROOT/scripts/write-dev-config.sh"

for _ in $(seq 1 90); do
    code=$(curl -sk -o /dev/null -w '%{http_code}' --connect-timeout 2 "$BASE/" || echo 000)
    case "$code" in
        000|000000) sleep 1 ;;
        *) break ;;
    esac
done

docker exec "$WEB" bash -c 'chown -R www-data:www-data /var/www/html && chmod -R a+rwX /var/www/html' \
    >/dev/null 2>&1 || true

python3 - "$BASE" "$ROOT/var/install-last.html" "$ROOT/woltlab" <<'PY' || die "Installer-Fehler – siehe var/install-last.html"
import json, re, os, ssl, sys, time, urllib.request, urllib.parse, http.cookiejar

base, out, wdir = sys.argv[1], sys.argv[2], sys.argv[3]
install_php = os.path.join(wdir, "install.php")

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(
    urllib.request.HTTPSHandler(context=ctx),
    urllib.request.HTTPCookieProcessor(cj),
)

def attr(tag, name):
    m = re.search(name + r'="([^"]*)"', tag)
    return m.group(1) if m else None

def parse(html):
    title = re.search(r"<title>([^<]*)</title>", html)
    form = re.search(r'<form[^>]*action="([^"]*)"[^>]*>(.*?)</form>', html, re.S | re.I)
    fields, action = {}, None
    if form:
        action = form.group(1)
        for tag in re.findall(r"<input[^>]*>", form.group(2)):
            n = attr(tag, "name")
            if n is not None:
                fields[n] = attr(tag, "value") or ""
        for name, body in re.findall(r'<select[^>]*name="([^"]*)"[^>]*>(.*?)</select>', form.group(2), re.S):
            opts = re.findall(r'<option[^>]*value="([^"]*)"', body)
            fields[name] = opts[0] if opts else ""
    return (title.group(1) if title else ""), action, fields

def fatal(html):
    m = re.search(r"Fatal Error:[^<\n]*", html)
    return m.group(0) if m else None

def fetch(url, data=None, ajax=False):
    headers = {"User-Agent": "wsc-local-setup"}
    if ajax:
        headers["X-Requested-With"] = "XMLHttpRequest"
    req = urllib.request.Request(url, data=data, headers=headers)
    return op.open(req, timeout=300).read().decode("utf-8", "ignore")

def xsrf_token():
    for c in cj:
        if c.name == "XSRF-TOKEN":
            return urllib.parse.unquote(c.value)
    return None

def ajax_post(path, fields):
    token = xsrf_token()
    if not token:
        raise RuntimeError("XSRF-TOKEN fehlt – ACP-Session nicht aktiv")
    url = base + path + ("&" if "?" in path else "?") + "t=" + urllib.parse.quote(token, safe="")
    data = urllib.parse.urlencode(fields).encode()
    body = fetch(url, data, ajax=True)
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        m = re.search(r"Fatal Error:[^<]+", body)
        raise RuntimeError(m.group(0) if m else body[:500])

html = fetch(base + "/install.php?dev=1&languageCode=en")
open(out, "w").write(html)

for i in range(600):
    if not os.path.exists(install_php):
        break
    fe = fatal(html)
    if fe and "Permission denied" not in fe:
        sys.stderr.write(fe + "\n")
        sys.exit(1)
    title, action, fields = parse(html)
    if not action or "install.php" not in action or not fields:
        break
    data = urllib.parse.urlencode(fields).encode()
    html = fetch(base + "/" + action.lstrip("/"), data)
    open(out, "w").write(html)
    m = re.search(r"(\d+)%", title or "")
    pct = m.group(1) if m else "?"
    if sys.stdout.isatty():
        print(f"\r  Setup … {pct}%", end="", flush=True)
    elif pct in ("50", "95"):
        print(f"  Setup … {pct}%", flush=True)
    time.sleep(0.15)

if sys.stdout.isatty():
    print(flush=True)
if not os.path.exists(os.path.join(wdir, "global.php")):
    sys.stderr.write("global.php fehlt nach Phase 1\n")
    sys.exit(1)

# Phase 2 – wie der Browser: ACP-Session + install-package AJAX
print("  Kernpaket …", end="", flush=True)
fetch(base + "/acp/index.php?action=WCFSetup")
if not xsrf_token():
    sys.stderr.write("\nKeine ACP-Session nach installPackages\n")
    sys.exit(1)

payload = ajax_post("/acp/index.php?install-package/", {"queueID": 1, "step": "prepare"})
step = payload.get("step")
node = payload.get("node")
queue_id = payload.get("queueID", 1)
guard = 0

while step == "install" and node:
    payload = ajax_post(
        "/acp/index.php?install-package/",
        {"queueID": queue_id, "step": "install", "node": node},
    )
    step = payload.get("step")
    node = payload.get("node")
    queue_id = payload.get("queueID", queue_id)
    guard += 1
    if guard % 10 == 0:
        print(".", end="", flush=True)
    if guard > 800:
        sys.stderr.write("\nZu viele Installations-Nodes\n")
        sys.exit(1)

if step != "success":
    sys.stderr.write(f"\nKernpaket nicht fertig (step={step})\n")
    sys.exit(1)

print(" fertig", flush=True)
sys.exit(0)
PY

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

docker cp "$ROOT/var/set-admin.php" "$WEB:/tmp/set-admin.php" >/dev/null
if docker exec \
    -e "ADMIN_USER=${ADMIN_USER}" \
    -e "ADMIN_PASSWORD=${ADMIN_PASSWORD}" \
    -e "ADMIN_EMAIL=${ADMIN_EMAIL:-${ADMIN_USER}@wsc.local}" \
    "$WEB" php /tmp/set-admin.php >/dev/null; then
    ui_ok "Admin-Login gesetzt (${ADMIN_USER})"
else
    ui_warn "Admin-Update fehlgeschlagen – Login ggf. dev/root."
fi

docker exec "$WEB" rm -f \
    /var/www/html/wsc-dev-config-55.json \
    /tmp/set-admin.php 2>/dev/null || true
rm -f "$ROOT/var/set-admin.php" "$ROOT/var/wsc-dev-config-55.json"
