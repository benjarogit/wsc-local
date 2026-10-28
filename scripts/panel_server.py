#!/usr/bin/env python3
"""Lokales Steuerungs-Panel für wsc-local (nur 127.0.0.1)."""
from __future__ import annotations

import json
import hashlib
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from panel_version import panel_version

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "workbench"))
from cli import PROJECTS as WORKBENCH_PROJECTS, PROFILES, project_names, project_status, read_project, parse_env, save_setup_credentials  # noqa: E402
from host_system import system_report
from acp_login import prepare as prepare_acp_login
from host_install import installation_plan, launch_installation
PANEL_DIR = ROOT / "panel"
ENV_FILE = ROOT / ".env"
TOKEN_FILE = ROOT / "var" / "panel-token"
SNAPSHOT_DIR = ROOT / "snapshots"
HOST = "127.0.0.1"
PORT = int(os.environ.get("PANEL_PORT", "9099"))
PANEL_VERSION = panel_version()
WORKSPACE_ID = hashlib.sha256(str(ROOT.resolve()).encode()).hexdigest()[:16]


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("'").strip('"')
    return env


def ensure_token(env: dict[str, str]) -> str:
    tok = env.get("PANEL_TOKEN") or os.environ.get("PANEL_TOKEN", "")
    if tok:
        return tok
    if TOKEN_FILE.is_file():
        tok = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if tok:
            return tok
    tok = secrets.token_urlsafe(24)
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(tok + "\n", encoding="utf-8")
    TOKEN_FILE.chmod(0o600)
    env["PANEL_TOKEN"] = tok
    return tok


ENV = load_env()
TOKEN = ensure_token(ENV)
NAME_PREFIX = ENV.get("NAME_PREFIX", "woltlab")
PROJECT = ENV.get("COMPOSE_PROJECT_NAME", "wsc-local")
ADMIN_USER = ENV.get("ADMIN_USER", "admin")
PHPMYADMIN_PORT = ENV.get("PHPMYADMIN_PORT", "8081")
MAILHOG_UI_PORT = ENV.get("MAILHOG_UI_PORT", "8025")
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()
ACTIVE_COMMANDS = 0
BACKGROUND_ACTIONS = frozenset({"install", "start", "stop", "doctor", "snapshot", "export", "restore", "remove", "recovery_install", "recovery_remove", "tls_enable", "tls_disable", "mail_start", "mail_stop", "guide_domain", "guide_directory", "guide_migration", "uploads_apply"})


def workbench_command(action: str, name: str, extra_args: tuple[str, ...] = ()) -> tuple[str, ...]:
    if action not in BACKGROUND_ACTIONS:
        raise ValueError("Unbekannte Hintergrundaktion.")
    if action.startswith("recovery_"):
        return ("recovery", action.removeprefix("recovery_"), name, "--yes")
    if action.startswith("guide_"):
        return ("guide", name, action.removeprefix("guide_"))
    if action.startswith("tls_"):
        return ("tls", name, "enable" if action == "tls_enable" else "disable", "--yes")
    if action.startswith("mail_"):
        return ("service", name, "mail", "start" if action == "mail_start" else "stop")
    if action == "remove":
        return ("remove", name, "--yes")
    if action == "uploads_apply":
        return ("uploads", name, *extra_args, "--apply", "--yes")
    return (action, name, *extra_args)


def cname(svc: str) -> str:
    return f"{NAME_PREFIX}-{svc}"


def container_running(name: str) -> bool:
    r = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return name in r.stdout.splitlines()


