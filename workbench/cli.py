"""Project manager shared by the CLI and the local dashboard."""
from __future__ import annotations

import argparse
import http.cookiejar
import hashlib
import html
import http.client
from html.parser import HTMLParser
import io
import json
import locale
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from host_system import detect_host, print_report, tls_environment

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("WSC_LOCAL_HOME", Path.home() / ".local/share/wsc-local")).expanduser()
PROJECTS = DATA / "projects"
SECRETS = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "wsc-local/secrets"
PROFILES = json.loads((ROOT / "workbench/profiles.json").read_text(encoding="utf-8"))["profiles"]
HANDBOOK = "https://manual.woltlab.com/de/"


def instance_paths(name: str) -> tuple[Path, Path]:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}", name):
        raise ValueError("Name muss mit Kleinbuchstaben/Zahl beginnen und darf nur Kleinbuchstaben, Zahlen und - enthalten.")
    root = PROJECTS / name
    secret = SECRETS / f"{name}.env"
    return root, secret


def read_project(name: str) -> tuple[dict[str, Any], Path, Path]:
    root, secret = instance_paths(name)
    config_path = root / "wsc-local.json"
    if not config_path.is_file():
        raise ValueError(f"Projekt '{name}' nicht gefunden. Vorhandene Projekte mit 'wsc list' anzeigen.")
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    return cfg, root, secret


