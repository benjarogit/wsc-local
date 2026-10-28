"""Identify compatible dashboard assets and server code without loading secrets."""
from __future__ import annotations

import hashlib
from pathlib import Path


def panel_version() -> str:
    root = Path(__file__).resolve().parent.parent
    digest = hashlib.sha256()
    for name in (
        "VERSION",
        "panel/index.html", "panel/app.js", "panel/styles.css", "panel/theme.js", "panel/ui_helpers.js", "panel/i18n.js", "panel/locale-en.js", "panel/vendor/fontawesome/icons.svg",
        "scripts/panel_server.py", "scripts/panel_version.py",
        "workbench/cli.py", "workbench/profiles.json",
        "workbench/host_system.py", "workbench/launcher.py", "workbench/acp_login.py", "workbench/host_install.py",
        "scripts/install-host.sh", "Install-wsc-local.ps1",
    ):
        digest.update(name.encode())
        digest.update((root / name).read_bytes())
    return digest.hexdigest()[:12]


if __name__ == "__main__":
    print(panel_version())
