#!/usr/bin/env bash
# Schreibt wsc-dev-config-55.json für Unattended-Install
set -euo pipefail
# shellcheck source=/dev/null
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
load_env

[[ -n "${ADMIN_PASSWORD:-}" ]] || die "ADMIN_PASSWORD fehlt."
ADMIN_USER="${ADMIN_USER:-admin}"
EMAIL="${ADMIN_EMAIL:-${ADMIN_USER}@wsc.local}"

# Kein database.auto am Document-Root (WCF verbietet das) – DB kommt über WCFSETUP_*
python3 - "$ROOT/woltlab/wsc-dev-config-55.json" "$ADMIN_USER" "$ADMIN_PASSWORD" "$EMAIL" <<'PY'
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
    "user": [],
}
# "root" ist reserviert; "dev" wird vom Installer selbst angelegt
if user not in ("root", "dev"):
    cfg["user"].append({
        "username": user,
        "password": pw,
        "email": email,
    })
with open(path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")
print(path)
PY