def compose(name: str, *args: str, timeout: int = 900, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    cfg, root, secret = read_project(name)
    if not secret.is_file():
        raise ValueError(f"Lokale Geheimnisse fehlen für '{name}'.")
    generated = compose_text(root, cfg)
    compose_file = root / "compose.yaml"
    if not compose_file.is_file() or compose_file.read_text(encoding="utf-8") != generated:
        compose_file.write_text(generated, encoding="utf-8")
    # The panel may inherit COMPOSE_PROJECT_NAME from the legacy stack. Pin
    # every Workbench command to this instance's project so status and actions
    # cannot accidentally target that shared stack.
    # Include optional services when stopping or removing the whole project.
    # Compose otherwise leaves containers behind for inactive profiles.
    lifecycle_profiles = ["--profile", "*"] if args and args[0] in {"down", "stop"} else []
    cmd = ["docker", "compose", "--project-name", cfg["project"], "--project-directory", str(root), "--env-file", str(secret), "-f", str(compose_file), *lifecycle_profiles, *args]
    # Compose interpolation gives exported process variables precedence over
    # --env-file. The dashboard can inherit ports from the legacy stack (for
    # example HTTPS_PORT=443), so the instance's secret env file must win.
    env = os.environ.copy()
    env.update(line.split("=", 1) for line in secret.read_text(encoding="utf-8").splitlines() if "=" in line)
    return subprocess.run(cmd, cwd=root, env=env, input=input_text, text=True, capture_output=True, timeout=timeout, check=False)


def profile_for(suite: str) -> dict[str, Any]:
    suite = suite.removeprefix("WSC ")
    for profile in PROFILES:
        if profile["suite"] == suite:
            return profile
    raise ValueError("Unterstützte Profile sind WSC 5.5 bis 6.2 sowie das experimentelle Entwicklungsprofil 6.3.")


def compose_text(root: Path, cfg: dict[str, Any]) -> str:
    # All bind paths are absolute to keep Compose independent of the caller's working directory.
    site = root / "site"
    db = root / "data/database"
    mysql = cfg.get("database", "mariadb") == "mysql8"
    db_image = "mysql:8.0" if mysql else "mariadb:10.11"
    db_health = 'test: ["CMD-SHELL", "mysqladmin ping -h 127.0.0.1 -uroot -p$$MYSQL_ROOT_PASSWORD --silent"]' if mysql else 'test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]'
    db_environment = """      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}""" if mysql else """      MARIADB_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MARIADB_DATABASE: ${MYSQL_DATABASE}
      MARIADB_USER: ${MYSQL_USER}
      MARIADB_PASSWORD: ${MYSQL_PASSWORD}"""
    if cfg.get("webserver", "nginx-php-fpm") == "apache":
        web_services = f'''  web:
    build:
      context: {ROOT.as_posix()}/workbench/runtime/apache
      args:
        PHP_VERSION: {cfg["php_version"]}
    ports:
      - "127.0.0.1:${{HTTP_PORT}}:80"
      - "127.0.0.1:${{HTTPS_PORT}}:443"
    volumes:
      - {site.as_posix()}:/var/www/html
      - {root.as_posix()}/config/php.ini:/usr/local/etc/php/conf.d/99-wsc.ini:ro
      - {ROOT.as_posix()}/workbench/runtime/cookie-domain.php:/usr/local/bin/wsc-local-cookie-domain.php:ro
      - {root.as_posix()}/config/apache.conf:/etc/apache2/sites-available/000-default.conf:ro
      - {root.as_posix()}/tls/fullchain.pem:/etc/ssl/certs/wsc-local.pem:ro
      - {root.as_posix()}/tls/privkey.pem:/etc/ssl/private/wsc-local.key:ro
    environment:
      HOST_UID: ${{HOST_UID}}
      HOST_GID: ${{HOST_GID}}
      WCFSETUP_DBHOST: database
      WCFSETUP_DBUSER: ${{MYSQL_USER}}
      WCFSETUP_DBPASSWORD: ${{MYSQL_PASSWORD}}
      WCFSETUP_DBNAME: ${{MYSQL_DATABASE}}
    command: ["/usr/local/bin/wsc-apache-entrypoint"]
    depends_on:
      database:
        condition: service_healthy
    networks: [wsc]
'''
    else:
        web_services = f'''  php:
    build:
      context: {ROOT.as_posix()}/workbench/runtime
      args:
        PHP_VERSION: {cfg["php_version"]}
    volumes:
      - {site.as_posix()}:/var/www/html
      - {root.as_posix()}/config/php.ini:/usr/local/etc/php/conf.d/99-wsc.ini:ro
      - {ROOT.as_posix()}/workbench/runtime/cookie-domain.php:/usr/local/bin/wsc-local-cookie-domain.php:ro
    environment:
      HOST_UID: ${{HOST_UID}}
      HOST_GID: ${{HOST_GID}}
      WCFSETUP_DBHOST: database
      WCFSETUP_DBUSER: ${{MYSQL_USER}}
      WCFSETUP_DBPASSWORD: ${{MYSQL_PASSWORD}}
      WCFSETUP_DBNAME: ${{MYSQL_DATABASE}}
    command: ["/usr/local/bin/wsc-php-fpm-entrypoint"]
    depends_on:
      database:
        condition: service_healthy
    networks: [wsc]
  web:
    image: nginx:stable-alpine
    ports:
      - "127.0.0.1:${{HTTP_PORT}}:80"
      - "127.0.0.1:${{HTTPS_PORT}}:443"
    volumes:
      - {site.as_posix()}:/var/www/html:ro
      - {root.as_posix()}/config/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - {root.as_posix()}/tls/fullchain.pem:/etc/nginx/certs/fullchain.pem:ro
      - {root.as_posix()}/tls/privkey.pem:/etc/nginx/certs/privkey.pem:ro
    depends_on: [php]
    networks: [wsc]
'''
    document = f'''name: {cfg["project"]}
services:
{web_services}  database:
    image: {db_image}
    environment:
{db_environment}
    volumes:
      - {db.as_posix()}:/var/lib/mysql
    healthcheck:
      {db_health}
      interval: 5s
      timeout: 5s
      retries: 20
    networks: [wsc]
  mail:
    image: axllent/mailpit:v1.21
    profiles: [mail]
    ports:
      - "127.0.0.1:${{MAIL_PORT}}:8025"
    networks: [wsc]
networks:
  wsc:
    name: {cfg["project"]}_net
'''

    # Bind paths may contain spaces, #, colons or other YAML punctuation.
    lines = []
    for line in document.splitlines():
        stripped = line.lstrip()
        indent = line[:len(line) - len(stripped)]
        if stripped.startswith('- ') and not stripped.startswith('- "'):
            source, target = stripped[2:].rsplit(':/', 1)
            target = '/' + target
            read_only = target.endswith(':ro')
            if read_only:
                target = target[:-3]
            lines.extend([indent + '- type: bind', indent + '  source: ' + json.dumps(source), indent + '  target: ' + json.dumps(target)])
            if read_only:
                lines.append(indent + '  read_only: true')
            continue
        elif stripped.startswith('context: '):
            line = indent + 'context: ' + json.dumps(stripped[len('context: '):])
        lines.append(line)
    return "\n".join(lines) + "\n"


def create_project(args: argparse.Namespace) -> str:
    if getattr(args, "profile", None):
        profile_path = Path(args.profile).expanduser().resolve()
        if not profile_path.is_file():
            raise ValueError(f"Projektprofil nicht gefunden: {profile_path}")
        shared = json.loads(profile_path.read_text(encoding="utf-8"))
        if shared.get("schema") != 1:
            raise ValueError("Dieses Projektprofil wird nicht unterstützt.")
        args.suite = shared.get("suite_version", args.suite)
        args.php = args.php or shared.get("php_version")
        args.database = args.database or shared.get("database", "mariadb")
        args.webserver = args.webserver or shared.get("webserver", "nginx-php-fpm")
    root, secret = instance_paths(args.name)
    if root.exists():
        raise ValueError(f"Projekt '{args.name}' existiert bereits.")
    profile = profile_for(args.suite)
    if profile.get("channel") == "development" and not getattr(args, "experimental_ack", False):
        raise ValueError("WSC 6.3 ist ein inoffizieller Alpha-Entwicklungsbuild. Nutzung mit --experimental ausdrücklich bestätigen.")
    php = args.php or ("8.1" if profile["suite"] == "5.5" else "8.5" if profile["suite"] == "6.3" else "8.4" if profile["suite"] == "6.2" else "8.3")
    prefix = ".".join(php.split(".")[:2])
    if prefix not in {"8.1", "8.2", "8.3", "8.4", "8.5"}:
        raise ValueError("Der PHP-Container unterstützt derzeit die Profile 8.1 bis 8.5. Für Legacy-WSC 5.5 wird PHP 8.1 verwendet.")
    php_tuple = tuple(int(part) for part in php.split("."))
    minimum_tuple = tuple(int(part) for part in profile["php_min"].split("."))
    maximum_tuple = tuple(int(part) for part in profile["php_max"].split("."))
    if php_tuple < minimum_tuple or php_tuple > maximum_tuple:
        raise ValueError(f"PHP {php} liegt außerhalb des WoltLab-Profils {profile['php_min']} bis {profile['php_max']}. Quelle: {PROFILES and 'https://manual.woltlab.com/de/php-compatibility/'}")
    if profile["legacy"] and not args.legacy_ack:
        raise ValueError(f"WSC {profile['suite']} ist Legacy. Mit --legacy bestätigen; für neue Projekte wird ein aktuelles Profil empfohlen.")
    database_profile = getattr(args, "database", None) or "mariadb"
    if database_profile not in {"mariadb", "mysql8"}:
        raise ValueError("Datenbankprofil muss mariadb oder mysql8 sein.")
    webserver_profile = getattr(args, "webserver", None) or "nginx-php-fpm"
    if webserver_profile not in {"nginx-php-fpm", "apache"}:
        raise ValueError("Webserverprofil muss nginx-php-fpm oder apache sein.")
    reserved = reserved_ports()
    port = args.port or next((p for p in range(8080, 8500) if all(p + offset not in reserved and not port_taken(p + offset) for offset in range(3))), None)
    if port is None:
        raise ValueError("Kein freies lokales Port-Trio zwischen 8080 und 8501 gefunden.")
    if port < 1024 or port > 65533:
        raise ValueError("Projektport muss zwischen 1024 und 65533 liegen.")
    if any(p in reserved or port_taken(p) for p in (port, port + 1, port + 2)):
        raise ValueError(f"Mindestens einer der Ports {port}–{port + 2} wird bereits verwendet.")
    password = os.urandom(24).hex()
    project = f"wsc-{args.name}"
    cfg = {
        "schema": 1,
        "name": args.name,
        "project": project,
        "suite_version": profile["suite"],
        "php_version": php,
        "profile_status": "development" if profile.get("channel") == "development" else "legacy" if profile["legacy"] else "supported",
        "profile_channel": profile.get("channel", "stable"),
        "profile_source": profile.get("source", PROFILES and "https://manual.woltlab.com/de/php-compatibility/"),
        "webserver": webserver_profile,
        "database": "mariadb",
        "host": "127.0.0.1",
        "http_port": port,
        "url": f"http://127.0.0.1:{port}",
        "https_port": port + 1,
        "mail_port": port + 2,
        "mail_service": "mailpit",
        "browser_gate_token": os.urandom(16).hex(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "handbook": HANDBOOK,
    }
    cfg["database"] = database_profile
    root.mkdir(parents=True)
    (root / "site").mkdir(mode=0o755)
    # A restrictive host umask can otherwise make Nginx's unprivileged worker
    # unable to traverse the web root even though PHP-FPM runs as the host UID.
    (root / "site").chmod(0o755)
    (root / "data/database").mkdir(parents=True)
    (root / "config").mkdir()
    (root / "tls").mkdir()
    shutil.copy2(ROOT / "workbench/runtime/php.ini", root / "config/php.ini")
    shutil.copy2(ROOT / "workbench/runtime/nginx.conf", root / "config/nginx.conf")
    shutil.copy2(ROOT / "workbench/runtime/apache.conf", root / "config/apache.conf")
    ensure_fastcgi_request_metadata(root / "config/nginx.conf", cfg["browser_gate_token"])
    ensure_apache_preflight_gate(root / "config/apache.conf", cfg["browser_gate_token"])
    secret.parent.mkdir(parents=True, exist_ok=True)
    (root / "tls/fullchain.pem").touch()
    (root / "tls/privkey.pem").touch()
    admin_password = os.urandom(24).hex()
    secret.write_text(f"HTTP_PORT={port}\nHTTPS_PORT={port + 1}\nMAIL_PORT={port + 2}\nHOST_UID={os.getuid() if hasattr(os, 'getuid') else 1000}\nHOST_GID={os.getgid() if hasattr(os, 'getgid') else 1000}\nMYSQL_DATABASE=woltlab\nMYSQL_USER=wsc\nMYSQL_PASSWORD={password}\nMYSQL_ROOT_PASSWORD={os.urandom(24).hex()}\nWSC_ADMIN_USERNAME=admin\nWSC_ADMIN_EMAIL=admin@example.test\nWSC_ADMIN_PASSWORD={admin_password}\n", encoding="utf-8")
    secret.chmod(0o600)
    (root / "wsc-local.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "compose.yaml").write_text(compose_text(root, cfg), encoding="utf-8")
    (root / "README.md").write_text(f"# {args.name}\n\nLokales WoltLab-Projekt ({profile['suite']}, PHP {php}).\n\nStart: `wsc start {args.name}`\nAdresse: {cfg['url']}\n\nDieses Projektprofil enthält keine Passwörter. Geheimnisse liegen separat im lokalen Benutzerprofil.\n\nKompatibilitätsquelle: {PROFILES and 'https://manual.woltlab.com/de/php-compatibility/'}\n", encoding="utf-8")
    (root / ".gitignore").write_text(".env\n*.sql\ncompose.yaml\ndata/\ntls/*.pem\nsnapshots/\nexports/\n", encoding="utf-8")
    try:
        if args.zip:
            install_zip(Path(args.zip).expanduser().resolve(), root / "site")
        elif getattr(args, "download_core", False):
            version = getattr(args, "version", None) or ("latest" if profile.get("channel") == "development" else "6.2.8")
            download_core_project(args.name, version, getattr(args, "sha256", None))
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        secret.unlink(missing_ok=True)
        raise
    write_browser_preflight(root, cfg)
    database_label = "MySQL 8" if database_profile == "mysql8" else "MariaDB 10.11"
    webserver_label = "Apache · PHP" if webserver_profile == "apache" else "Nginx/PHP-FPM"
    profile_label = " · LEGACY (EOL)" if profile["legacy"] else " · ALPHA (inoffiziell)" if profile.get("unofficial") else ""
    next_step = f"\nLokales HTTPS wird bei der automatischen Einrichtung aktiviert: wsc install {args.name}" if profile.get("requires_https") else ""
    return f"Projekt '{args.name}' angelegt: {root}\nProfil: WSC {profile['suite']}{profile_label} · PHP {php} · {webserver_label} · {database_label}\nAdresse nach dem Start: {cfg['url']}\nWSC-Core-ZIP: {'eingespielt' if args.zip or getattr(args, 'download_core', False) else 'noch nicht vorhanden – offizielles Core laden oder wsc install-zip ' + args.name + ' DATEI.zip'}{next_step}"


def save_setup_credentials(name: str, username: str, email: str, password: str) -> None:
    """Persist optional WoltLab administrator credentials before installation."""
    if not isinstance(username, str) or not re.fullmatch(r"[\w .-]{1,40}", username, re.UNICODE):
        raise ValueError("Der Adminname darf 1–40 Buchstaben, Zahlen, Leerzeichen, Punkte oder Bindestriche enthalten.")
    if not isinstance(email, str) or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("Bitte eine gültige Admin-E-Mail-Adresse eingeben.")
    if not isinstance(password, str) or any(char in password for char in "\r\n\0"):
        raise ValueError("Das Adminpasswort darf keine Zeilenumbrüche oder Nullzeichen enthalten.")
    if password and len(password) < 12:
        raise ValueError("Das Adminpasswort muss mindestens 12 Zeichen lang sein.")
    _, _, secret = read_project(name)
    values = parse_env(secret)
    values.update({
        "WSC_ADMIN_USERNAME": username,
        "WSC_ADMIN_EMAIL": email,
        "WSC_ADMIN_PASSWORD": password or values.get("WSC_ADMIN_PASSWORD") or os.urandom(24).hex(),
    })
    secret.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")
    secret.chmod(0o600)


def reserved_ports(exclude: str = "") -> set[int]:
    ports: set[int] = set()
    for name in project_names():
        if name == exclude:
            continue
        cfg, _, _ = read_project(name)
        ports.update(int(cfg[key]) for key in ("http_port", "https_port", "mail_port") if key in cfg)
    return ports


def port_taken(port: int) -> bool:
    import socket
    with socket.socket() as sock:
        return sock.connect_ex(("127.0.0.1", port)) == 0


def install_zip(zip_path: Path, destination: Path) -> None:
    if not zip_path.is_file():
        raise ValueError(f"ZIP nicht gefunden: {zip_path}")
    import zipfile
    if not zipfile.is_zipfile(zip_path):
        raise ValueError("Die Datei ist kein gültiges ZIP-Archiv.")
    with tempfile.TemporaryDirectory(prefix="wsc-zip-") as temp_dir:
        temp = Path(temp_dir)
        with zipfile.ZipFile(zip_path) as archive:
            base = temp.resolve()
            for member in archive.infolist():
                target = (temp / member.filename).resolve()
                if target != base and base not in target.parents:
                    raise ValueError("Das ZIP enthält einen ungültigen Pfad außerhalb des Projektordners.")
            archive.extractall(temp)
        candidates = [temp / "upload", temp]
        candidates.extend(p for p in temp.iterdir() if p.is_dir())
        payload = next((p for p in candidates if (p / "install.php").is_file()), None)
        if payload is None:
            raise ValueError("Im ZIP wurde keine install.php gefunden. Erwartet wird ein WoltLab-Core-ZIP.")
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copytree(payload, destination, dirs_exist_ok=True)
        # copytree copies the archive root mode too. Some WSC Alpha archives
        # mark it 0700, which prevents the separate Nginx container user from
        # traversing the bind-mounted document root and returns a misleading 404.
        destination.chmod(destination.stat().st_mode | 0o755)
    project_root = destination.parent
    config_path = project_root / "wsc-local.json"
    if config_path.is_file():
        write_browser_preflight(project_root, json.loads(config_path.read_text(encoding="utf-8")))


def write_browser_preflight(root: Path, cfg: dict[str, Any]) -> None:
    """Check the actual project hostname and cookie support in its browser origin."""
    project_url = cfg["url"].rstrip("/")
    expected_host = urllib.parse.urlsplit(project_url).hostname or ""
    expected_host_js = json.dumps(expected_host)
    expected_host_php = json.dumps(expected_host)
    gate_token_php = json.dumps(cfg["browser_gate_token"])
    require_https_php = "true" if cfg.get("tls_enabled") else "false"
    safe_project_url = html.escape(project_url, quote=True)
    content = f'''<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Browserprüfung · wsc-local</title>
<style>
body{{max-width:760px;margin:48px auto;padding:0 20px;color:#202832;background:#f3f6f7;font:16px/1.55 system-ui,sans-serif}}
main{{padding:24px;border:1px solid #d9e0e5;border-radius:10px;background:#fff}} h1{{margin-top:0;font-size:1.5rem}}
.check{{padding:12px 14px;margin:12px 0;border-left:4px solid #9a6a00;background:#fff7e6}}
.pass{{border-color:#176b4b;background:#eaf5ee}} .fail{{border-color:#a53737;background:#fff0f0}}
.actions{{display:none;gap:12px;flex-wrap:wrap;margin-top:20px}} a{{color:#12494f}}
.actions a{{padding:10px 14px;border:1px solid #175b63;border-radius:6px;text-decoration:none;font-weight:650}}
.actions .primary{{background:#175b63;color:white}}
</style></head><body><main>
<h1>Browser für WoltLab prüfen</h1>
<p>Vor dem WoltLab-Systemtest prüft diese Seite Hostname, HTTPS bis zu PHP und einen echten Cookie-Rundlauf zwischen Browser und Server.</p>
<div id="host" class="check">Hostname wird geprüft …</div>
<div id="https" class="check">HTTPS-Verbindung wird geprüft …</div>
<div id="cookie" class="check">Cookies werden geprüft …</div>
<p id="help" aria-live="polite"></p>
<div id="actions" class="actions"><a id="systemtest" href="test.php" target="_blank" rel="noopener">WoltLab-Systemtest öffnen ↗</a><button id="continue" type="button" disabled>Systemtest ist grün – weiter</button></div>
<div id="install-actions" class="actions"><a class="primary" href="install.php" target="_blank" rel="noopener">WoltLab-Installer öffnen ↗</a></div>
<noscript>JavaScript muss für diese Browserprüfung aktiviert sein.</noscript>
<p><a href="http://127.0.0.1:9099/">Zurück zur wsc-local Workbench</a></p>
</main><script>
(() => {{
  const expectedHost = {expected_host_js};
  const hostOk = location.hostname.toLowerCase() === expectedHost.toLowerCase();
  const host = document.getElementById('host');
  host.className = `check ${{hostOk ? 'pass' : 'fail'}}`;
  host.textContent = hostOk ? `Hostname stimmt: ${{location.hostname}}` : `Falscher Hostname: geöffnet unter ${{location.hostname || '(unbekannt)'}}, erwartet wird ${{expectedHost}}.`;
  const cookie = document.getElementById('cookie');
  const https = document.getElementById('https');
  const help = document.getElementById('help');
  const setCheck = (element, ok, passText, failText) => {{
    element.className = `check ${{ok ? 'pass' : 'fail'}}`;
    element.textContent = ok ? passText : failText;
  }};
  const token = Array.from(crypto.getRandomValues(new Uint8Array(16)), (byte) => byte.toString(16).padStart(2, '0')).join('');
  fetch(`wsc-local-browser-check.php?step=set&token=${{token}}`, {{ credentials: 'same-origin', cache: 'no-store' }})
    .then((response) => {{ if (!response.ok) throw new Error(`HTTP ${{response.status}}`); return response.json(); }})
    .then((setResult) => fetch(`wsc-local-browser-check.php?step=check&token=${{token}}`, {{ credentials: 'same-origin', cache: 'no-store' }})
      .then((response) => {{ if (!response.ok) throw new Error(`HTTP ${{response.status}}`); return response.json(); }})
      .then((serverResult) => {{
        const serverHostOk = setResult.host_ok && serverResult.host_ok;
        const httpsOk = !serverResult.https_required || (setResult.https_ok && serverResult.https_ok);
        const cookieOk = serverResult.cookie_ok;
        setCheck(host, hostOk && serverHostOk,
          `Hostname stimmt im Browser und auf dem Server: ${{location.hostname}}`,
          `Hostname stimmt nicht überein. Browser: ${{location.hostname}} · PHP: ${{serverResult.server_name || 'unbekannt'}} · erwartet: ${{expectedHost}}.`);
        setCheck(https, httpsOk,
          'HTTPS kommt korrekt und verschlüsselt bei PHP an.',
          serverResult.https_required ? 'HTTPS ist aktiv im Browser, kommt aber nicht korrekt bei PHP an. Webserver-Konfiguration prüfen.' : 'HTTPS-Status konnte nicht bestätigt werden.');
        setCheck(cookie, cookieOk,
          'Cookie wurde vom Browser gesetzt und vom PHP-Server wieder empfangen.',
          'Cookie-Rundlauf fehlgeschlagen. Browser-Cookies sind blockiert oder der Server kann sie nicht korrekt setzen/empfangen.');
        const ready = hostOk && serverHostOk && httpsOk && cookieOk;
        document.getElementById('actions').style.display = ready ? 'flex' : 'none';
        document.getElementById('continue').disabled = !ready;
        help.textContent = ready
          ? 'Browser und Server sind bereit. Öffne jetzt den WoltLab-Systemtest. Wenn dort alle Pflichtprüfungen grün sind, komm hierher zurück und bestätige es, um den Installer freizugeben.'
          : 'Der Installer bleibt gesperrt. Erlaube Cookies für diese Projektadresse und starte die Browserprüfung erneut. Bei einem Serverfehler klicke in der Workbench auf „Prüfen“.';
      }}))
    .catch((error) => {{
      setCheck(cookie, false, '', `Serverprüfung fehlgeschlagen (${{error.message}}).`);
      setCheck(https, false, '', 'HTTPS und Serverantwort konnten nicht gemeinsam geprüft werden.');
      document.getElementById('actions').style.display = 'none';
      help.textContent = 'Der Installer bleibt gesperrt. Prüfe in der Workbench den Projektstatus und die Logs.';
    }});
  document.getElementById('continue').addEventListener('click', () => {{
    fetch(`wsc-local-browser-check.php?step=continue&token=${{token}}`, {{ credentials: 'same-origin', cache: 'no-store' }})
      .then((response) => {{ if (!response.ok) throw new Error(`HTTP ${{response.status}}`); return response.json(); }})
      .then((result) => {{
        if (!result.unlocked) throw new Error('Browserprüfung muss erneut ausgeführt werden.');
        document.getElementById('install-actions').style.display = 'flex';
        help.textContent = 'WoltLab-Systemtest als erfolgreich bestätigt. Der Installer ist jetzt für diese Browser-Sitzung freigegeben.';
      }})
      .catch((error) => {{ help.textContent = `Installer bleibt gesperrt: ${{error.message}}`; }});
  }});
  document.getElementById('systemtest').addEventListener('click', () => {{
    document.getElementById('continue').disabled = false;
  }});
}})();
</script></body></html>\n'''
    path = root / "site/wsc-local-check.html"
    path.write_text(content, encoding="utf-8")
    path.chmod(0o644)
    php = f'''<?php
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, max-age=0');
$expectedHost = {expected_host_php};
$gateToken = {gate_token_php};
$httpsRequired = {require_https_php};
$requestHost = strtolower((string) parse_url('http://' . ($_SERVER['HTTP_HOST'] ?? ''), PHP_URL_HOST));
$serverName = strtolower((string) ($_SERVER['SERVER_NAME'] ?? ''));
$https = !empty($_SERVER['HTTPS']) && strtolower((string) $_SERVER['HTTPS']) !== 'off';
$hostOk = $requestHost === strtolower($expectedHost) && $serverName === strtolower($expectedHost);
$token = (string) ($_GET['token'] ?? '');
if (!preg_match('/^[a-f0-9]{{32}}$/D', $token)) {{ http_response_code(400); echo json_encode(['error' => 'invalid token']); exit; }}
$secure = $https;
if (($_GET['step'] ?? '') === 'set') {{
    setcookie('wsc_local_probe', $token, ['expires' => time() + 60, 'path' => '/', 'secure' => $secure, 'httponly' => false, 'samesite' => 'Lax']);
    echo json_encode(['host_ok' => $hostOk, 'server_name' => $serverName, 'https_ok' => $https]);
    exit;
}}
if (($_GET['step'] ?? '') === 'check') {{
    $cookieOk = hash_equals($token, (string) ($_COOKIE['wsc_local_probe'] ?? ''));
    setcookie('wsc_local_probe', '', ['expires' => time() - 3600, 'path' => '/', 'secure' => $secure, 'httponly' => false, 'samesite' => 'Lax']);
    $ready = $hostOk && $cookieOk && (!$httpsRequired || $https);
    if ($ready) setcookie('wsc_local_browser_verified', $gateToken, ['expires' => time() + 3600, 'path' => '/', 'secure' => $secure, 'httponly' => true, 'samesite' => 'Lax']);
    echo json_encode(['host_ok' => $hostOk, 'server_name' => $serverName, 'https_required' => $httpsRequired, 'https_ok' => $https, 'cookie_ok' => $cookieOk]);
    exit;
}}
if (($_GET['step'] ?? '') === 'continue') {{
    $preflightOk = hash_equals($gateToken, (string) ($_COOKIE['wsc_local_browser_verified'] ?? '')) && $hostOk && (!$httpsRequired || $https);
    if ($preflightOk) setcookie('wsc_local_install_verified', $gateToken, ['expires' => time() + 3600, 'path' => '/', 'secure' => $secure, 'httponly' => true, 'samesite' => 'Lax']);
    echo json_encode(['unlocked' => $preflightOk]);
    exit;
}}
http_response_code(404);
echo json_encode(['error' => 'not found']);
'''
    check_path = root / "site/wsc-local-browser-check.php"
    check_path.write_text(php, encoding="utf-8")
    check_path.chmod(0o644)


def ensure_fastcgi_request_metadata(config_path: Path, gate_token: str = "1") -> bool:
    """Pass the browser's actual host and HTTPS state through to PHP-FPM."""
    content = config_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    updated_lines = []
    for index, line in enumerate(lines):
        updated_lines.append(line.replace("fastcgi_param HTTP_HOST $host;", "fastcgi_param HTTP_HOST $http_host;"))
        if line.strip() != "include fastcgi_params;":
            continue
        following = "\n".join(lines[index + 1:index + 12])
        indent = line[:len(line) - len(line.lstrip())]
        if "fastcgi_param SERVER_NAME $host;" in following:
            continue
        updated_lines.extend(f"{indent}{setting}" for setting in (
            "fastcgi_param SERVER_NAME $host;",
            "fastcgi_param HTTP_HOST $http_host;",
            "fastcgi_param SERVER_PORT $server_port;",
            "fastcgi_param REQUEST_SCHEME $scheme;",
            "fastcgi_param HTTPS $https;",
        ))
    updated = "\n".join(updated_lines) + ("\n" if content.endswith("\n") else "")
    map_block = f'''map "$uri:$cookie_wsc_local_browser_verified" $wsc_local_deny_systemtest {{
    default 0;
    ~^/test\\.php:(?!{gate_token}$) 1;
}}
map "$uri:$cookie_wsc_local_install_verified" $wsc_local_deny_installer {{
    default 0;
    ~^/install\\.php:(?!{gate_token}$) 1;
}}
'''
    updated = re.sub(
        r'(?ms)^map "\$uri:\$cookie_wsc_local_(?:browser|install)_verified" \$wsc_local_deny_(?:systemtest|installer) \{\n.*?^\}\n',
        "",
        updated,
    )
    updated = map_block + updated
    updated = updated.replace('    if ($wsc_local_deny_installer) { return 403 "Open /wsc-local-check.html first."; }', '')
    if "if ($wsc_local_deny_systemtest)" not in updated:
        updated = re.sub(
            r"(?m)^server \{\s*$",
            'server {\n    if ($wsc_local_deny_systemtest) { return 403 "Run /wsc-local-check.html first."; }\n    if ($wsc_local_deny_installer) { return 403 "Confirm the WoltLab system test in /wsc-local-check.html first."; }',
            updated,
        )
    if updated != content:
        config_path.write_text(updated, encoding="utf-8")
        return True
    return False


def ensure_apache_preflight_gate(config_path: Path, gate_token: str = "1") -> bool:
    content = config_path.read_text(encoding="utf-8")
    install_rule = '''    RewriteCond %{REQUEST_URI} ^/install\\.php$ [NC]
    RewriteCond %{HTTP:Cookie} !(^|;\\s*)wsc_local_install_verified=1(;|$) [NC]
    RewriteRule ^ - [F,L]
'''
    install_rule = install_rule.replace("wsc_local_install_verified=1", f"wsc_local_install_verified={gate_token}")
    def update_vhost(match: re.Match[str]) -> str:
        block = match.group(0)
        block = re.sub(r"(wsc_local_browser_verified=)[a-f0-9]+", rf"\g<1>{gate_token}", block)
        block = re.sub(r"(wsc_local_install_verified=)[a-f0-9]+", rf"\g<1>{gate_token}", block)
        if "wsc_local_install_verified=" in block:
            return block
        return block.replace("    RewriteRule ^ - [F,L]", "    RewriteRule ^ - [F,L]\n" + install_rule, 1)
    updated = re.sub(r"(?s)<VirtualHost [^>]+>.*?</VirtualHost>", update_vhost, content)
    if updated != content:
        config_path.write_text(updated, encoding="utf-8")
        return True
    return False


def download_core_project(name: str, version: str, expected_sha256: str | None = None) -> str:
    cfg, root, _ = read_project(name)
    if cfg["suite_version"] == "6.3":
        if version not in {None, "latest", "6.3"}:
            raise ValueError("Für WSC 6.3 wird automatisch der neueste Alpha-Testbuild geladen; eigene Archive bitte mit wsc install-zip einspielen.")
        return download_experimental_63(name, root)
    version = version or "6.2.8"
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("Core-Version bitte vollständig angeben, zum Beispiel 6.2.8.")
    if version.split(".", 2)[:2] != cfg["suite_version"].split(".")[:2]:
        raise ValueError(f"WSC-Core {version} passt nicht zum Projektprofil {cfg['suite_version']}.")
    known_hashes = {"6.2.8": "13f2fe424c8a54b72d48f1c43f77d5ed62325bb20a89c67040144dbc3fc7dd00"}
    expected = (expected_sha256 or known_hashes.get(version) or "").lower()
    if expected and not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("SHA-256 muss aus 64 Hex-Zeichen bestehen.")
    url = f"https://assets.woltlab.com/release/woltlab-suite-{version}.zip"
    downloads = DATA / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    archive = downloads / f"woltlab-suite-{version}.zip"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "wsc-local/Workbench"})
        with urllib.request.urlopen(request, timeout=60) as response, archive.open("wb") as out:
            shutil.copyfileobj(response, out)
    except Exception as exc:
        archive.unlink(missing_ok=True)
        raise RuntimeError("WoltLab Core konnte nicht geladen werden. Bitte über die offizielle Downloadseite laden und anschließend wsc install-zip nutzen: https://www.woltlab.com/de/woltlab-suite-download/") from exc
    if expected and file_hash(archive) != expected:
        archive.unlink(missing_ok=True)
        raise ValueError("Die SHA-256-Prüfung des offiziellen Core-Downloads ist fehlgeschlagen.")
    install_zip(archive, root / "site")
    return f"WoltLab Suite Core {version} heruntergeladen und als ZIP geprüft."


def download_experimental_63(name: str, root: Path) -> str:
    """Download a community-built WSC 6.3 alpha archive and verify its published digest."""
    api_url = "https://api.github.com/repos/YoureCom/wsc-63-testbuilds/releases?per_page=100"
    def fetch(url: str, limit: int, *, github_api: bool = False) -> bytes:
        headers = {"User-Agent": "wsc-local/Workbench"}
        if github_api:
            headers["Accept"] = "application/vnd.github+json"
        last_error: Exception | None = None
        for attempt in range(4):
            request = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=90) as response:
                    data = response.read(limit + 1)
                if len(data) > limit:
                    raise ValueError("Der veröffentlichte Testbuild überschreitet die erlaubte Dateigröße.")
                return data
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code not in {408, 429, 500, 502, 503, 504}:
                    raise
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
            if attempt < 3:
                time.sleep(1.5 * (2 ** attempt))
        raise RuntimeError(f"GitHub war nach mehreren Versuchen nicht erreichbar: {last_error}") from last_error

    try:
        releases = json.loads(fetch(api_url, 2 * 1024 * 1024, github_api=True))
        release = next((item for item in releases if item.get("prerelease") and re.fullmatch(r"6\.3-alpha-[0-9]{8}-[0-9a-f]+", item.get("tag_name", ""))), None)
        if not release:
            raise ValueError("Kein veröffentlichter WSC-6.3-Alpha-Testbuild gefunden.")
        assets = {asset["name"]: asset for asset in release.get("assets", [])}
        bundle_name = "WoltLabSuite-6.3-testbuild.zip"
        if bundle_name not in assets:
            raise ValueError("Der 6.3-Testbuild enthält nicht das erwartete Installationsarchiv.")
        bundle = assets[bundle_name]
        if int(bundle.get("size", 0)) <= 0 or int(bundle["size"]) > 100 * 1024 * 1024:
            raise ValueError("Die von GitHub angegebene Größe des 6.3-Archivs ist ungültig oder zu groß.")
        digest = bundle.get("digest", "")
        match = re.fullmatch(r"sha256:([0-9a-fA-F]{64})", digest)
        if match:
            expected_sha256 = match.group(1).lower()
        else:
            sums_asset = assets.get("SHA256SUMS")
            if not sums_asset:
                raise ValueError("GitHub veröffentlicht weder eine SHA-256-Prüfsumme noch SHA256SUMS für das 6.3-Archiv.")
            sums = fetch(sums_asset["browser_download_url"], 64 * 1024).decode("ascii")
            sum_match = re.search(rf"^([0-9a-fA-F]{{64}})\s+\*?{re.escape(bundle_name)}$", sums, re.M)
            if not sum_match:
                raise ValueError("SHA256SUMS enthält keine Prüfsumme für das 6.3-Installationsarchiv.")
            expected_sha256 = sum_match.group(1).lower()
        archive_data = fetch(bundle["browser_download_url"], 100 * 1024 * 1024)
        if len(archive_data) != int(bundle["size"]):
            raise ValueError("Das heruntergeladene 6.3-Archiv ist unvollständig.")
        actual = hashlib.sha256(archive_data).hexdigest()
        if actual != expected_sha256:
            raise ValueError("SHA-256-Prüfung des inoffiziellen WSC-6.3-Testbuilds fehlgeschlagen.")
        downloads = DATA / "downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        archive = downloads / f"{release['tag_name']}-{bundle_name}"
        archive.write_bytes(archive_data)
        install_zip(archive, root / "site")
        cfg, _, _ = read_project(name)
        cfg["core_version"] = release["tag_name"]
        cfg["core_source"] = "https://github.com/YoureCom/wsc-63-testbuilds"
        cfg["core_sha256"] = actual
        (root / "wsc-local.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return f"WSC 6.3 Alpha-Testbuild {release['tag_name']} geladen. SHA-256 geprüft. Quelle: https://github.com/YoureCom/wsc-63-testbuilds (inoffiziell, nur zum Testen)."
    except (OSError, urllib.error.URLError, json.JSONDecodeError, UnicodeDecodeError, RuntimeError) as exc:
        raise RuntimeError(f"Der inoffizielle WSC-6.3-Testbuild konnte nicht automatisch geladen werden: {exc}") from exc


class _SetupFormParser(HTMLParser):
    """Read the first form's hidden inputs and destination from WCFSetup HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.fields: dict[str, str] = {}
        self.action = ""
        self._form_seen = False
        self._inside_first_form = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "form" and not self._form_seen:
            self._form_seen = True
            self._inside_first_form = True
            self.action = attributes.get("action") or ""
        elif tag == "form" and self._form_seen:
            self._inside_first_form = False
        if tag == "input" and self._inside_first_form:
            if attributes.get("type", "").lower() == "hidden" and attributes.get("name"):
                self.fields[attributes["name"]] = attributes.get("value") or ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self._inside_first_form = False


class _SetupAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.assets: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("href"):
            self.links.append(attributes["href"])
        if tag in {"script", "img"} and attributes.get("src"):
            self.assets.append(attributes["src"])
        if tag == "link" and attributes.get("rel") == "stylesheet" and attributes.get("href"):
            self.assets.append(attributes["href"])


def _post_setup_step(opener: Any, url: str, values: dict[str, str], referer: str | None = None, host_header: str | None = None) -> tuple[str, str]:
    headers = {"User-Agent": "wsc-local/Workbench"}
    if host_header:
        headers["Host"] = host_header
    if referer:
        headers["Referer"] = referer
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(values).encode("utf-8"),
        headers=headers,
    )
    with opener.open(request, timeout=300) as response:
        return response.geturl(), response.read().decode("utf-8", "replace")


class _IPv4HTTPConnection(http.client.HTTPConnection):
    """Keep the requested host for cookies/Host while connecting to Docker's IPv4 bind."""

    def connect(self) -> None:
        self.sock = socket.create_connection(("127.0.0.1", self.port), self.timeout, self.source_address)


class _IPv4HTTPSConnection(http.client.HTTPSConnection):
    """Connect over IPv4 but preserve hostname for TLS SNI and cookie scope."""

    def connect(self) -> None:
        sock = socket.create_connection(("127.0.0.1", self.port), self.timeout, self.source_address)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


class _IPv4HTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req: urllib.request.Request) -> Any:
        return self.do_open(_IPv4HTTPConnection, req)


