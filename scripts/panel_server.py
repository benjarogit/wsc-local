#!/usr/bin/env python3
"""Lokales Steuerungs-Panel für wsc-local (nur 127.0.0.1)."""
from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PANEL_DIR = ROOT / "panel"
ENV_FILE = ROOT / ".env"
SNAPSHOT_DIR = ROOT / "snapshots"
HOST = "127.0.0.1"
PORT = int(os.environ.get("PANEL_PORT", "9099"))


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
    tok = secrets.token_urlsafe(24)
    with ENV_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\nPANEL_TOKEN={tok}\n")
    env["PANEL_TOKEN"] = tok
    return tok


ENV = load_env()
TOKEN = ensure_token(ENV)
NAME_PREFIX = ENV.get("NAME_PREFIX", "woltlab")
PROJECT = ENV.get("COMPOSE_PROJECT_NAME", "wsc-local")
ADMIN_USER = ENV.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = ENV.get("ADMIN_PASSWORD", "")
PHPMYADMIN_PORT = ENV.get("PHPMYADMIN_PORT", "8081")
MAILHOG_UI_PORT = ENV.get("MAILHOG_UI_PORT", "8025")


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

    def _json(self, code: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str, inject_token: bool = False) -> None:
        data = path.read_bytes()
        if inject_token:
            html = data.decode("utf-8")
            meta = f'<meta name="panel-token" content="{TOKEN}">'
            html = html.replace("<head>", f"<head>\n  {meta}", 1) if "<head>" in html else meta + html
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
        if path in ("/", "/index.html"):
            self._send_file(PANEL_DIR / "index.html", "text/html; charset=utf-8", inject_token=True)
            return
        if path == "/app.js":
            self._send_file(PANEL_DIR / "app.js", "application/javascript; charset=utf-8")
            return
        if path == "/logo.png":
            self._send_file(PANEL_DIR / "logo.png", "image/png")
            return
        if not self._check_auth():
            self._json(401, {"error": "Unauthorized"})
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
                    "password": ADMIN_PASSWORD,
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
        if urllib.parse.urlparse(self.path).path != "/api/action":
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
        if code != 0:
            self._json(500, {"error": "Befehl fehlgeschlagen", "output": out, "message": "Fehler"})
            return
        self._json(200, {"ok": True, "output": out, "message": "Fertig"})


def main() -> None:
    if not ENV_FILE.is_file():
        raise SystemExit("Kein .env – zuerst ./setup.sh ausführen.")
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"wsc-local Panel: http://{HOST}:{PORT}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nPanel beendet.", flush=True)


if __name__ == "__main__":
    main()
