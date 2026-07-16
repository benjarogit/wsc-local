#!/usr/bin/env bash
# Schreibt wsc-dev-config-55.json für Unattended-Install
set -euo pipefail
# shellcheck source=/dev/null
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
load_env

[[ -n "${ADMIN_PASSWORD:-}" ]] || die "ADMIN_PASSWORD fehlt."
ADMIN_USER="${ADMIN_USER:-admin}"
EMAIL="${ADMIN_EMAIL:-${ADMIN_USER}@wsc.local}"

mkdir -p "$ROOT/var"
OUT="$ROOT/var/wsc-dev-config-55.json"

# Kein database.auto am Document-Root – DB kommt über WCFSETUP_*
python3 - "$OUT" "$ADMIN_USER" "$ADMIN_PASSWORD" "$EMAIL" <<'PY'
import json, sys
path, user, pw, email = sys.argv[1:5]
cfg = {
    "setup": {
        "useDefaultInstallPath": True,
        "forceStaticCookiePrefix": True,
    },
    "configuration": {
        "option": {
            "captcha_type": "",
            "module_cookie_policy_page": "0",
        }
    },
    # Admin-Login wird nach der Installation gesetzt (set-admin.php).
    # Zusätzliche User hier würden die Paket-Installation stören.
    "user": [],
}
with open(path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")
PY

WEB="$(cname web)"
if container_running "$WEB"; then
    docker cp "$OUT" "$WEB:/var/www/html/wsc-dev-config-55.json" >/dev/null
    docker exec "$WEB" chown www-data:www-data /var/www/html/wsc-dev-config-55.json
else
    cp -f "$OUT" "$ROOT/woltlab/wsc-dev-config-55.json"
fi