def run_tools(*args: str, timeout: int = 600) -> tuple[int, str]:
    r = subprocess.run(
        ["bash", str(ROOT / "tools.sh"), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env={**os.environ, **ENV},
    )
    out = (r.stdout or "") + (r.stderr or "")
    out = re.sub(r"\x1b\[[0-9;]*m", "", out)
    return r.returncode, out.strip()


def run_workbench(*args: str, timeout: int = 900) -> tuple[int, str]:
    global ACTIVE_COMMANDS
    with JOBS_LOCK:
        ACTIVE_COMMANDS += 1
    try:
        r = subprocess.run(
            [sys.executable, str(ROOT / "wsc"), *args],
            cwd=str(ROOT), capture_output=True, text=True, timeout=timeout,
            check=False, env=os.environ.copy(),
        )
        out = (r.stdout or "") + (r.stderr or "")
        out = re.sub(r"\x1b\[[0-9;]*m", "", out)
        return r.returncode, out.strip()
    finally:
        with JOBS_LOCK:
            ACTIVE_COMMANDS -= 1


def run_workbench_job(job_id: str, action: str, name: str, extra_args: tuple[str, ...] = ()) -> None:
    try:
        code, output = run_workbench(*workbench_command(action, name, extra_args))
    except Exception as exc:
        code, output = 1, str(exc)
    with JOBS_LOCK:
        JOBS[job_id].update({
            "name": name,
            "state": "done" if code == 0 else "failed",
            "output": output,
            "error": "" if code == 0 else (output or "Aktion fehlgeschlagen"),
        })


def ensure_docker_ready(suite: str) -> None:
    if not shutil.which("docker"):
        raise RuntimeError("Docker wurde nicht gefunden. Installiere Docker Desktop oder Docker Engine und starte das Dashboard danach erneut.")
    try:
        check = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True, timeout=12, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Docker antwortet gerade nicht. Starte Docker Desktop/Engine, warte bis es bereit ist und versuche es erneut. Dein Projekt wurde noch nicht angelegt.") from exc
    if check.returncode:
        raise RuntimeError("Docker läuft gerade nicht. Starte Docker Desktop oder Docker Engine und klicke danach erneut auf „Projekt anlegen“. Es wurde noch nichts verändert.")
    if suite in {"6.2", "6.3"} and not shutil.which("mkcert"):
        raise RuntimeError("Für das lokale HTTPS braucht die automatische Einrichtung mkcert. Installationshilfe: https://github.com/FiloSottile/mkcert#installation. Danach kannst du das Projekt erneut anlegen.")


def workbench_instances() -> list[dict]:
    items = []
    for name in project_names():
        try:
            items.append(project_status(name))
        except Exception as exc:
            try:
                config, root, _ = read_project(name)
            except Exception:
                continue
            state_path = root / "installation-state.json"
            try:
                installation = json.loads(state_path.read_text()) if state_path.is_file() else {"state": "unverified"}
            except (OSError, ValueError):
                installation = {"state": "unverified"}
            files_available = (root / "site/global.php").is_file()
            items.append({
                "name": name, "suite": config.get("suite_version", "?"),
                "php": config.get("php_version", "?"), "database": config.get("database", "mariadb"),
                "webserver": config.get("webserver", "nginx-php-fpm"),
                "legacy": config.get("profile_status") == "legacy", "url": config.get("url", ""),
                "experimental": config.get("profile_status") == "development",
                "mail_url": "", "tls_enabled": config.get("tls_enabled", False),
                "running": False, "services": [], "site_ready": files_available and installation.get("state") == "ready",
                "files_available": files_available, "installation": installation,
                "core_available": (root / "site/install.php").exists(),
                "status_error": f"Docker-Status nicht verfügbar: {exc}",
            })
    return items


def safe_snap_name(name: str) -> str | None:
    if re.fullmatch(r"snapshot_[0-9]{8}_[0-9]{6}", name):
        return name
    return None


def _restore_named(snap: str) -> tuple[int, str]:
    env = {**os.environ, **ENV}
    script = r"""
set -euo pipefail
ROOT="$1"
SNAP="$2"
# shellcheck source=/dev/null
source "$ROOT/scripts/lib.sh"
load_env
SNAP_PATH="$ROOT/snapshots/$SNAP"
compose down || true
mkdir -p "$ROOT/woltlab"
find "$ROOT/woltlab" -mindepth 1 -exec rm -rf {} + 2>/dev/null || true
if [[ -s "$SNAP_PATH/woltlab_files.tar.gz" ]]; then
  tar -xzf "$SNAP_PATH/woltlab_files.tar.gz" -C "$ROOT/woltlab"
fi
compose up -d
for i in $(seq 1 40); do
  docker exec "$(cname mysql)" mysqladmin ping -h 127.0.0.1 -uroot -p"${MYSQL_ROOT_PASSWORD}" --silent >/dev/null 2>&1 && break
  sleep 1
done
if [[ -s "$SNAP_PATH/database.sql" ]]; then
  docker exec "$(cname mysql)" mysql -u root -p"${MYSQL_ROOT_PASSWORD}" \
    -e "DROP DATABASE IF EXISTS \`${MYSQL_DATABASE}\`; CREATE DATABASE \`${MYSQL_DATABASE}\`;" >/dev/null 2>&1
  docker exec -i "$(cname mysql)" mysql -u root -p"${MYSQL_ROOT_PASSWORD}" \
    "${MYSQL_DATABASE}" < "$SNAP_PATH/database.sql"
fi
echo "Restore OK: $SNAP"
"""
    r = subprocess.run(
        ["bash", "-c", script, "_", str(ROOT), snap],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
        env=env,
    )
    out = re.sub(r"\x1b\[[0-9;]*m", "", (r.stdout or "") + (r.stderr or "")).strip()
    return r.returncode, out


class Handler(BaseHTTPRequestHandler):
    server_version = "wsc-panel/1.0"

    def log_message(self, fmt: str, *args) -> None:
        pass

    def _check_auth(self) -> bool:
        if self.headers.get("X-Panel-Token") == TOKEN:
            return True
        cookie = self.headers.get("Cookie", "")
        return f"panel_token={TOKEN}" in cookie

    def _json(self, code: int, data: dict, download: str = "") -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Workbench-Version", PANEL_VERSION)
        if download:
            self.send_header("Content-Disposition", f'attachment; filename="{download}"')
        try:
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            # The task/result survives a tab closing or a temporary disconnect.
            self.close_connection = True

    def _send_file(self, path: Path, content_type: str, inject_token: bool = False) -> None:
        data = path.read_bytes()
        if inject_token:
            html = data.decode("utf-8")
            meta = f'<meta name="panel-token" content="{TOKEN}"><meta name="panel-version" content="{PANEL_VERSION}">'
            html = html.replace("<head>", f"<head>\n  {meta}", 1) if "<head>" in html else meta + html
            html = html.replace('href="/styles.css"', f'href="/styles.css?v={PANEL_VERSION}"').replace('src="/app.js"', f'src="/app.js?v={PANEL_VERSION}"').replace('src="/theme.js"', f'src="/theme.js?v={PANEL_VERSION}"').replace('src="/ui_helpers.js"', f'src="/ui_helpers.js?v={PANEL_VERSION}"')
            for asset in ('i18n.js', 'locale-en.js'):
                html = html.replace(f'src="/{asset}"', f'src="/{asset}?v={PANEL_VERSION}"')
            html = html.replace('id="ui-version"', f'id="ui-version" title="{PANEL_VERSION}"').replace('<!--ui-version-->', PANEL_VERSION[:6])
            data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Set-Cookie", f"panel_token={TOKEN}; Path=/; HttpOnly; SameSite=Strict")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/version":
            with JOBS_LOCK:
                active = max(ACTIVE_COMMANDS, sum(job.get("state") == "running" for job in JOBS.values()))
            self._json(200, {"version": PANEL_VERSION, "release_version": (ROOT / "VERSION").read_text().strip(), "workspace_id": WORKSPACE_ID, "active_jobs": active})
            return
        if path in ("/", "/index.html"):
            self._send_file(PANEL_DIR / "index.html", "text/html; charset=utf-8", inject_token=True)
            return
        if path in {"/app.js", "/theme.js", "/ui_helpers.js", "/i18n.js", "/locale-en.js"}:
            self._send_file(PANEL_DIR / path.lstrip("/"), "application/javascript; charset=utf-8")
            return
        if path == "/styles.css":
            self._send_file(PANEL_DIR / "styles.css", "text/css; charset=utf-8")
            return
        if path in {"/icons.svg", "/icons-license.txt"}:
            filename = "icons.svg" if path == "/icons.svg" else "LICENSE.txt"
            self._send_file(PANEL_DIR / "vendor/fontawesome" / filename, "image/svg+xml" if filename.endswith("svg") else "text/plain; charset=utf-8")
            return
        if path == "/logo.png":
            self._send_file(PANEL_DIR / "logo.png", "image/png")
            return
        if not self._check_auth():
            self._json(401, {"error": "Unauthorized"})
            return
        if path == "/api/system":
            self._json(200, {**system_report(), "installation": installation_plan()})
            return
        if path == "/api/catalog":
            php = {"5.5": ["8.1"], "6.0": ["8.3", "8.2"], "6.1": ["8.3", "8.2"], "6.2": ["8.4", "8.3", "8.2"], "6.3": ["8.5"]}
            self._json(200, {"profiles": [{**profile, "php_choices": php[profile["suite"]], "download_available": profile["suite"] in {"6.2", "6.3"}} for profile in PROFILES]})
            return
        profile_match = re.fullmatch(r"/api/instances/([a-z0-9][a-z0-9-]{0,39})/profile", path)
        if profile_match:
            try:
                cfg, _, _ = read_project(profile_match.group(1))
                shared = {key: cfg[key] for key in ("schema", "suite_version", "php_version", "database", "webserver")}
                self._json(200, shared, profile_match.group(1) + ".wsc-local.json")
            except ValueError as exc:
                self._json(404, {"error": str(exc)})
            return
        exports_match = re.fullmatch(r"/api/instances/([a-z0-9][a-z0-9-]{0,39})/exports(?:/([^/]+))?", path)
        if exports_match:
            name, filename = exports_match.groups()
            directory = WORKBENCH_PROJECTS / name / "exports"
            pattern = re.compile(re.escape(name) + r"-[0-9]{8}_[0-9]{6}\.tar\.gz")
            if not filename:
                items = [{"name": item.name, "size": item.stat().st_size} for item in sorted(directory.glob("*.tar.gz"), reverse=True) if pattern.fullmatch(item.name) and not item.is_symlink()]
                self._json(200, {"items": items})
                return
            archive = directory / filename
            if not pattern.fullmatch(filename) or not archive.is_file() or archive.is_symlink():
                self._json(404, {"error": "Export nicht gefunden."})
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/gzip")
            self.send_header("Content-Length", str(archive.stat().st_size))
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            with archive.open("rb") as source:
                shutil.copyfileobj(source, self.wfile, 1024 * 1024)
            return
        if path == "/api/jobs":
            with JOBS_LOCK:
                items = [{**{field: value for field, value in job.items() if field != "result"}, "job_id": key} for key, job in JOBS.items() if job.get("state") == "running" or time.time() - job.get("created_at", 0) < 300]
            items.sort(key=lambda job: job.get("created_at", 0), reverse=True)
            self._json(200, {"items": items})
            return
        job_match = re.fullmatch(r"/api/jobs/([a-f0-9]{32})", path)
        if job_match:
            with JOBS_LOCK:
                stored_job = JOBS.get(job_match.group(1))
                job = dict(stored_job) if stored_job else None
            if job and job.get("name") and job.get("action") == "install":
                state_file = WORKBENCH_PROJECTS / job["name"] / "installation-state.json"
                if state_file.is_file():
                    job["stage"] = json.loads(state_file.read_text()).get("stage", "")
            if job is None:
                self._json(404, {"error": "Vorgang nicht gefunden. Bitte Projektstatus und vorhandene Sicherungen prüfen."})
            else:
                self._json(200, job)
            return
        if path == "/api/instances":
            self._json(200, {"items": workbench_instances()})
            return
        recovery_match = re.fullmatch(r"/api/instances/([a-z0-9][a-z0-9-]{0,39})/recovery", path)
        if recovery_match:
            try:
                cfg, root, _ = read_project(recovery_match.group(1))
                self._json(200, {"directory": str(root / "site"), "url": cfg["url"].rstrip("/") + "/wsc-recovery.php"})
            except ValueError as exc:
                self._json(404, {"error": str(exc)})
            return
        credentials_match = re.fullmatch(r"/api/instances/([a-z0-9][a-z0-9-]{0,39})/credentials", path)
        if credentials_match:
            try:
                name = credentials_match.group(1)
                config, _, secret = read_project(name)
                values = parse_env(secret)
                self._json(200, {"url": config.get("url", ""), "admin": {"username": values.get("WSC_ADMIN_USERNAME", "admin"), "email": values.get("WSC_ADMIN_EMAIL", ""), "password": values.get("WSC_ADMIN_PASSWORD", "")}, "database": {"host": "database", "name": values.get("MYSQL_DATABASE", "woltlab"), "username": values.get("MYSQL_USER", "wsc"), "password": values.get("MYSQL_PASSWORD", "")}})
            except Exception as exc:
                self._json(404, {"error": str(exc)})
            return
        match = re.fullmatch(r"/api/instances/([a-z0-9][a-z0-9-]{0,39})/snapshots", path)
        if match:
            name = match.group(1)
            try:
                directory = WORKBENCH_PROJECTS / name / "snapshots"
                items = []
                if directory.is_dir():
                    for item in sorted(directory.iterdir(), reverse=True):
                        if item.is_dir() and re.fullmatch(r"[0-9]{8}_[0-9]{6}", item.name) and (item / "manifest.json").is_file():
                            items.append({"name": item.name})
                self._json(200, {"items": items})
            except Exception as exc:
                self._json(400, {"error": str(exc)})
            return
        if path == "/api/status":
            services = []
            for s in ("web", "mysql", "phpmyadmin", "mailhog"):
                n = cname(s)
                services.append({"name": n, "running": container_running(n)})
            self._json(
                200,
                {
                    "running": container_running(cname("web")),
                    "prefix": NAME_PREFIX,
                    "project": PROJECT,
                    "services": services,
                    "links": [
                        {"label": "WoltLab", "url": "https://wsc.local"},
                        {"label": "phpMyAdmin", "url": f"http://localhost:{PHPMYADMIN_PORT}"},
                        {"label": "MailHog", "url": f"http://localhost:{MAILHOG_UI_PORT}"},
                    ],
                    "user": ADMIN_USER,
                },
            )
            return
        if path == "/api/snapshots":
            SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
            items = []
            for p in sorted(SNAPSHOT_DIR.iterdir()):
                if not p.is_dir() or p.name.startswith("."):
                    continue
                size = subprocess.run(
                    ["du", "-sh", str(p)], capture_output=True, text=True, check=False
                ).stdout.split()
                items.append({"name": p.name, "size": size[0] if size else "?"})
            self._json(200, {"items": items})
            return
        self._json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        if not self._check_auth():
            self._json(401, {"error": "Unauthorized"})
            return
        route = urllib.parse.urlparse(self.path).path
        if route == "/api/server/stop":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length)) if 0 < length < 4096 else {}
                if body.get("workspace_id") != WORKSPACE_ID:
                    self._json(409, {"error": "Der Server gehört zu einer anderen Workbench."})
                    return
                with JOBS_LOCK:
                    active = ACTIVE_COMMANDS > 0 or any(job.get("state") == "running" for job in JOBS.values())
                if active:
                    self._json(409, {"error": "Eine Einrichtung läuft noch."})
                    return
                self._json(200, {"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            except (ValueError, TypeError):
                self._json(400, {"error": "Ungültige Serveranfrage."})
            return
        if (route == "/api/workbench" or route.endswith("/archive") or route.endswith("/acp-login") or route == "/api/system/install") and self.headers.get("X-Workbench-Version") != PANEL_VERSION:
            self._json(409, {"version_mismatch": True, "version": PANEL_VERSION, "error": "Die Dashboard-Oberfläche ist veraltet. Lade die Seite neu, bevor du weiterarbeitest. Dein Projekt wurde durch diesen Klick nicht verändert."})
            return
        acp_match = re.fullmatch(r"/api/instances/([a-z0-9][a-z0-9-]{0,39})/acp-login", route)
        if acp_match or route == "/api/system/install":
            name = acp_match.group(1) if acp_match else "system"
            action = "acp_login" if acp_match else "host_install"
            agent = self.headers.get("User-Agent", "")
            with JOBS_LOCK:
                if any(job.get("state") == "running" and (job.get("name") == name or action == "host_install") for job in JOBS.values()):
                    self._json(409, {"error": "Ein Vorgang läuft noch. Bitte warte bis zum Abschluss."})
                    return
                job_id = uuid.uuid4().hex
                JOBS[job_id] = {"name": name, "action": action, "created_at": time.time(), "stage": "ACP-Anmeldung wird vorbereitet …" if acp_match else "Bitte schließe die Einrichtung im Systemterminal ab …", "state": "running", "output": "", "error": ""}
            def execute_special():
                try:
                    result = prepare_acp_login(name, agent) if action == "acp_login" else launch_installation(ROOT)
                    with JOBS_LOCK:
                        JOBS[job_id].update(state="done", result=result, output="Vorgang abgeschlossen.")
                except Exception as exc:
                    with JOBS_LOCK:
                        JOBS[job_id].update(state="failed", error=str(exc))
            threading.Thread(target=execute_special, daemon=True).start()
            self._json(202, {"job_id": job_id, "name": name, "action": action})
            return
        archive_match = re.fullmatch(r"/api/instances/([a-z0-9][a-z0-9-]{0,39})/archive", route)
        if archive_match:
            temporary_path = None
            try:
                name = archive_match.group(1)
                _, project_root, _ = read_project(name)
                with JOBS_LOCK:
                    active = any(job.get("name") == name and job.get("state") == "running" for job in JOBS.values())
                if active or (project_root / "site/global.php").exists():
                    self._json(409, {"error": "Das Archiv kann nur vor der WoltLab-Einrichtung eingespielt werden."})
                    return
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 256 * 1024**2:
                    self._json(413, {"error": "Bitte ein Installations-ZIP mit maximal 256 MiB auswählen."})
                    return
                with tempfile.NamedTemporaryFile(prefix="wsc-panel-", suffix=".zip", delete=False) as temporary:
                    temporary_path = Path(temporary.name)
                    remaining = length
                    while remaining:
                        chunk = self.rfile.read(min(1024**2, remaining))
                        if not chunk:
                            raise ValueError("Die Archivübertragung wurde unterbrochen. Bitte erneut auswählen.")
                        temporary.write(chunk)
                        remaining -= len(chunk)
                code, output = run_workbench("install-zip", name, str(temporary_path))
                self._json(200 if code == 0 else 400, {"ok": code == 0, "output": output, "error": output if code else "", "message": "Installationsarchiv eingespielt."})
            except Exception as exc:
                self._json(400, {"error": str(exc)})
            finally:
                if temporary_path:
                    temporary_path.unlink(missing_ok=True)
            return
        if route not in ("/api/action", "/api/workbench"):
            self._json(404, {"error": "Not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._json(400, {"error": "Invalid JSON"})
            return
        action = body.get("action", "")
        name = body.get("name", "")
        try:
            if route == "/api/workbench":
                if action == "create":
                    project = body.get("project", "")
                    suite = body.get("suite", "6.2")
                    source = body.get("source", "download")
                    if source not in {"download", "zip"} or (suite not in {"6.2", "6.3"} and source != "zip"):
                        self._json(400, {"error": "Für dieses Profil bitte ein eigenes WoltLab-Installations-ZIP auswählen."})
                        return
                    webserver = body.get("webserver", "nginx-php-fpm")
                    database = body.get("database", "mariadb")
                    php = body.get("php", "")
                    choices = {"5.5": {"8.1"}, "6.0": {"8.2", "8.3"}, "6.1": {"8.2", "8.3"}, "6.2": {"8.2", "8.3", "8.4"}, "6.3": {"8.5"}}
                    if database not in {"mariadb", "mysql8"} or (php and php not in choices.get(suite, set())):
                        self._json(400, {"error": "PHP- oder Datenbankauswahl passt nicht zum WoltLab-Profil."})
                        return
                    if not isinstance(project, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}", project):
                        self._json(400, {"error": "Projektname: Kleinbuchstaben, Zahlen und Bindestriche; muss mit Buchstabe/Zahl beginnen."})
                        return
                    if suite not in {"5.5", "6.0", "6.1", "6.2", "6.3"}:
                        self._json(400, {"error": "Unbekanntes WSC-Profil."})
                        return
                    if suite in {"5.5", "6.0", "6.3"} and body.get("experimental_ack") is not True:
                        self._json(400, {"error": "Bitte die Verwendung des Legacy- bzw. Entwicklungsprofils im Formular bestätigen."})
                        return
                    if webserver not in {"nginx-php-fpm", "apache"}:
                        self._json(400, {"error": "Unbekanntes Webserverprofil."})
                        return
                    admin_username = body.get("admin_username", "admin")
                    admin_email = body.get("admin_email", "admin@example.test")
                    admin_password = body.get("admin_password", "")
                    if not isinstance(admin_username, str) or not re.fullmatch(r"[\w .-]{1,40}", admin_username, re.UNICODE):
                        self._json(400, {"error": "Der Adminname darf 1–40 Buchstaben, Zahlen, Leerzeichen, Punkte oder Bindestriche enthalten."})
                        return
                    if not isinstance(admin_email, str) or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", admin_email):
                        self._json(400, {"error": "Bitte eine gültige Admin-E-Mail-Adresse eingeben."})
                        return
                    if not isinstance(admin_password, str) or (admin_password and (len(admin_password) < 12 or any(char in admin_password for char in "\r\n\0"))):
                        self._json(400, {"error": "Ein eigenes Adminpasswort muss mindestens 12 Zeichen lang sein."})
                        return
                    try:
                        ensure_docker_ready(suite)
                    except RuntimeError as exc:
                        self._json(409, {"error": str(exc)})
                        return
                    args = ["create", project, "--suite", suite, "--webserver", webserver]
                    args.extend(["--database", database])
                    if php: args.extend(["--php", php])
                    if suite in {"5.5", "6.0"}: args.append("--legacy")
                    if suite == "6.2" and source == "download": args.append("--download-core")
                    if suite == "6.3":
                        args.append("--experimental")
                        if source == "download": args.append("--download-core")
                    code, out = run_workbench(*args)
                    if code == 0:
                        save_setup_credentials(project, admin_username, admin_email, admin_password)
                        out += "\nAdmin-Zugangsdaten wurden sicher für die automatische Installation gespeichert. Du kannst sie in der Projektkarte ansehen."
                else:
                    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}", name):
                        self._json(400, {"error": "Ungültiger Projektname"})
                        return
                    with JOBS_LOCK:
                        is_installing = any(job.get("name") == name and job.get("state") == "running" for job in JOBS.values())
                    if is_installing and action not in BACKGROUND_ACTIONS | {"logs"}:
                        self._json(409, {"error": "Für dieses Projekt läuft bereits ein Vorgang. Warte auf den Abschluss, bevor du Einstellungen oder Daten änderst."})
                        return
                    if action == "save_credentials":
                        _, project_root, _ = read_project(name)
                        if (project_root / "site/global.php").exists():
                            self._json(409, {"error": "Nach der Installation änderst du Login-Daten direkt in WoltLab."})
                            return
                        save_setup_credentials(name, body.get("username", ""), body.get("email", ""), body.get("password", ""))
                        self._json(200, {"ok": True, "message": "Login-Daten gespeichert."})
                        return
                    allowed = {"install", "start", "stop", "doctor", "snapshot", "export", "logs", "restore", "remove", "recovery_install", "recovery_remove", "uploads_preview", "uploads_apply", "tls_enable", "tls_disable", "mail_start", "mail_stop", "guide_domain", "guide_directory", "guide_migration"}
                    if action not in allowed:
                        self._json(400, {"error": "Unbekannte Workbench-Aktion"})
                        return
                    if action in BACKGROUND_ACTIONS:
                        read_project(name)
                        extra_args = ()
                        if action == "restore":
                            snap = body.get("snapshot", "")
                            if not isinstance(snap, str) or not re.fullmatch(r"[0-9]{8}_[0-9]{6}", snap):
                                self._json(400, {"error": "Ungültige Sicherungsauswahl"})
                                return
                            snapshot_path = WORKBENCH_PROJECTS / name / "snapshots" / snap
                            if not (snapshot_path / "manifest.json").is_file():
                                self._json(404, {"error": "Sicherung nicht gefunden"})
                                return
                            extra_args = (str(snapshot_path), "--yes")
                        if action == "uploads_apply":
                            size = body.get("size", "")
                            if not isinstance(size, str) or not re.fullmatch(r"[1-9][0-9]{0,5}[MG]", size):
                                self._json(400, {"error": "Uploadgröße ist ungültig. Beispiel: 256M oder 1G."})
                                return
                            extra_args = ("--size", size)
                        messages = {"install": "WoltLab wird automatisch eingerichtet …", "snapshot": "Dateien und Datenbank werden gesichert …", "export": "Server-Export wird erstellt …", "restore": "Sicherung wird wiederhergestellt …", "recovery_install": "Sicherung und offizielles Recovery Tool werden vorbereitet …", "recovery_remove": "Recovery Tool wird entfernt …", "guide_domain": "Sicherung und Domain-Anleitung werden vorbereitet …", "guide_directory": "Sicherung und Verzeichnis-Anleitung werden vorbereitet …", "guide_migration": "Umzugspaket und Anleitung werden vorbereitet …"}
                        message = messages.get(action, "Projektvorgang wird ausgeführt …")
                        job_id = uuid.uuid4().hex
                        with JOBS_LOCK:
                            active = next((key for key, job in JOBS.items() if job.get("name") == name and job.get("state") == "running"), None)
                            if not active:
                                JOBS[job_id] = {"name": name, "action": action, "created_at": time.time(), "stage": message, "state": "running", "output": "", "error": ""}
                            active_action = JOBS[active].get("action") if active else None
                        if active:
                            if active_action != action:
                                self._json(409, {"error": "Für dieses Projekt läuft bereits ein anderer Vorgang. Warte auf dessen Abschluss."})
                            else:
                                self._json(202, {"job_id": active, "name": name, "action": action})
                            return
                        threading.Thread(target=run_workbench_job, args=(job_id, action, name, extra_args), daemon=True).start()
                        self._json(202, {"job_id": job_id, "name": name, "action": action, "message": message})
                        return
                    elif action == "uploads_preview":
                        size = body.get("size", "")
                        if not isinstance(size, str) or len(size) > 12:
                            self._json(400, {"error": "Uploadgröße ist ungültig."})
                            return
                        code, out = run_workbench("uploads", name, "--size", size)
                    elif action == "logs":
                        service = body.get("service", "web")
                        if service not in {"web", "php", "database", "mail"}:
                            self._json(400, {"error": "Unbekannter Dienst."})
                            return
                        code, out = run_workbench("logs", name, "--service", service)
                    else:
                        code, out = run_workbench(action, name)
                if code != 0:
                    self._json(500, {"error": out or "Aktion fehlgeschlagen"})
                    return
                self._json(200, {"ok": True, "output": out, "message": "Fertig"})
                return
            if action == "start":
                code, out = run_tools("start")
            elif action == "stop":
                code, out = run_tools("stop")
            elif action == "doctor":
                code, out = run_tools("doctor")
            elif action == "repair":
                code, out = run_tools("repair")
            elif action == "rebuild":
                code, out = run_tools("rebuild")
            elif action == "snapshot_create":
                code, out = run_tools("create")
            elif action == "snapshot_restore":
                snap = safe_snap_name(name)
                if not snap:
                    self._json(400, {"error": "Ungültiger Snapshot-Name"})
                    return
                if not (SNAPSHOT_DIR / snap).is_dir():
                    self._json(404, {"error": "Snapshot nicht gefunden"})
                    return
                code, out = _restore_named(snap)
            elif action == "snapshot_delete":
                snap = safe_snap_name(name)
                if not snap:
                    self._json(400, {"error": "Ungültiger Snapshot-Name"})
                    return
                path = SNAPSHOT_DIR / snap
                if path.is_dir():
                    subprocess.run(["rm", "-rf", str(path)], check=False)
                code, out = 0, f"Gelöscht: {snap}"
            else:
                self._json(400, {"error": f"Unbekannte Aktion: {action}"})
                return
        except subprocess.TimeoutExpired:
            self._json(504, {"error": "Zeitüberschreitung"})
            return
        except (ValueError, TypeError) as exc:
            self._json(400, {"error": str(exc)})
            return
        except Exception as exc:
            self._json(500, {"error": "Der Vorgang konnte nicht abgeschlossen werden: " + str(exc)})
            return
        if code != 0:
            self._json(500, {"error": "Befehl fehlgeschlagen", "output": out, "message": "Fehler"})
            return
        self._json(200, {"ok": True, "output": out, "message": "Fertig"})


def main() -> None:
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    (ROOT / "var/panel.pid").write_text(str(os.getpid()) + "\n")
    print(f"wsc-local Panel: http://{HOST}:{PORT}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nPanel beendet.", flush=True)
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