class _IPv4HTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req: urllib.request.Request) -> Any:
        return self.do_open(lambda host, **kwargs: _IPv4HTTPSConnection(host, context=self._context, **kwargs), req)


def write_install_state(root: Path, state: str, stage: str, error: str = "") -> None:
    if len(error) > 4000:
        log_dir = root / "logs"
        log_dir.mkdir(exist_ok=True)
        (log_dir / "installation-error.log").write_text(error, encoding="utf-8")
        error = "Die Einrichtung wurde unterbrochen. Die letzten Meldungen folgen; das vollständige Protokoll liegt unter logs/installation-error.log.\n" + error[-3000:]
    temporary = root / ".installation-state.tmp"
    temporary.write_text(json.dumps({"state": state, "stage": stage, "error": error, "updated_at": datetime.now(timezone.utc).isoformat()}, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(root / "installation-state.json")


def apply_local_port_compatibility(root: Path, cfg: dict[str, Any]) -> None:
    """Correct the verified WSC 6.2/6.3 host comparison for local authorities."""
    if cfg.get("suite_version") not in {"6.2", "6.3"}:
        return
    path = root / "site/lib/system/request/RequestHandler.class.php"
    original = path.read_text(encoding="utf-8")
    before = '''                if ($domainName !== $psrRequest->getUri()->getHost()) {
                    $targetUrl = $psrRequest->getUri()->withHost($domainName);'''
    after = '''                // wsc-local: Compare hostname and port separately for local authorities.
                $configuredHost = \\parse_url('http://' . $domainName, \\PHP_URL_HOST);
                $configuredPort = \\parse_url('http://' . $domainName, \\PHP_URL_PORT);
                if ($configuredHost !== $psrRequest->getUri()->getHost() || $configuredPort !== $psrRequest->getUri()->getPort()) {
                    $targetUrl = $psrRequest->getUri()->withHost($configuredHost)->withPort($configuredPort);'''
    if original.count(before) != 1:
        return  # A different upstream implementation must pass the final URL checks.
    backup_dir = root / "config/compatibility"
    backup_dir.mkdir(exist_ok=True)
    (backup_dir / "RequestHandler.class.php.original").write_text(original, encoding="utf-8")
    patched = original.replace(before, after, 1)
    path.write_text(patched, encoding="utf-8")
    cfg["compatibility_patches"] = [{"name": f"WSC {cfg['suite_version']}: lokale Ports", "file": "lib/system/request/RequestHandler.class.php", "original_sha256": hashlib.sha256(original.encode()).hexdigest(), "patched_sha256": hashlib.sha256(patched.encode()).hexdigest()}]
    (root / "wsc-local.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_install_language(language: str | None = None, env: dict[str, str] | None = None) -> str:
    """Dashboard passes an explicit choice; CLI falls back to its host locale."""
    if language is not None:
        if language not in {'de', 'en'}:
            raise ValueError('Installationssprache muss de oder en sein.')
        return language
    env = os.environ if env is None else env
    selected = next((env[key] for key in ('LC_ALL', 'LC_MESSAGES', 'LANG') if env.get(key)), '')
    if not selected:
        selected = locale.getlocale()[0] or ''
    primary = re.split(r'[_\-.@]', selected.lower(), maxsplit=1)[0]
    return 'en' if primary == 'en' else 'de'


def verify_page_language(page: str, language: str) -> None:
    match = re.search(r"<html\b[^>]*\slang\s*=\s*[\"']([a-zA-Z_-]+)[\"']", page, re.I)
    if not match or re.split('[-_]', match.group(1).lower())[0] != language:
        raise RuntimeError('WoltLab wurde nicht in der gewählten Sprache eingerichtet. Die Installation wird nicht als einsatzbereit markiert.')


def install_woltlab(name: str, language: str | None = None) -> str:
    cfg, root, _ = read_project(name)
    if (root / "site/global.php").exists():
        raise ValueError("WoltLab-Dateien sind bereits eingerichtet. Bei einer unterbrochenen Einrichtung zuerst Diagnose und Sicherung verwenden.")
    cfg['installation_language'] = resolve_install_language(language if language is not None else cfg.get('installation_language'))
    (root / 'wsc-local.json').write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    write_install_state(root, "running", "Umgebung und HTTPS vorbereiten")
    try:
        result = _install_woltlab(name)
    except Exception as exc:
        write_install_state(root, "failed", "Einrichtung unterbrochen", str(exc))
        raise
    write_install_state(root, "ready", "Website, Dateien und Admin-Anmeldung geprüft")
    for filename in ("wsc-local-check.html", "wsc-local-browser-check.php", "wsc-recovery.php", "wsc-recovery-auth.php"):
        (root / "site" / filename).unlink(missing_ok=True)
    return result


def _install_woltlab(name: str) -> str:
    """Run WCFSetup's normal installer steps unattended with the saved settings."""
    cfg, root, secret = read_project(name)
    if (root / "site/global.php").exists():
        raise ValueError("WoltLab scheint bereits installiert zu sein. Öffne die Projektadresse oder nutze Wiederherstellen.")
    if not (root / "site/install.php").is_file():
        raise ValueError("Das WoltLab-Installationsarchiv fehlt. Erstelle das Projekt erneut und lade dabei ein gültiges Suite-Archiv.")
    language = resolve_install_language(cfg.get("installation_language"))
    values = parse_env(secret)
    if profile_for(cfg["suite_version"]).get("requires_https") and not cfg.get("tls_enabled"):
        write_install_state(root, "running", "Lokales HTTPS-Zertifikat einrichten")
        local_tls(name, True, confirmed=True)
        cfg, root, secret = read_project(name)
        values = parse_env(secret)
    runtime = "Apache mit PHP" if cfg.get("webserver") == "apache" else "Nginx und PHP-FPM"
    write_install_state(root, "running", f"{runtime} bauen und starten – beim ersten Mal kann das mehrere Minuten dauern")
    start_output = action(name, "start", "up", "-d", "--wait", "--wait-timeout", "180")
    cfg, root, secret = read_project(name)
    values = parse_env(secret)
    public_base = cfg["url"].rstrip("/") + "/"
    port = cfg["https_port"] if cfg.get("tls_enabled") else cfg["http_port"]
    scheme = "https" if cfg.get("tls_enabled") else "http"
    expected_host = cfg.get("domain", "127.0.0.1")
    host_header = f"{expected_host}:{port}"
    # Docker publishes these local ports on IPv4 loopback. Some libc resolvers
    # return ::1 first for *.localhost, where nothing is listening. Keep the
    # project's hostname in URLs (and thus cookie scope), but dial IPv4 below.
    base = public_base
    context = ssl._create_unverified_context() if base.startswith("https:") else None
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPCookieProcessor(jar),
        _IPv4HTTPHandler(),
        _IPv4HTTPSHandler(context=context) if context else _IPv4HTTPSHandler(),
    )
    token = os.urandom(16).hex()
    install_stage = "Vorbereitung"

    def mark_stage(stage: str) -> None:
        nonlocal install_stage
        install_stage = stage
        write_install_state(root, "running", stage)

    def local_request(url: str, data: bytes | None = None, headers: dict[str, str] | None = None) -> urllib.request.Request:
        request_headers = {"User-Agent": "wsc-local/Workbench", **(headers or {})}
        return urllib.request.Request(url, data=data, headers=request_headers)
    try:
        for step in ("set", "check", "continue"):
            mark_stage(f"lokale Browser-/HTTPS-Prüfung ({step})")
            url = base + "wsc-local-browser-check.php?" + urllib.parse.urlencode({"step": step, "token": token})
            deadline = time.monotonic() + (90 if step == "set" else 30)
            while True:
                try:
                    with opener.open(local_request(url), timeout=30) as response:
                        result = json.loads(response.read().decode("utf-8"))
                    break
                except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                    if time.monotonic() >= deadline:
                        raise RuntimeError(f"Der lokale Webserver antwortet auch nach {90 if step == 'set' else 30} Sekunden nicht. Prüfe Docker und Ports; die Einrichtung wurde abgebrochen. ({exc})") from exc
                    time.sleep(2)
            if step == "check" and not (result.get("host_ok") and result.get("cookie_ok") and (result.get("https_ok") or not profile_for(cfg["suite_version"]).get("requires_https"))):
                raise RuntimeError("Die automatische Browser-/HTTPS-Prüfung ist fehlgeschlagen. Öffne „Prüfen“ für die konkrete Ursache.")
            if step == "continue" and not result.get("unlocked"):
                raise RuntimeError("WoltLab-Installer konnte nach der lokalen Browserprüfung nicht freigegeben werden.")

        install_url = urllib.parse.urljoin(base, "install.php")
        initial_url = install_url + "?" + urllib.parse.urlencode({"languageCode": language})
        mark_stage("WoltLab-Installer öffnen")
        with opener.open(local_request(initial_url), timeout=90) as response:
            page = response.read().decode("utf-8", "replace")
        for _ in range(32):
            parser = _SetupFormParser()
            parser.feed(page)
            fields = dict(parser.fields)
            step = fields.get("step", "")
            if not step:
                mark_stage("ACP-Sitzung und WoltLab-Core-Paketwarteschlange")
                # WCFSetup's final page submits a GET form to the ACP to finish
                # its package queue; this form intentionally has no `step`.
                if parser.action and "acp/index.php" in parser.action and fields.get("action") == "WCFSetup":
                    acp_url = urllib.parse.urljoin(install_url, parser.action)
                    acp_url += "?" + urllib.parse.urlencode(fields)
                elif "100% complete" in page or "100% abgeschlossen" in page:
                    acp_url = urllib.parse.urljoin(base, "acp/index.php?action=WCFSetup")
                else:
                    visible = re.sub(r"(?is)<(head|script|style)\b.*?</\1>", " ", page)
                    detail = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", visible))).strip()
                    for key in ("MYSQL_PASSWORD", "MYSQL_ROOT_PASSWORD", "WSC_ADMIN_PASSWORD"):
                        if values.get(key):
                            detail = detail.replace(values[key], "[verborgen]")
                    if "Permission denied" in detail:
                        raise RuntimeError("PHP kann die Installationsdateien nicht schreiben. Der Webserver-Benutzer und die Rechte des Projektordners passen nicht zusammen. Prüfe das Webserverprofil und die Dateirechte.\n" + detail[:700])
                    raise RuntimeError("WoltLab hat keinen nächsten Installationsschritt geliefert. Letzte Antwort: " + detail[:700])
                mark_stage("WoltLab-ACP-Seite öffnen")
                with opener.open(local_request(acp_url, headers={"Referer": install_url}), timeout=300) as response:
                    acp_page = response.read().decode("utf-8", "replace")
                if response.status >= 400 or "Fatal Error" in acp_page or "An error has occurred" in acp_page:
                    raise RuntimeError("WoltLab hat die Suite-Dateien eingerichtet, aber die Abschlussprüfung im ACP schlug fehl. Öffne „Logs“ für Details.")
                # WCFSetup only renders the ACP package-queue page. The browser
                # normally runs this JavaScript queue to install com.woltlab.wcf;
                # complete the same authenticated AJAX requests here.
                xsrf = next((urllib.parse.unquote(cookie.value) for cookie in jar if cookie.name == "XSRF-TOKEN"), "")
                if not xsrf:
                    raise RuntimeError("WoltLab hat keine sichere ACP-Session für die Core-Installation erstellt.")

                def install_queue(fields: dict[str, Any]) -> dict[str, Any]:
                    endpoint = urllib.parse.urljoin(base, "acp/index.php?install-package/&t=" + urllib.parse.quote(xsrf, safe=""))
                    request = urllib.request.Request(
                        endpoint,
                        data=urllib.parse.urlencode(fields).encode("utf-8"),
                        headers={"User-Agent": "wsc-local/Workbench", "X-Requested-With": "XMLHttpRequest", "Host": host_header},
                    )
                    try:
                        with opener.open(request, timeout=300) as result:
                            payload = json.loads(result.read().decode("utf-8", "replace"))
                    except urllib.error.URLError as exc:
                        raise RuntimeError(f"Verbindung zur WoltLab-Core-Warteschlange fehlgeschlagen ({fields.get('step')}, {fields.get('node', 'prepare')}, {endpoint}): {exc}") from exc
                    if isinstance(payload.get("returnValues"), dict):
                        payload = payload["returnValues"]
                    return payload

                mark_stage("WoltLab-Core-Warteschlange vorbereiten")
                queue_result = install_queue({"queueID": "1", "step": "prepare"})
                queue_id = str(queue_result.get("queueID", "1"))
                node = queue_result.get("node")
                queue_step = queue_result.get("step")
                queue_count = 0
                while queue_step == "install" and node:
                    if queue_result.get("innerTemplate"):
                        raise RuntimeError("Die WoltLab-Core-Installation benötigt eine manuelle Eingabe, die wsc-local nicht sicher ausfüllen kann.")
                    mark_stage(f"WoltLab-Core installieren ({node})")
                    queue_result = install_queue({"queueID": queue_id, "step": "install", "node": str(node)})
                    queue_id = str(queue_result.get("queueID", queue_id))
                    node = queue_result.get("node")
                    queue_step = queue_result.get("step")
                    queue_count += 1
                    if queue_count > 800:
                        raise RuntimeError("WoltLab hat ungewöhnlich viele Core-Installationsschritte angefordert; der Vorgang wurde sicher beendet.")
                if queue_step != "success":
                    detail = json.dumps(queue_result, ensure_ascii=False)[:500]
                    raise RuntimeError(f"WoltLab konnte das Core-Paket nicht fertig installieren (Schritt: {queue_step or 'unbekannt'}). {detail}")
                # The license and mail pages are optional defaults for a new
                # core-only local project. Complete WoltLab's own setup state
                # through its OptionAction; license credentials remain unset
                # and can be added later in the ACP.
                mark_stage("WoltLab-Ersteinrichtung abschließen")
                apply_local_port_compatibility(root, cfg)
                finish_code = (
                    '$_SERVER["DOCUMENT_ROOT"]="/var/www/html"; '
                    f'$_SERVER["HTTP_HOST"]="{host_header}"; '
                    f'$_SERVER["SERVER_PORT"]="{port}"; $_SERVER["HTTPS"]="{"on" if cfg.get("tls_enabled") else "off"}"; '
                    '$_SERVER["SCRIPT_NAME"]="/acp/index.php"; '
                    '$_SERVER["SCRIPT_FILENAME"]="/var/www/html/acp/index.php"; '
                    '$_SERVER["REQUEST_URI"]="/acp/index.php?first-time-setup/"; '
                    '$_SERVER["REQUEST_METHOD"]="GET"; chdir("/var/www/html"); '
                    'require "/var/www/html/global.php"; '
                    '$defaultLanguage=\\wcf\\system\\language\\LanguageFactory::getInstance()->getDefaultLanguage()->languageCode; '
                    '$adminLanguage=(new \\wcf\\data\\language\\Language((new \\wcf\\data\\user\\User(1))->languageID))->languageCode; '
                    f'if ($defaultLanguage!=="{language}" || $adminLanguage!=="{language}") throw new \\RuntimeException("WoltLab installation language verification failed"); '
                    '$app=new \\wcf\\data\\application\\Application(1); '
                    '$appData=["domainName"=>' + repr(host_header) + ',"domainPath"=>"/","cookieDomain"=>' + repr(expected_host) + ']; '
                    '(new \\wcf\\data\\application\\ApplicationAction([$app], "update", ["data"=>$appData]))->executeAction(); '
                    '$option=\\wcf\\data\\option\\Option::getOptionByName("first_time_setup_state"); '
                    '$offline=\\wcf\\data\\option\\Option::getOptionByName("offline"); '
                    '(new \\wcf\\data\\option\\OptionAction([], "updateAll", ["data"=>[$option->optionID=>-1,$offline->optionID=>0]]))->executeAction(); '
                    'echo "WoltLab setup defaults applied\\n";'
                )
                finish = compose(
                    name,
                    "exec",
                    "--user",
                    f"{values.get('HOST_UID', '1000')}:{values.get('HOST_GID', '1000')}",
                    "-T",
                    "web" if cfg.get("webserver") == "apache" else "php",
                    "php",
                    "-r",
                    finish_code,
                    timeout=120,
                )
                if finish.returncode:
                    raise RuntimeError("WoltLab-Core wurde installiert, aber die optionale Ersteinrichtung konnte nicht abgeschlossen werden: " + (finish.stderr.strip() or finish.stdout.strip()))
                home_url = base
                mark_stage("fertige WoltLab-Startseite prüfen")
                try:
                    with opener.open(local_request(home_url, headers={"Referer": acp_url}), timeout=90) as response:
                        home_page = response.read().decode("utf-8", "replace")
                except urllib.error.HTTPError as exc:
                    error_page = exc.read().decode("utf-8", "replace")
                    visible = re.sub(r"(?is)<(head|script|style)\b.*?</\1>", " ", error_page)
                    detail = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", visible))).strip()
                    raise RuntimeError(f"Die WoltLab-Startseite antwortet mit HTTP {exc.code} bei {exc.geturl()}: {detail[:700]}") from exc
                if response.status >= 400 or "Fatal Error" in home_page or "An error has occurred" in home_page:
                    raise RuntimeError("Die WoltLab-Dateien sind eingerichtet, aber die Website besteht die Abschlussprüfung noch nicht. Öffne „Logs“ für die Ursache.")
                mark_stage("Stylesheets, JavaScript und lokale Links prüfen")
                assets = _SetupAssetParser()
                assets.feed(home_page)
                origin = urllib.parse.urlsplit(base)
                for reference in assets.assets + assets.links:
                    address = urllib.parse.urlsplit(urllib.parse.urljoin(base, reference))
                    if address.hostname == origin.hostname and (address.netloc != origin.netloc or address.scheme != origin.scheme):
                        raise RuntimeError("WoltLab erzeugt eine falsche lokale Adresse (Domain, Port oder HTTPS): " + address.geturl())
                if not assets.assets:
                    raise RuntimeError("Die WoltLab-Startseite liefert keine prüfbaren Stylesheets oder Skripte.")
                for reference in dict.fromkeys(assets.assets):
                    address = urllib.parse.urljoin(base, reference)
                    if urllib.parse.urlsplit(address).netloc == origin.netloc:
                        with opener.open(local_request(address), timeout=30) as asset_response:
                            asset_response.read(1)
                mark_stage("Admin-Zugang mit den gespeicherten Zugangsdaten prüfen")
                login_jar = http.cookiejar.CookieJar()
                login_opener = urllib.request.build_opener(
                    urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(login_jar),
                    _IPv4HTTPHandler(), _IPv4HTTPSHandler(context=context) if context else _IPv4HTTPSHandler(),
                )
                login_url = urllib.parse.urljoin(base, "acp/")
                with login_opener.open(local_request(login_url), timeout=45) as login_response:
                    login_page = login_response.read().decode("utf-8", "replace")
                    login_url = login_response.geturl()
                if "rescue-mode" in login_url:
                    raise RuntimeError("Die Administration meldet eine falsche Domain oder ein falsches Verzeichnis (Rescue Mode).")
                login_form = _SetupFormParser()
                login_form.feed(login_page)
                login_fields = {**login_form.fields, "username": values.get("WSC_ADMIN_USERNAME", "admin"), "password": values.get("WSC_ADMIN_PASSWORD", ""), "send": "1"}
                login_fields["t"] = next((urllib.parse.unquote(cookie.value) for cookie in login_jar if cookie.name == "XSRF-TOKEN"), login_fields.get("t", ""))
                final_url, admin_page = _post_setup_step(login_opener, urllib.parse.urljoin(login_url, login_form.action), login_fields, login_url)
                if re.search(r'<input\b[^>]*\btype=[\"\']password[\"\']', admin_page, re.I) or "rescue-mode" in final_url or "Fatal Error" in admin_page or not re.search(r"\bUser\.init\(\s*[1-9]\d*\s*,", admin_page):
                    raise RuntimeError("Die automatische Admin-Anmeldung ist fehlgeschlagen. Die Installation wird nicht als einsatzbereit markiert.")
                verify_page_language(home_page, language)
                verify_page_language(admin_page, language)
                return f"WoltLab Suite wurde automatisch installiert und die Website geprüft. Adresse: {public_base.rstrip('/')}\nAdmin-Anmeldung: {public_base.rstrip('/')}/acp/\n{start_output}"

            data = dict(fields)
            step_labels = {"showLicense": "Lizenz bestätigen", "configureDB": "Datenbankverbindung einrichten", "createDB": "Datenbanktabellen erstellen", "createUser": "Adminzugang anlegen"}
            mark_stage("Installationsschritt: " + step_labels.get(step, step))
            data["languageCode"] = language
            if step == "showLicense":
                # The user's explicit click on “Einrichten” authorizes the standard installer flow.
                data["send"] = "1"
                data["accepted"] = "1"
            elif step == "configureDB":
                data.update({
                    "send": "1",
                    "dbHost": "database",
                    "dbUser": values.get("MYSQL_USER", "wsc"),
                    "dbPassword": values.get("MYSQL_PASSWORD", ""),
                    "dbName": values.get("MYSQL_DATABASE", "woltlab"),
                })
            elif step == "createDB":
                pass
            elif step == "createUser":
                admin_password = values.get("WSC_ADMIN_PASSWORD", "")
                admin_email = values.get("WSC_ADMIN_EMAIL", "admin@example.test")
                data.update({
                    "send": "1",
                    "username": values.get("WSC_ADMIN_USERNAME", "admin"),
                    "email": admin_email,
                    "confirmEmail": admin_email,
                    "password": admin_password,
                    "confirmPassword": admin_password,
                })
            # WoltLab compares HTTP_HOST with the parsed Referer host. For local
            # non-standard ports the Referer parser drops the port, so omit it
            # on this server-side check; browser verification is handled above.
            next_url, page = _post_setup_step(opener, install_url, data, referer=None if step == "showSystemRequirements" else install_url, host_header=host_header)
            if step == "showSystemRequirements" and 'class="badge red"' in page:
                failures = []
                for block in re.findall(r"<section class=\"section\">.*?</section>", page, re.S):
                    heading = re.search(r'<h2 class="sectionTitle">(.*?)</h2>', block, re.S)
                    badge = re.search(r'<span class="badge red">(.*?)</span>', block, re.S)
                    if heading and badge:
                        clean = lambda value: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()
                        failures.append(f"{clean(heading.group(1))}: {clean(badge.group(1))}")
                detail = "; ".join(failures) or "Voraussetzungen wurden vom Installer abgelehnt."
                raise RuntimeError(f"WoltLab-Systemcheck blockiert die automatische Einrichtung: {detail}")
            parser_next = _SetupFormParser()
            parser_next.feed(page)
            next_step = parser_next.fields.get("step", "")
            if next_step == step and step != "createDB":
                text = re.sub(r"<[^>]+>", " ", page)
                text = re.sub(r"\s+", " ", html.unescape(text)).strip()
                raise RuntimeError(f"WoltLab konnte den Schritt „{step}“ nicht abschließen: {text[:500]}")
        raise RuntimeError("WoltLab hat mehr Installationsschritte als erwartet angefordert. Bitte Logs prüfen.")
    except (urllib.error.URLError, TimeoutError, ssl.SSLError) as exc:
        raise RuntimeError(f"WoltLab-Installation wurde bei „{install_stage}“ durch einen Verbindungsfehler unterbrochen: {exc}") from exc


def project_names() -> list[str]:
    return sorted(p.name for p in PROJECTS.iterdir() if p.is_dir() and (p / "wsc-local.json").is_file()) if PROJECTS.exists() else []


def project_status(name: str) -> dict[str, Any]:
    cfg, root, _ = read_project(name)
    result = compose(name, "ps", "--format", "json", timeout=30)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Docker Compose konnte den Projektstatus nicht lesen.")
    services = []
    try:
        decoded = json.loads(result.stdout) if result.stdout.strip() else []
        rows = decoded if isinstance(decoded, list) else [decoded]
    except json.JSONDecodeError:
        rows = []
        for line in result.stdout.splitlines():
            if line.strip():
                try: rows.append(json.loads(line))
                except json.JSONDecodeError: pass
    for row in rows:
        services.append({"name": row.get("Service", "?"), "state": row.get("State", "unknown"), "status": row.get("Status", "")})
    web_row = next((row for row in rows if row.get("Service") == "web"), {})
    running = web_row.get("State") == "running"
    publishers = web_row.get("Publishers", [])
    published = {int(item["TargetPort"]): int(item["PublishedPort"]) for item in publishers if item.get("URL") == "127.0.0.1" and item.get("PublishedPort")}
    port_mismatch = running and any(published.get(target) != expected for target, expected in ((80, cfg["http_port"]), (443, cfg["https_port"])))
    status_error = "Docker veröffentlicht noch alte Ports. Klicke auf „Ports korrigieren & neu starten“." if port_mismatch else ""
    files_available = (root / "site/global.php").exists()
    state_file = root / "installation-state.json"
    installation = json.loads(state_file.read_text()) if state_file.is_file() else {"state": "unverified" if files_available else "prepared", "stage": "", "error": ""}
    site_ready = files_available and installation.get("state") == "ready"
    return {"recovery_enabled": (root / "recovery-tool.json").is_file() and (root / "site/wsc-recovery.php").is_file(), "name": name, "suite": cfg["suite_version"], "php": cfg["php_version"], "database": cfg.get("database", "mariadb"), "webserver": cfg.get("webserver", "nginx-php-fpm"), "legacy": cfg["profile_status"] == "legacy", "experimental": cfg.get("profile_status") == "development", "core_version": cfg.get("core_version", ""), "url": cfg["url"], "mail_url": f"http://127.0.0.1:{cfg['mail_port']}", "tls_enabled": cfg.get("tls_enabled", False), "running": running, "port_mismatch": port_mismatch, "status_error": status_error, "services": services, "site_ready": site_ready, "installation": installation, "files_available": files_available, "core_available": (root / "site/install.php").exists()}


def action(name: str, command: str, *args: str) -> str:
    if args[:2] == ("up", "-d"):
        cfg, root, _ = read_project(name)
        if not cfg.get("browser_gate_token"):
            cfg["browser_gate_token"] = os.urandom(16).hex()
            (root / "wsc-local.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        gate_token = cfg["browser_gate_token"]
        config_path = root / "config/nginx.conf"
        changed = ensure_apache_preflight_gate(config_path, gate_token) if cfg.get("webserver") == "apache" else ensure_fastcgi_request_metadata(config_path, gate_token)
        if (root / "site/install.php").is_file() and not (root / "site/global.php").exists():
            write_browser_preflight(root, cfg)
        if changed and "web" not in args:
            args = (*args, "--force-recreate", "web")
    result = compose(name, *args)
    output = (result.stdout + result.stderr).strip()
    # Ports can become occupied between project creation and first start.
    # Recover automatically and keep the project's files and database intact.
    if result.returncode and args[:2] == ("up", "-d") and re.search(r"address already in use|port is already allocated|bind: address", output, re.I):
        stopped = compose(name, "down", "--remove-orphans")
        if stopped.returncode:
            raise RuntimeError("Der belegte Port wurde erkannt, aber Docker konnte die teilweise gestarteten Container nicht sauber anhalten. Bitte unter „Prüfen“ die Docker-Logs ansehen.\n\n" + (stopped.stderr or stopped.stdout).strip())
        cfg, root, secret = read_project(name)
        env = dict(line.split("=", 1) for line in secret.read_text(encoding="utf-8").splitlines() if "=" in line)
        old_ports = {int(env[key]) for key in ("HTTP_PORT", "HTTPS_PORT", "MAIL_PORT") if key in env}
        tried = set(old_ports)
        last_output = output
        for _ in range(8):
            candidate = next((p for p in range(8080, 8500) if not (tried | reserved_ports(exclude=name)).intersection({p, p + 1, p + 2}) and all(not port_taken(p + offset) for offset in range(3))), None)
            if candidate is None:
                break
            tried.update({candidate, candidate + 1, candidate + 2})
            env.update(HTTP_PORT=str(candidate), HTTPS_PORT=str(candidate + 1), MAIL_PORT=str(candidate + 2))
            secret.write_text("".join(f"{key}={value}\n" for key, value in env.items()), encoding="utf-8")
            secret.chmod(0o600)
            cfg.update(http_port=candidate, https_port=candidate + 1, mail_port=candidate + 2)
            cfg["url"] = f"https://{cfg.get('domain', f'{name}.localhost')}:{candidate + 1}" if cfg.get("tls_enabled") else f"http://127.0.0.1:{candidate}"
            (root / "wsc-local.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            # A failed bind can leave a Created container with the old port mapping.
            # Remove it explicitly, then force Compose to build a fresh container.
            removed = compose(name, "rm", "--force", "--stop", "web")
            if removed.returncode:
                raise RuntimeError("Docker konnte den alten Webcontainer mit der belegten Portbindung nicht entfernen. Bitte Docker Desktop/Engine neu starten und danach erneut versuchen.\n\n" + (removed.stderr or removed.stdout).strip())
            result = compose(name, "up", "-d", "--force-recreate")
            last_output = (result.stdout + result.stderr).strip()
            if result.returncode == 0:
                return f"Ein anderer Dienst hat den bisherigen Port belegt. Ich habe freie Ports eingerichtet und das Projekt gestartet.\nAdresse: {cfg['url']}\n{last_output}".strip()
            if not re.search(r"address already in use|port is already allocated|bind: address", last_output, re.I):
                break
            compose(name, "down", "--remove-orphans")
        raise RuntimeError("Der bisherige Port war belegt. Ich habe die Container mit neuen Ports bis zu achtmal sauber neu erstellt, Docker konnte aber weiterhin keinen Port binden. Öffne „Prüfen“ und kontrolliere, ob Docker Desktop/Engine erreichbar ist.\n\n" + last_output)
    if result.returncode:
        _, root, _ = read_project(name)
        log_dir = root / "logs"
        log_dir.mkdir(exist_ok=True)
        (log_dir / "runtime.log").write_text(output, encoding="utf-8")
        detail = re.sub(r"\x1b\[[0-9;]*m", "", output)[-2200:]
        raise RuntimeError(f"Docker konnte den Vorgang „{command}“ nicht abschließen. Das vollständige Protokoll liegt unter {log_dir / 'runtime.log'}.\n{detail}")
    if args[:2] == ("up", "-d"):
        _, root, _ = read_project(name)
        (root / "logs/runtime.log").unlink(missing_ok=True)
    return output or f"{command}: fertig"


def remove_project(name: str, confirmed: bool = False) -> str:
    cfg, root, secret = read_project(name)
    if not confirmed:
        if not sys.stdin.isatty():
            raise ValueError(f"Entfernen löscht Projektdateien, Datenbank und lokale Zugangsdaten. Bitte mit 'wsc remove {name} --yes' ausdrücklich bestätigen.")
        print(f"Projekt '{name}' sowie Dateien, Datenbank und lokale Zugangsdaten endgültig entfernen?")
        if input(f"Zum Bestätigen '{name}' eingeben: ").strip() != name:
            return "Abgebrochen. Das Projekt wurde nicht verändert."

    stopped = compose(name, "down", "--volumes", "--remove-orphans")
    if stopped.returncode:
        details = (stopped.stdout + stopped.stderr).strip()
        raise RuntimeError("Docker konnte die Projekt-Container nicht sicher anhalten. Die Projektdateien bleiben erhalten.\n" + details)

    try:
        shutil.rmtree(root)
    except PermissionError:
        # Database containers commonly create bind-mounted files as UID 999.
        # Use the already-downloaded database image as a temporary root helper
        # so uninstall works without asking the user to repair permissions.
        helper_image = "mysql:8.0" if cfg.get("database") == "mysql8" else "mariadb:10.11"
        helper = subprocess.run(
            ["docker", "run", "--rm", "--user", "0:0", "--volume", f"{root}:/cleanup", helper_image, "sh", "-c", "chmod -R a+rwX /cleanup"],
            capture_output=True, text=True, timeout=120, check=False,
        )
        if helper.returncode:
            raise RuntimeError("Die Container wurden angehalten, aber Datenbankdateien sind durch Docker geschützt. Projektdateien bleiben erhalten. Starte Docker erneut und versuche das Entfernen noch einmal.\n" + (helper.stderr or helper.stdout).strip())
        shutil.rmtree(root)
    secret.unlink(missing_ok=True)
    # Remove only this project's build image. Shared PHP base images and the
    # downloaded Core archive cache stay available to other projects.
    image_service = "web" if cfg.get("webserver") == "apache" else "php"
    subprocess.run(["docker", "image", "rm", f"{cfg['project']}-{image_service}"], capture_output=True, text=True, check=False)
    return f"Projekt '{name}' vollständig entfernt. Container, Netzwerk, Projektdateien, Datenbankdateien und lokale Zugangsdaten wurden gelöscht. Gemeinsame Download- und Docker-Basis-Caches bleiben erhalten."


def service_action(name: str, service: str, command: str) -> str:
    if service != "mail" or command not in {"start", "stop", "logs"}:
        raise ValueError("Verfügbare optionale Dienste: mail (start, stop, logs).")
    if command == "start":
        return action(name, "Mail-Testdienst starten", "--profile", "mail", "up", "-d", "mail")
    if command == "stop":
        return action(name, "Mail-Testdienst stoppen", "--profile", "mail", "stop", "mail")
    return action(name, "Mail-Testdienst Logs", "--profile", "mail", "logs", "--tail", "100", "mail")


def doctor(name: str) -> str:
    cfg, root, _ = read_project(name)
    issues: list[str] = []
    notes: list[str] = []
    profile = profile_for(cfg["suite_version"])
    if cfg["profile_status"] == "legacy":
        notes.append(f"WSC {cfg['suite_version']} ist als Legacy markiert; regulärer Hersteller-Support ist nicht zu erwarten.")
    if profile.get("requires_https") and not cfg.get("tls_enabled"):
        issues.append(f"WSC {cfg['suite_version']} verlangt HTTPS. Mit 'wsc install {name}' wird lokales HTTPS automatisch eingerichtet.")
    if profile.get("unofficial"):
        notes.append("Experimentelles, inoffizielles WSC-6.3-Profil. Nicht für produktive Installationen verwenden.")
    if cfg.get("webserver") != "apache":
        nginx = (root / "config/nginx.conf").read_text(encoding="utf-8")
        if "fastcgi_param SERVER_NAME $host;" not in nginx or "fastcgi_param HTTPS $https;" not in nginx:
            issues.append("PHP erhält Hostname oder HTTPS-Status nicht zuverlässig. Mit 'wsc start NAME' wird die Webserver-Konfiguration automatisch repariert.")
    if shutil.disk_usage(root).free < 2 * 1024**3:
        issues.append("Wenig freier Speicherplatz: weniger als 2 GiB frei.")
    status = project_status(name)
    if status.get("port_mismatch"):
        issues.append(status["status_error"])
    url = urllib.parse.urlsplit(cfg["url"])
    expected_host = cfg.get("domain") if cfg.get("tls_enabled") else "127.0.0.1"
    if expected_host and url.hostname != expected_host:
        issues.append(f"Projektadresse und Hostname weichen voneinander ab: erwartet {expected_host}, konfiguriert {url.hostname or '(keiner)'}. Bitte die Projektadresse verwenden und HTTPS über die Projektaktion neu einrichten.")
    if profile.get("requires_https") and url.scheme != "https":
        issues.append("Der WSC-6.3-Installer benötigt HTTPS. Öffne den Installer erst nach „Lokales HTTPS“ über die angezeigte Projektadresse.")
    if status["running"]:
        php_service = "web" if cfg.get("webserver") == "apache" else "php"
        php = compose(name, "exec", "-T", php_service, "php", "-r", "echo json_encode(['version'=>PHP_VERSION,'bits'=>PHP_INT_SIZE*8,'extensions'=>get_loaded_extensions(),'gd_webp'=>extension_loaded('gd') && (gd_info()['WebP Support'] ?? false),'imagick_webp'=>extension_loaded('imagick') && in_array('WEBP', Imagick::queryFormats('WEBP')),'memory_limit'=>ini_get('memory_limit'),'file_uploads'=>ini_get('file_uploads'),'max_file_uploads'=>ini_get('max_file_uploads'),'upload_max_filesize'=>ini_get('upload_max_filesize'),'post_max_size'=>ini_get('post_max_size'),'sys_temp_dir'=>sys_get_temp_dir(),'tmp_exists'=>is_dir(sys_get_temp_dir()),'tmp_writable'=>is_writable(sys_get_temp_dir()),'site_writable'=>is_writable('/var/www/html'),'site_free_bytes'=>disk_free_space('/var/www/html')]);")
        if php.returncode == 0:
            try:
                info = json.loads(php.stdout)
                actual = tuple(int(x) for x in info["version"].split(".")[:3])
                minimum = tuple(int(x) for x in profile["php_min"].split("."))
                maximum = tuple(int(x) for x in profile["php_max"].split(".") + ["999"] if x.isdigit())
                if actual < minimum or actual > maximum:
                    issues.append(f"PHP {info['version']} liegt außerhalb des WSC-{cfg['suite_version']}-Profils.")
                if info.get("bits") != 64:
                    issues.append("WoltLab benötigt eine 64-Bit-PHP-Laufzeit.")
                exts = set(x.lower() for x in info["extensions"])
                required = {"ctype", "dom", "exif", "fileinfo", "gmp", "intl", "libxml", "mbstring", "openssl", "pdo", "pdo_mysql", "zlib"}
                missing = sorted(required - exts)
                if missing:
                    issues.append("PHP-Erweiterungen fehlen: " + ", ".join(missing))
                if not info.get("gd_webp") and not info.get("imagick_webp"):
                    issues.append("WoltLab benötigt GD oder ImageMagick mit WebP-Unterstützung.")
                if "curl" not in exts:
                    notes.append("PHP-Erweiterung curl fehlt (von WoltLab empfohlen).")
                if "zip" not in exts:
                    notes.append("PHP-Erweiterung zip fehlt; Paketimporte in WoltLab können eingeschränkt sein.")
                memory = str(info.get("memory_limit", "0")).strip().upper()
                memory_bytes = -1 if memory == "-1" else parse_size(memory)
                if memory_bytes != -1 and memory_bytes < 128 * 1024**2:
                    issues.append(f"PHP memory_limit={memory} liegt unter den vom Installer benötigten 128 MiB.")
                if str(info.get("file_uploads", "")).lower() not in {"1", "on", "true"}:
                    issues.append("PHP file_uploads ist deaktiviert.")
                notes.append(f"Upload-Limits: upload_max_filesize={info['upload_max_filesize']}, post_max_size={info['post_max_size']}.")
                upload_size = parse_size(str(info["upload_max_filesize"]))
                post_size = parse_size(str(info["post_max_size"]))
                if upload_size <= 0 or post_size <= 0 or post_size < upload_size:
                    issues.append("PHP-Uploadlimits sind ungültig: post_max_size muss mindestens so groß wie upload_max_filesize sein.")
                if not info.get("tmp_exists") or not info.get("tmp_writable"):
                    issues.append("PHP kann den Upload-Temporärordner nicht finden oder beschreiben.")
                if not info.get("site_writable"):
                    issues.append("PHP kann den WoltLab-Projektordner nicht beschreiben; Dateirechte prüfen.")
                if int(info.get("site_free_bytes") or 0) < 2 * 1024**3:
                    issues.append("Im Dateisystem des PHP-Containers sind weniger als 2 GiB frei.")
            except (ValueError, KeyError):
                issues.append("PHP-Systeminformationen konnten nicht gelesen werden.")
        else:
            issues.append("PHP-Laufzeit im Container ist nicht erreichbar: " + (php.stderr.strip() or php.stdout.strip() or "unbekannter Fehler"))
        database = next((service for service in status["services"] if service["name"] == "database"), None)
        if not database or database["state"] != "running" or "healthy" not in database["status"].lower():
            issues.append("Die Datenbank ist noch nicht gesund gestartet. Warte kurz und prüfe Logs, falls der Status so bleibt.")
    else:
        issues.append("Projekt ist gestoppt; PHP-Laufzeitprüfung erfolgt nach dem Start.")
    if not (root / "site").is_dir() or not os.access(root / "site", os.W_OK):
        issues.append("WoltLab-Projektordner fehlt oder ist nicht beschreibbar.")
    if cfg.get("core_available") or (root / "site/install.php").is_file():
        notes.append(f"Automatische Einrichtung: wsc install {name}. Hostname, Cookies und HTTPS werden dabei automatisch geprüft.")
    references = "WoltLab: https://manual.woltlab.com/de/requirements/ · https://manual.woltlab.com/de/installation/ · https://manual.woltlab.com/de/php-compatibility/ · https://manual.woltlab.com/de/file-uploads/"
    summary = "Keine serverseitigen Probleme gefunden." if not issues else "Prüfungen mit Handlungsbedarf:"
    lines = ["Doctor – WoltLab-Installationsprüfung", summary]
    lines.extend(f"• {item}" for item in issues)
    lines.extend(f"• Hinweis: {item}" for item in notes)
    lines.append("\n" + references)
    return "\n".join(lines)


def parse_size(value: str) -> int:
    match = re.fullmatch(r"\s*([1-9][0-9]*)\s*(B|K|KB|M|MB|G|GB)?\s*", value, re.I)
    if not match:
        raise ValueError("Uploadgröße bitte als z. B. 256M oder 1G angeben.")
    scale = {None: 1, "B": 1, "K": 1024, "KB": 1024, "M": 1024**2, "MB": 1024**2, "G": 1024**3, "GB": 1024**3}[match.group(2).upper() if match.group(2) else None]
    size = int(match.group(1)) * scale
    if size > 4 * 1024**3:
        raise ValueError("Uploadlimit darf höchstens 4G sein.")
    return size


def format_size(size: int) -> str:
    for suffix, unit in (("G", 1024**3), ("M", 1024**2), ("K", 1024)):
        if size >= unit and size % unit == 0:
            return f"{size // unit}{suffix}"
    return f"{size}B"


def update_upload_limits(name: str, size: str, apply: bool = False, confirmed: bool = False) -> str:
    cfg, root, _ = read_project(name)
    target_bytes = parse_size(size)
    post_bytes = ((target_bytes * 5 // 4 + 1024**2 - 1) // (1024**2)) * 1024**2
    php_path, nginx_path = root / "config/php.ini", root / "config/nginx.conf"
    php_before, nginx_before = php_path.read_text(encoding="utf-8"), nginx_path.read_text(encoding="utf-8")

    def replace_ini(content: str, key: str, value: str) -> str:
        pattern = re.compile(rf"^\s*;?\s*{re.escape(key)}\s*=.*$", re.I | re.M)
        line = f"{key}={value}"
        updated, count = pattern.subn(line, content)
        if not count:
            updated = updated.rstrip() + "\n" + line
        return updated.rstrip() + "\n"

    def current_ini(content: str, key: str) -> str:
        match = re.search(rf"^\s*;?\s*{re.escape(key)}\s*=\s*([^;\s]+)", content, re.I | re.M)
        return match.group(1) if match else "nicht gesetzt"

    php_after = replace_ini(php_before, "upload_max_filesize", format_size(target_bytes))
    php_after = replace_ini(php_after, "post_max_size", format_size(post_bytes))
    if cfg.get("webserver") == "apache":
        nginx_after = nginx_before
        request_limit = "Apache does not add a separate request limit in this profile"
    else:
        nginx_pattern = re.compile(r"^\s*client_max_body_size\s+[^;]+;\s*$", re.M)
        nginx_line = f"    client_max_body_size {format_size(post_bytes)};"
        if nginx_pattern.search(nginx_before):
            nginx_after = nginx_pattern.sub(nginx_line, nginx_before)
        else:
            nginx_after = nginx_before.replace("server {", "server {\n" + nginx_line, 1)
        old_limits = ", ".join(re.findall(r"^\s*client_max_body_size\s+([^;\s]+)", nginx_before, re.M)) or "nicht gesetzt"
        request_limit = f"Nginx client_max_body_size: {old_limits} → {format_size(post_bytes)}"
    diff = [f"PHP upload_max_filesize: {current_ini(php_before, 'upload_max_filesize')} → {format_size(target_bytes)}", f"PHP post_max_size: {current_ini(php_before, 'post_max_size')} → {format_size(post_bytes)}", request_limit]
    webserver_note = "Apache setzt in diesem Profil kein zusätzliches Request-Limit; PHP begrenzt die Uploadgröße." if cfg.get("webserver") == "apache" else "Nginx muss zusätzlich ein passendes Request-Limit erhalten."
    preview = "Vorschau der geplanten Änderung\n" + "\n".join(f"• {line}" for line in diff) + f"\n\nWoltLab verlangt, dass post_max_size größer als upload_max_filesize ist. {webserver_note} https://manual.woltlab.com/de/file-uploads/"
    if not apply:
        return preview + "\n\nNoch nichts geändert. Anwenden: wsc uploads " + name + " --size " + size + " --apply"
    if confirmed:
        pass
    elif sys.stdin.isatty():
        answer = input(preview + "\n\nDiese Werte anwenden und PHP/Webserver neu laden? [ja/NEIN] ")
        if answer.strip().lower() != "ja":
            return "Abgebrochen; Konfiguration blieb unverändert."
    else:
        raise ValueError("Änderung braucht eine interaktive Bestätigung. Nutze das Terminal und wiederhole den Befehl mit --apply.")
    backup_php, backup_nginx = php_before, nginx_before
    php_path.write_text(php_after, encoding="utf-8")
    nginx_path.write_text(nginx_after, encoding="utf-8")
    if project_status(name)["running"]:
        services = ("web",) if cfg.get("webserver") == "apache" else ("php", "web")
        result = compose(name, "up", "-d", "--force-recreate", *services)
        if result.returncode:
            php_path.write_text(backup_php, encoding="utf-8")
            nginx_path.write_text(backup_nginx, encoding="utf-8")
            compose(name, "up", "-d", "--force-recreate", *services)
            raise RuntimeError("Dienste konnten die Änderung nicht laden; vorherige Konfiguration wurde zurückgesetzt. " + result.stderr.strip())
    return "Upload-Limits angewandt. PHP und Webserver verwenden die bestätigten Werte."


RECOVERY_URL = "https://www.woltlab.com/media/299-wsc-recovery-php/"


def recovery_install(name: str, confirmed: bool = False) -> str:
    _, root, _ = read_project(name)
    if not (root / "site/global.php").is_file():
        raise ValueError("Recovery benötigt eine installierte WoltLab Suite. Richte das Projekt zuerst vollständig ein.")
    if not confirmed and (not sys.stdin.isatty() or input("Das offizielle WoltLab Recovery Tool wird temporär als öffentlich erreichbare PHP-Datei abgelegt. Sicherung vorher erstellen und nach der Nutzung sofort entfernen. Fortfahren? [ja/NEIN] ").strip().lower() != "ja"):
        return "Abgebrochen."
    destination = root / "site/wsc-recovery.php"
    if destination.exists():
        raise ValueError("wsc-recovery.php existiert bereits; erst prüfen oder entfernen.")
    request = urllib.request.Request(RECOVERY_URL, headers={"User-Agent": "wsc-local/Workbench"})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            content = response.read(4 * 1024 * 1024 + 1)
    except (OSError, urllib.error.URLError) as exc:
        raise RuntimeError("Das offizielle Recovery Tool konnte nicht geladen werden. Prüfe die Internetverbindung und versuche es erneut. Es wurde keine Recovery-Datei abgelegt.") from exc
    if len(content) > 4 * 1024 * 1024 or not content.lstrip().startswith(b"<?php"):
        raise ValueError("Die offizielle Downloadantwort sah nicht wie das erwartete PHP-Hilfsskript aus; nichts wurde installiert.")
    safety_copy = snapshot(name)
    destination.write_bytes(content)
    destination.chmod(0o644)
    manifest = root / "recovery-tool.json"
    try:
        manifest.write_text(json.dumps({"path": "site/wsc-recovery.php", "sha256": hashlib.sha256(content).hexdigest(), "source": RECOVERY_URL, "installed_at": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n", encoding="utf-8")
    except OSError:
        destination.unlink(missing_ok=True)
        raise
    backup_message = f"\nSicherung vor der Recovery-Aktion: {safety_copy}" if safety_copy else ""
    return f"Offizielles WoltLab Recovery Tool bereit: {read_project(name)[0]['url']}/wsc-recovery.php{backup_message}\nNach Gebrauch sofort entfernen: wsc recovery remove {name}\nWoltLab-Anleitung: https://manual.woltlab.com/de/recovery-tool/"


def recovery_remove(name: str, confirmed: bool = False) -> str:
    _, root, _ = read_project(name)
    manifest = root / "recovery-tool.json"
    if not manifest.is_file():
        raise ValueError("Es gibt keinen von wsc-local verwalteten Recovery-Installationsnachweis.")
    record = json.loads(manifest.read_text(encoding="utf-8"))
    target = (root / record.get("path", "")).resolve()
    if root.resolve() not in target.parents or target.name != "wsc-recovery.php" or not target.is_file():
        raise ValueError("Der Recovery-Pfad ist ungültig oder die Datei fehlt.")
    if file_hash(target) != record.get("sha256"):
        raise ValueError("Recovery-Datei hat sich verändert. Sie wird nicht automatisch gelöscht; prüfe und entferne sie manuell.")
    authorization = root / "site/wsc-recovery-auth.php"
    if authorization.exists() or authorization.is_symlink():
        # Recognize only the official inert authorization-file format. Never
        # remove an arbitrary changed PHP file under this reserved filename.
        if authorization.is_symlink() or not authorization.is_file() or authorization.stat().st_size > 4096 or not re.fullmatch(rb"<\?php exit; /\* --- DO NOT EDIT THIS FILE --- \*/ \?>\r?\n[0-9]{10}\r?\n[a-f0-9]{40}\s*", authorization.read_bytes()):
            raise ValueError("Die Recovery-Authentifizierungsdatei hat ein unbekanntes Format. Prüfe sie manuell; es wurde keine Recovery-Datei gelöscht.")
    if not confirmed and (not sys.stdin.isatty() or input("Recovery Tool entfernen? [ja/NEIN] ").strip().lower() != "ja"):
        return "Abgebrochen."
    authorization.unlink(missing_ok=True)
    target.unlink()
    manifest.unlink()
    return "Recovery-Datei und gegebenenfalls die offizielle Authentifizierungsdatei entfernt. Prüfe zusätzlich im Browser, dass /wsc-recovery.php nicht mehr erreichbar ist."


def local_tls(name: str, enable: bool, confirmed: bool = False) -> str:
    cfg, root, _ = read_project(name)
    if not cfg.get("browser_gate_token"):
        cfg["browser_gate_token"] = os.urandom(16).hex()
        (root / "wsc-local.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    gate_token = cfg["browser_gate_token"]
    apache = cfg.get("webserver") == "apache"
    config_path = root / "config/apache.conf" if apache else root / "config/nginx.conf"
    content = config_path.read_text(encoding="utf-8")
    begin, end = "# wsc-local TLS begin", "# wsc-local TLS end"
    if not confirmed and (not sys.stdin.isatty() or input(f"Lokales TLS für '{name}' {'einrichten' if enable else 'abschalten'}? [ja/NEIN] ").strip().lower() != "ja"):
        return "Abgebrochen; TLS wurde nicht geändert."
    if enable:
        if cfg.get("tls_enabled"):
            return f"TLS ist bereits eingerichtet: {cfg['url']}"
        mkcert = shutil.which("mkcert")
        if not mkcert:
            raise ValueError("mkcert ist nicht installiert. Anleitung: https://github.com/FiloSottile/mkcert")
        tls_env = tls_environment()
        domain = f"{name}.localhost"
        ca = subprocess.run([mkcert, "-install"], capture_output=True, text=True, check=False, env=tls_env)
        if ca.returncode:
            raise RuntimeError("mkcert konnte das lokale CA-Zertifikat nicht einrichten. " + (ca.stderr or ca.stdout).strip())
        cert = root / "tls/fullchain.pem"
        key = root / "tls/privkey.pem"
        result = subprocess.run([mkcert, "-cert-file", str(cert), "-key-file", str(key), "localhost", "127.0.0.1", domain], capture_output=True, text=True, check=False, env=tls_env)
        if result.returncode:
            raise RuntimeError("Lokales Zertifikat konnte nicht erzeugt werden. " + (result.stderr or result.stdout).strip())
        key.chmod(0o600)
        cfg["tls_certificate_sha256"] = hashlib.sha256(cert.read_bytes() + key.read_bytes()).hexdigest()
        if apache:
            server = f'''\n{begin}
<VirtualHost *:443>
    ServerName {domain}
    RewriteEngine On
    RewriteCond %{{REQUEST_URI}} ^/(?:test|install)\\.php$ [NC]
    RewriteCond %{{HTTP:Cookie}} !(^|;\\s*)wsc_local_browser_verified=1(;|$) [NC]
    RewriteRule ^ - [F,L]
    DocumentRoot /var/www/html
    DirectoryIndex index.php index.html
    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/wsc-local.pem
    SSLCertificateKeyFile /etc/ssl/private/wsc-local.key
    <Directory /var/www/html>
        Options FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
    <FilesMatch "^\\.(?:env|ini|log|sql|bak)$">
        Require all denied
    </FilesMatch>
</VirtualHost>
{end}\n'''
        else:
            server = f'''\n{begin}
server {{
    if ($wsc_local_deny_systemtest) {{ return 403 "Run /wsc-local-check.html first."; }}
    if ($wsc_local_deny_installer) {{ return 403 "Confirm the WoltLab system test in /wsc-local-check.html first."; }}
    listen 443 ssl;
    server_name {domain} localhost;
    root /var/www/html;
    index index.php index.html;
    client_max_body_size 160M;
    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;
    location / {{ try_files $uri $uri/ /index.php?$query_string; }}
    location ~ \\.php(?:$|/) {{
        fastcgi_split_path_info ^(.+?\\.php)(/.*)$;
        try_files $fastcgi_script_name =404;
        include fastcgi_params;
        fastcgi_param SERVER_NAME $host;
        fastcgi_param HTTP_HOST $http_host;
        fastcgi_param SERVER_PORT $server_port;
        fastcgi_param REQUEST_SCHEME $scheme;
        fastcgi_param HTTPS $https;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_param PATH_INFO $fastcgi_path_info;
        fastcgi_param HTTP_PROXY "";
        fastcgi_pass php:9000;
        fastcgi_read_timeout 300;
    }}
    location ~* \\.(?:env|ini|log|sql|bak)$ {{ deny all; }}
}}
{end}\n'''
        config_path.write_text(content.rstrip() + server, encoding="utf-8")
        cfg["tls_enabled"] = True
        cfg["domain"] = domain
        cfg["url"] = f"https://{domain}:{cfg['https_port']}"
    else:
        if not cfg.get("tls_enabled"):
            return "TLS war für dieses Projekt nicht eingerichtet."
        if begin in content and end in content:
            start, stop = content.index(begin), content.index(end) + len(end)
            config_path.write_text((content[:start] + content[stop:]).rstrip() + "\n", encoding="utf-8")
        cert, key = root / "tls/fullchain.pem", root / "tls/privkey.pem"
        expected_hash = cfg.get("tls_certificate_sha256")
        actual_hash = hashlib.sha256(cert.read_bytes() + key.read_bytes()).hexdigest() if cert.is_file() and key.is_file() else ""
        if expected_hash and actual_hash == expected_hash:
            cert.unlink(missing_ok=True)
            key.unlink(missing_ok=True)
        elif (cert.is_file() and cert.stat().st_size) or (key.is_file() and key.stat().st_size):
            print("Hinweis: Zertifikatsdateien wurden verändert und bleiben daher erhalten.", file=sys.stderr)
        cert.parent.mkdir(parents=True, exist_ok=True)
        cert.touch(exist_ok=True)
        key.touch(exist_ok=True)
        cfg.pop("tls_certificate_sha256", None)
        cfg["tls_enabled"] = False
        cfg.pop("domain", None)
        cfg["url"] = f"http://127.0.0.1:{cfg['http_port']}"
    (root / "wsc-local.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if apache:
        ensure_apache_preflight_gate(config_path, gate_token)
    else:
        ensure_fastcgi_request_metadata(config_path, gate_token)
    write_browser_preflight(root, cfg)
    if project_status(name)["running"]:
        result = compose(name, "up", "-d", "--force-recreate", "web")
        if result.returncode:
            raise RuntimeError("Der Webserver konnte die lokale TLS-Konfiguration nicht laden. " + result.stderr.strip())
    return f"Lokales TLS {'eingerichtet' if enable else 'entfernt'}: {cfg['url']}"


def redact_export_database_config(site: Path) -> None:
    """Replace local database credentials in the export copy, never in the site."""
    config = site / "config.inc.php"
    content = config.read_text(encoding="utf-8")
    literal = r"(?:'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\")"
    values = {"dbHost": "localhost", "dbUser": "CHANGE_ME", "dbPassword": "CHANGE_ME", "dbName": "CHANGE_ME"}
    for key, value in values.items():
        content, count = re.subn(rf"\${key}\s*=\s*{literal}\s*;", lambda _: f"${key} = '{value}';", content)
        if count != 1:
            raise ValueError("Server-Export abgebrochen: Die lokale Datenbankkonfiguration konnte nicht eindeutig bereinigt werden.")
    content = re.sub(r"\$dbPort\s*=\s*\d+\s*;", "$dbPort = 0;", content)
    config.write_text(content, encoding="utf-8")


def snapshot(name: str, export: bool = False) -> Path:
    cfg, root, _ = read_project(name)
    status = project_status(name)
    if not status.get("files_available"):
        raise ValueError("WSC-Dateien fehlen. Für einen vollständigen Stand muss site/global.php vorhanden sein.")
    was_running = status["running"]
    if was_running:
        action(name, "stop", "stop", "--timeout", "60")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = root / "exports" / f"{name}-{stamp}.tar.gz" if export else root / "snapshots" / f"{stamp}"
    target.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="wsc-snapshot-"))
    try:
        database = work / "database.sql"
        up = compose(name, "up", "-d", "--wait", "database")
        if up.returncode:
            raise RuntimeError(up.stderr.strip() or "Datenbank konnte nicht gestartet werden.")
        db_prefix = "mysql" if cfg.get("database") == "mysql8" else "mariadb"
        root_var = "MYSQL_ROOT_PASSWORD" if db_prefix == "mysql" else "MARIADB_ROOT_PASSWORD"
        database_var = "MYSQL_DATABASE" if db_prefix == "mysql" else "MARIADB_DATABASE"
        dump_binary = "mysqldump" if db_prefix == "mysql" else "mariadb-dump"
        dump = compose(name, "exec", "-T", "database", "sh", "-lc", f'{dump_binary} -uroot -p"${root_var}" --default-character-set=utf8mb4 --hex-blob --single-transaction --routines --triggers "${database_var}"')
        if dump.returncode or not dump.stdout.strip():
            raise RuntimeError("Datenbank-Dump fehlgeschlagen oder leer. " + dump.stderr.strip()[-1200:])
        database.write_text(dump.stdout, encoding="utf-8")
        if export:
            export_site = work / "site"
            shutil.copytree(root / "site", export_site, ignore=shutil.ignore_patterns("wsc-local-check.html", "wsc-local-browser-check.php", "wsc-recovery.php", "wsc-recovery-auth.php", "wsc-local-acp-*.php"))
            redact_export_database_config(export_site)
            manifest = {"schema": 1, "project": name, "created_at": datetime.now(timezone.utc).isoformat(), "files_sha256": tree_hash(export_site), "database_sha256": file_hash(database), "suite_version": cfg["suite_version"], "php_version": cfg["php_version"]}
            (work / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            with tarfile.open(target, "w:gz") as archive:
                archive.add(export_site, arcname="site")
                archive.add(database, arcname="database.sql")
                export_config = dict(cfg)
                export_config.pop("browser_gate_token", None)
                config_payload = json.dumps(export_config, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
                config_info = tarfile.TarInfo("wsc-local.json")
                config_info.size = len(config_payload)
                archive.addfile(config_info, io.BytesIO(config_payload))
                archive.add(work / "manifest.json", arcname="manifest.json")
                readme = work / "IMPORT.md"
                readme.write_text("""# WoltLab-Serverumzug: Importhinweise

Dieses Paket enthält den gemeinsam erstellten Stand aus WoltLab-Dateien und Datenbank sowie die nicht geheime Projektkonfiguration. Lokale Passwörter, Zertifikate, Containerdaten und persönliche Einstellungen fehlen absichtlich.

1. Am Zielserver PHP-Erweiterungen und Datenbankversion passend zur Suite-Version prüfen.
2. Dateien und Datenbank einspielen; beide stammen aus derselben angehaltenen Installation.
3. Neue Datenbankzugangsdaten in `config.inc.php` eintragen und Dateirechte prüfen.
4. Domain und Verzeichnisstruktur mit der WoltLab-Administrationsoberfläche bzw. der offiziellen Anleitung anpassen.
5. Reverse Proxy und HTTPS für die öffentliche Domain einrichten. Let's Encrypt funktioniert mit einer öffentlichen Domain und passender Challenge, nicht mit `localhost`.
6. Nach dem Umzug Anmeldungen, Uploads, E-Mail-Versand und Hintergrundaufgaben prüfen.

WoltLab-Handbuch (eigene Anleitung und Quellen):
- Datensicherung: https://manual.woltlab.com/de/backup/
- Serverumzug: https://manual.woltlab.com/de/server-migration/
- PHP-Kompatibilität: https://manual.woltlab.com/de/php-compatibility/
- Datei-Uploads: https://manual.woltlab.com/de/file-uploads/
- Verzeichnisstruktur: https://manual.woltlab.com/de/customize-directory-structure/
- Let's Encrypt / localhost: https://letsencrypt.org/docs/certificates-for-localhost/
""", encoding="utf-8")
                archive.add(readme, arcname="IMPORT.md")
            if not target.is_file() or target.stat().st_size == 0:
                raise RuntimeError("Server-Export ist leer oder unvollständig.")
        else:
            target.mkdir()
            shutil.copytree(root / "site", target / "site", ignore=shutil.ignore_patterns("wsc-local-check.html", "wsc-local-browser-check.php", "wsc-recovery.php", "wsc-recovery-auth.php", "wsc-local-acp-*.php"))
            shutil.copy2(database, target / "database.sql")
            meta = {"schema": 1, "project": name, "created_at": datetime.now(timezone.utc).isoformat(), "files_sha256": tree_hash(target / "site"), "database_sha256": file_hash(database), "suite_version": cfg["suite_version"], "php_version": cfg["php_version"]}
            (target / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
            if file_hash(target / "database.sql") != meta["database_sha256"] or tree_hash(target / "site") != meta["files_sha256"]:
                raise RuntimeError("Snapshot-Prüfsumme stimmt nicht; Snapshot wird verworfen.")
    except Exception:
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        elif target.exists():
            target.unlink()
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
        if was_running:
            action(name, "start", "up", "-d")
        else:
            action(name, "stop", "down")
    return target


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(bytes.fromhex(file_hash(path)))
    return digest.hexdigest()


def align_database_config(site: Path, secret: Path) -> bool:
    config = site / "config.inc.php"
    if not config.is_file():
        return False
    values = parse_env(secret)
    replacements = {
        "dbHost": "database",
        "dbPort": "3306",
        "dbUser": values.get("MYSQL_USER", "wsc"),
        "dbPassword": values.get("MYSQL_PASSWORD", ""),
        "dbName": values.get("MYSQL_DATABASE", "woltlab"),
    }
    content = config.read_text(encoding="utf-8")
    updated = content
    for key, value in replacements.items():
        pattern = re.compile(rf"^(\s*\${key}\s*=\s*)(?:'[^']*'|\"[^\"]*\"|[^;]+)(\s*;)", re.M)
        php_value = str(value) if key == "dbPort" else "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"
        updated, count = pattern.subn(rf"\g<1>{php_value}\g<2>", updated, count=1)
        if count != 1:
            return False
    config.write_text(updated, encoding="utf-8")
    return True


def restore(name: str, archive: Path, yes: bool = False) -> str:
    cfg, root, secret = read_project(name)
    if not yes:
        if not sys.stdin.isatty():
            raise ValueError("Restore überschreibt Dateien und Datenbank. Interaktiv bestätigen oder --yes angeben.")
        answer = input(f"Restore für '{name}' überschreibt aktuelle Dateien und Datenbank. Fortfahren? [ja/NEIN] ")
        if answer.strip().lower() != "ja":
            return "Abgebrochen."
    if archive.is_dir():
        snap = archive
        manifest = json.loads((snap / "manifest.json").read_text(encoding="utf-8"))
        if file_hash(snap / "database.sql") != manifest["database_sha256"] or tree_hash(snap / "site") != manifest["files_sha256"]:
            raise ValueError("Snapshot-Prüfung fehlgeschlagen; Dateien oder Dump sind verändert/unvollständig.")
        site = snap / "site"
        dump = snap / "database.sql"
    else:
        work = Path(tempfile.mkdtemp(prefix="wsc-import-"))
        try:
            with tarfile.open(archive, "r:gz") as tar:
                for member in tar.getmembers():
                    if member.issym() or member.islnk() or member.name.startswith("/"):
                        raise ValueError("Export enthält nicht erlaubte Links oder absolute Dateipfade.")
                    if not (member.isdir() or member.isfile()):
                        raise ValueError("Export enthält einen nicht erlaubten Dateityp.")
                    target = (work / member.name).resolve()
                    if target != work.resolve() and work.resolve() not in target.parents:
                        raise ValueError("Export enthält einen ungültigen Dateipfad.")
                tar.extractall(work)
            site, dump = work / "site", work / "database.sql"
            if not site.is_dir() or not dump.is_file() or not (work / "wsc-local.json").is_file():
                raise ValueError("Export ist unvollständig; benötigt werden site/, database.sql und wsc-local.json.")
            current_cfg = json.loads((work / "wsc-local.json").read_text(encoding="utf-8"))
            if current_cfg.get("suite_version") != cfg["suite_version"]:
                raise ValueError("Export und Zielprojekt verwenden unterschiedliche WSC-Hauptversionen.")
            if current_cfg.get("database", "mariadb") != cfg.get("database", "mariadb"):
                raise ValueError("Export und Zielprojekt verwenden verschiedene Datenbankprofile.")
            if (work / "manifest.json").is_file():
                manifest = json.loads((work / "manifest.json").read_text(encoding="utf-8"))
                if file_hash(dump) != manifest.get("database_sha256") or tree_hash(site) != manifest.get("files_sha256"):
                    raise ValueError("Export-Prüfsummen stimmen nicht; das Paket ist beschädigt oder wurde verändert.")
        except Exception:
            shutil.rmtree(work, ignore_errors=True)
            raise
    was_running = project_status(name)["running"]
    restored = False
    try:
        if (root / "site/global.php").is_file():
            safety_copy = snapshot(name)
            print(f"Sicherung vor Restore: {safety_copy}")
        action(name, "stop", "down")
        replacement = root / ".site-restore"
        shutil.rmtree(replacement, ignore_errors=True)
        shutil.copytree(site, replacement)
        config_updated = align_database_config(replacement, secret)
        action(name, "start database", "up", "-d", "--wait", "database")
        db_client = "mysql" if cfg.get("database") == "mysql8" else "mariadb"
        root_var = "MYSQL_ROOT_PASSWORD" if db_client == "mysql" else "MARIADB_ROOT_PASSWORD"
        database_var = "MYSQL_DATABASE" if db_client == "mysql" else "MARIADB_DATABASE"
        drop_command = f'{db_client} -uroot -p"${root_var}" -e "DROP DATABASE IF EXISTS woltlab; CREATE DATABASE woltlab;"'
        proc = compose(name, "exec", "-T", "database", "sh", "-lc", drop_command, timeout=900)
        if proc.returncode:
            raise RuntimeError("Datenbank konnte für den Restore nicht vorbereitet werden: " + proc.stderr.strip())
        import_command = f'{db_client} -uroot -p"${root_var}" "${database_var}"'
        sql = compose(name, "exec", "-T", "database", "sh", "-lc", import_command, input_text=dump.read_text(encoding="utf-8"), timeout=900)
        if sql.returncode:
            raise RuntimeError("Datenbank-Restore fehlgeschlagen: " + sql.stderr.strip() + (f" Die vorherige Sicherung liegt unter {safety_copy}." if 'safety_copy' in locals() else ""))
        old = root / ".site-before-restore"
        if old.exists():
            shutil.rmtree(old)
        if (root / "site").exists():
            (root / "site").rename(old)
        try:
            replacement.rename(root / "site")
        except Exception:
            if old.exists() and not (root / "site").exists():
                old.rename(root / "site")
            raise
        shutil.rmtree(old, ignore_errors=True)
        restored = True
        message = "WoltLab-Dateien und Datenbank wurden eingespielt. Zugangsdaten und Domain nach dem Serverumzug im WoltLab-Handbuch prüfen."
        if config_updated:
            message += " Die lokale config.inc.php wurde auf die Ziel-Datenbank dieses Projekts angepasst."
        elif (root / "site/global.php").is_file():
            message += " Prüfe config.inc.php und Datenbankzugangsdaten; automatische Anpassung war mit diesem Dateiformat nicht möglich."
        return message
    finally:
        if 'work' in locals():
            shutil.rmtree(work, ignore_errors=True)
        if restored and was_running:
            action(name, "start", "up", "-d")
        elif not restored:
            action(name, "cleanup", "down")
        else:
            action(name, "cleanup", "down")


def parse_env(path: Path) -> dict[str, str]:
    return dict(line.split("=", 1) for line in path.read_text().splitlines() if "=" in line and not line.startswith("#"))


def import_legacy(source: Path, name: str) -> str:
    source = source.expanduser().resolve()
    if not (source / ".env").is_file() or not (source / "woltlab").is_dir():
        raise ValueError("Kein wsc-local-Bestand erkannt: erwartet werden .env und woltlab/.")
    env = parse_env(source / ".env")
    suite = env.get("WSC_VERSION", "6.2").rsplit(".", 1)[0]
    if suite not in {p["suite"] for p in PROFILES}:
        suite = "6.2"
    old_compose = (source / "docker-compose.yml").read_text(encoding="utf-8", errors="ignore") if (source / "docker-compose.yml").is_file() else ""
    old_dockerfile = (source / "Dockerfile").read_text(encoding="utf-8", errors="ignore") if (source / "Dockerfile").is_file() else ""
    database = "mysql8" if re.search(r"image:\s*mysql(?::|\s)", old_compose) else "mariadb"
    webserver = "apache" if "apache" in old_dockerfile.lower() else "nginx-php-fpm"
    args = argparse.Namespace(name=name, suite=suite, php=None, legacy_ack=True, experimental_ack=True, port=None, zip=None, download_core=False, version="6.2.8", sha256=None, database=database, webserver=webserver)
    msg = create_project(args)
    _, dest, _ = read_project(name)
    shutil.copytree(source / "woltlab", dest / "site", dirs_exist_ok=True)
    old_snaps = source / "snapshots"
    if old_snaps.is_dir():
        shutil.copytree(old_snaps, dest / "legacy-snapshots", dirs_exist_ok=True)
    return msg + f"\nDateien und vorhandene Snapshots wurden übernommen. Der frühere Datenbank-Datenordner wird nicht automatisch in MariaDB konvertiert; den vollständigen Stand bitte über einen verifizierten Snapshot/Export importieren."


def import_bundle(source: Path, name: str) -> str:
    source = source.expanduser().resolve()
    if source.is_dir() and (source / ".env").is_file():
        return import_legacy(source, name)
    if source.is_dir() and (source / "woltlab_files.tar.gz").is_file() and (source / "database.sql").is_file():
        return import_legacy_snapshot(source, name)
    if not source.is_file():
        raise ValueError("Importquelle nicht gefunden.")
    try:
        with tarfile.open(source, "r:gz") as archive:
            member = archive.getmember("wsc-local.json")
            if not member.isfile():
                raise ValueError("Exportprofil im Archiv ist keine Datei.")
            handle = archive.extractfile(member)
            cfg = json.load(handle) if handle else None
    except (tarfile.TarError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError("Kein gültiger wsc-local Server-Export (erwartet wird .tar.gz).") from exc
    if not isinstance(cfg, dict) or cfg.get("suite_version") not in {p["suite"] for p in PROFILES}:
        raise ValueError("Das Exportprofil enthält kein unterstütztes WoltLab-Profil.")
    if instance_paths(name)[0].exists():
        raise ValueError(f"Projekt '{name}' existiert bereits.")
    create_args = argparse.Namespace(name=name, suite=cfg["suite_version"], php=cfg.get("php_version"), legacy_ack=True, experimental_ack=True, port=None, zip=None, download_core=False, version="6.2.8", sha256=None, database=cfg.get("database", "mariadb"), webserver=cfg.get("webserver", "nginx-php-fpm"))
    create_project(create_args)
    return restore(name, source, yes=True)


def import_legacy_snapshot(source: Path, name: str) -> str:
    root, _ = instance_paths(name)
    if root.exists():
        cfg, target_root, _ = read_project(name)
        suite = cfg["suite_version"]
    else:
        legacy_root = source.parent.parent
        if (legacy_root / "wsc-local.json").is_file():
            suite = json.loads((legacy_root / "wsc-local.json").read_text(encoding="utf-8")).get("suite_version", "")
        elif (legacy_root / ".env").is_file():
            old_env = parse_env(legacy_root / ".env")
            suite = old_env.get("WSC_VERSION", "").rsplit(".", 1)[0]
        else:
            raise ValueError("WSC-Version des alten Snapshots nicht gefunden. Zuerst den alten wsc-local-Ordner importieren.")
        if suite not in {p["suite"] for p in PROFILES}:
            raise ValueError(f"WSC-Profil '{suite}' wird nicht unterstützt.")
        legacy_compose = (legacy_root / "docker-compose.yml").read_text(encoding="utf-8", errors="ignore") if (legacy_root / "docker-compose.yml").is_file() else ""
        legacy_dockerfile = (legacy_root / "Dockerfile").read_text(encoding="utf-8", errors="ignore") if (legacy_root / "Dockerfile").is_file() else ""
        database = "mysql8" if re.search(r"image:\s*mysql(?::|\s)", legacy_compose) else "mariadb"
        webserver = "apache" if "apache" in legacy_dockerfile.lower() else "nginx-php-fpm"
        create_args = argparse.Namespace(name=name, suite=suite, php=None, legacy_ack=True, experimental_ack=True, port=None, zip=None, download_core=False, version="6.2.8", sha256=None, database=database, webserver=webserver)
        create_project(create_args)
        _, target_root, _ = read_project(name)
    work = Path(tempfile.mkdtemp(prefix="wsc-legacy-snapshot-"))
    try:
        extracted = work / "site"
        extracted.mkdir()
        with tarfile.open(source / "woltlab_files.tar.gz", "r:gz") as archive:
            for member in archive.getmembers():
                if not (member.isdir() or member.isfile()) or member.issym() or member.islnk() or member.name.startswith("/"):
                    raise ValueError("Alter Snapshot enthält einen nicht erlaubten Dateityp oder Pfad.")
                resolved = (extracted / member.name).resolve()
                if resolved != extracted.resolve() and extracted.resolve() not in resolved.parents:
                    raise ValueError("Alter Snapshot enthält einen Dateipfad außerhalb des Archivs.")
            archive.extractall(extracted)
        if not any((extracted / marker).is_file() for marker in ("install.php", "global.php")):
            raise ValueError("Im Dateiarchiv des alten Snapshots wurde kein WoltLab Core erkannt.")
        if not (source / "database.sql").stat().st_size:
            raise ValueError("Der alte Snapshot enthält keinen verwendbaren Datenbank-Dump.")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        modern = target_root / "snapshots" / stamp
        modern.parent.mkdir(parents=True, exist_ok=True)
        modern.mkdir()
        shutil.copytree(extracted, modern / "site")
        shutil.copy2(source / "database.sql", modern / "database.sql")
        manifest = {"schema": 1, "project": name, "source": "wsc-local legacy snapshot", "created_at": datetime.now(timezone.utc).isoformat(), "files_sha256": tree_hash(modern / "site"), "database_sha256": file_hash(modern / "database.sql"), "suite_version": suite}
        (modern / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        restore(name, modern, yes=True)
        return f"Alter Snapshot übernommen und geprüft: {modern}. WSC {suite}."
    finally:
        shutil.rmtree(work, ignore_errors=True)


def list_snapshots(name: str) -> str:
    _, root, _ = read_project(name)
    directory = root / "snapshots"
    if not directory.is_dir():
        return f"Noch keine Sicherungen. Mit 'wsc snapshot {name}' eine erstellen."
    rows = []
    for item in sorted(directory.iterdir(), reverse=True):
        if not item.is_dir() or not (item / "manifest.json").is_file():
            continue
        try:
            size = sum(path.stat().st_size for path in item.rglob("*") if path.is_file())
        except OSError:
            size = 0
        rows.append(f"{item.name}  ({size / 1024**2:.1f} MiB)  {item}")
    return "\n".join(rows) if rows else f"Noch keine Sicherungen. Mit 'wsc snapshot {name}' eine erstellen."


def guide(name: str, topic: str) -> str:
    cfg, root, _ = read_project(name)
    if topic not in {"domain", "directory", "migration"}:
        raise ValueError("Hilfethemen: domain, directory, migration.")
    if not (root / "site/global.php").is_file():
        raise ValueError("Diese Hilfe benötigt eine installierte WoltLab Suite. Richte das Projekt zuerst vollständig ein.")
    archive = snapshot(name, export=(topic == "migration"))
    if topic == "domain":
        details = f"\n1. Öffne zuerst die gewünschte Projektadresse {cfg['url']} und melde dich in WoltLab an.\n2. Folge dem Hinweis in der Administrationsoberfläche, wenn WoltLab den Hostwechsel erkennt.\n3. Prüfe Cookies, Anmeldungen und URL-Rewrites. Es werden keine Datenbankwerte automatisch geändert.\n\nHandbuch: https://manual.woltlab.com/de/customize-directory-structure/"
    elif topic == "directory":
        details = "\n1. Plane die neue Struktur und prüfe Webserver-Regeln sowie Dateirechte.\n2. Verschiebe Dateien nur nach der offiziellen Schrittfolge und prüfe danach alle App-Pfade.\n3. Direkte Dateisystem- oder Datenbankänderungen werden von diesem Assistenten nicht automatisch ausgeführt.\n\nHandbuch: https://manual.woltlab.com/de/customize-directory-structure/"
    else:
        details = "\n1. Aktiviere in WoltLab den Wartungsmodus.\n2. Spiele Dateien und Datenbank aus demselben Exportstand ein.\n3. Passe am Zielserver config.inc.php, Dateirechte, Domain, TLS und Reverse Proxy an.\n4. Prüfe Login, Uploads, E-Mail und Hintergrundaufgaben vor dem Öffnen.\n\nHandbuch: https://manual.woltlab.com/de/server-migration/"
    backup = f"\n\nVorab-Sicherung/Export: {archive}" if archive else "\n\nWoltLab ist noch nicht vollständig installiert; erst eine Installation abschließen und danach die passende Sicherung erstellen."
    return f"Geführte WoltLab-Hilfe: {topic}{backup}{details}"


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="wsc", description="WoltLab Workbench – lokale WoltLab-Projekte verwalten")
    p.add_argument("--version", action="version", version="wsc-local " + (ROOT / "VERSION").read_text().strip())
    sub = p.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="Voraussetzungen auf diesem Gerät prüfen")
    check.add_argument("--json", action="store_true")
    update = sub.add_parser("update", help="Workbench-Updates prüfen und installieren")
    update.add_argument("--check", action="store_true", help="Nur nach neuen Releases suchen")
    update.add_argument("--guide", action="store_true", help="Manuelle Anleitung anzeigen")
    update.add_argument("--yes", action="store_true", help="Angezeigtes Update ohne Rückfrage installieren")
    update.add_argument("--json", action="store_true", help="Update-Plan als JSON ausgeben")
    c = sub.add_parser("create", help="Neues WoltLab-Projekt anlegen")
    c.add_argument("name"); c.add_argument("--suite", default="6.2"); c.add_argument("--php"); c.add_argument("--database", choices=("mariadb", "mysql8"), default=None); c.add_argument("--webserver", choices=("nginx-php-fpm", "apache"), default=None); c.add_argument("--profile"); c.add_argument("--port", type=int); c.add_argument("--zip"); c.add_argument("--download-core", action="store_true"); c.add_argument("--version"); c.add_argument("--sha256"); c.add_argument("--legacy", dest="legacy_ack", action="store_true"); c.add_argument("--experimental", dest="experimental_ack", action="store_true", help="inoffizielles Entwicklungsprofil ausdrücklich bestätigen")
    x = sub.add_parser("install", help="WoltLab automatisch einrichten"); x.add_argument("name"); x.add_argument("--language", choices=("de", "en"), help="Installationssprache; Standard: Systemsprache bzw. gespeicherte Auswahl")
    l = sub.add_parser("list", help="Projekte anzeigen")
    rm = sub.add_parser("remove", help="Projekt und lokale Daten endgültig entfernen")
    rm.add_argument("name"); rm.add_argument("--yes", action="store_true", help="Bestätigung für Automatisierung; löscht Projektdateien und Datenbank")
    for cmd in ("start", "stop", "status", "logs", "doctor", "snapshot", "snapshots", "export"):
        x = sub.add_parser(cmd); x.add_argument("name")
        if cmd == "logs": x.add_argument("--service", default="web")
    x = sub.add_parser("install-zip"); x.add_argument("name"); x.add_argument("zip")
    x = sub.add_parser("download-core"); x.add_argument("name"); x.add_argument("--version"); x.add_argument("--sha256")
    x = sub.add_parser("uploads"); x.add_argument("name"); x.add_argument("--size", required=True); x.add_argument("--apply", action="store_true"); x.add_argument("--yes", action="store_true")
    r = sub.add_parser("recovery"); rs = r.add_subparsers(dest="recovery_action", required=True)
    for recovery_action in ("install", "remove"):
        rx = rs.add_parser(recovery_action); rx.add_argument("name"); rx.add_argument("--yes", action="store_true")
    x = sub.add_parser("service"); x.add_argument("name"); x.add_argument("service", choices=("mail",)); x.add_argument("action", choices=("start", "stop", "logs"))
    x = sub.add_parser("tls"); x.add_argument("name"); x.add_argument("action", choices=("enable", "disable")); x.add_argument("--yes", action="store_true")
    x = sub.add_parser("guide"); x.add_argument("name"); x.add_argument("topic", choices=("domain", "directory", "migration"))
    x = sub.add_parser("restore"); x.add_argument("name"); x.add_argument("snapshot"); x.add_argument("--yes", action="store_true")
    x = sub.add_parser("import"); x.add_argument("source"); x.add_argument("name")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "check":
            return 0 if print_report(args.json) else 1
        if detect_host()["kind"] == "windows":
            raise ValueError("Unter Windows die CLI in WSL2 ausführen. Start-wsc-local.cmd öffnet das Dashboard.")
        if args.command == "update":
            from updater import cli_update
            return cli_update(args)
        if args.command == "create":
            print(create_project(args))
        elif args.command == "install": print(install_woltlab(args.name, args.language))
        elif args.command == "list":
            if not project_names(): print("Noch keine Projekte. Beispiel: wsc create mein-forum")
            for name in project_names():
                try:
                    s = project_status(name)
                    profile_tag = " · ALPHA" if s.get("experimental") else " · LEGACY" if s["legacy"] else ""
                    print(f"{name:20} {'läuft' if s['running'] else 'gestoppt':10} WSC {s['suite']} · PHP {s['php']} · {s['url']}{profile_tag}")
                except Exception as exc: print(f"{name}: Status nicht verfügbar ({exc})")
        elif args.command == "remove": print(remove_project(args.name, args.yes))
        elif args.command == "start": print(action(args.name, "start", "up", "-d"))
        elif args.command == "stop": print(action(args.name, "stop", "stop", "--timeout", "60"))
        elif args.command == "status": print(json.dumps(project_status(args.name), ensure_ascii=False, indent=2))
        elif args.command == "logs":
            _, root, _ = read_project(args.name)
            runtime_log = root / "logs/runtime.log"
            print(runtime_log.read_text(encoding="utf-8")[-20000:] if runtime_log.is_file() else action(args.name, "logs", "logs", "--tail", "100", args.service))
        elif args.command == "doctor": print(doctor(args.name))
        elif args.command == "snapshot": print(f"Snapshot erstellt: {snapshot(args.name)}")
        elif args.command == "snapshots": print(list_snapshots(args.name))
        elif args.command == "export": print(f"Server-Export erstellt: {snapshot(args.name, export=True)}")
        elif args.command == "install-zip":
            _, root, _ = read_project(args.name); install_zip(Path(args.zip).expanduser().resolve(), root / "site"); print("Core-/Paket-ZIP sicher in das Projekt entpackt.")
        elif args.command == "download-core": print(download_core_project(args.name, args.version, args.sha256))
        elif args.command == "uploads": print(update_upload_limits(args.name, args.size, args.apply, args.yes))
        elif args.command == "recovery": print(recovery_install(args.name, args.yes) if args.recovery_action == "install" else recovery_remove(args.name, args.yes))
        elif args.command == "tls": print(local_tls(args.name, args.action == "enable", args.yes))
        elif args.command == "service": print(service_action(args.name, args.service, args.action))
        elif args.command == "guide": print(guide(args.name, args.topic))
        elif args.command == "restore": print(restore(args.name, Path(args.snapshot).expanduser().resolve(), args.yes))
        elif args.command == "import": print(import_bundle(Path(args.source), args.name))
        return 0
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired, tarfile.TarError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
