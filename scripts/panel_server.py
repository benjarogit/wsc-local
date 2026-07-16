#!/usr/bin/env python3
"""Lokales Steuerungs-Panel für wsc-local (nur 127.0.0.1)."""
from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import threading
import traceback
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
PANEL_DIR = ROOT / "panel"
ENV_FILE = ROOT / ".env"
SNAPSHOT_DIR = ROOT / "snapshots"
HOST = "127.0.0.1"
PORT = int(os.environ.get("PANEL_PORT", "9099"))

SVC_LABELS = {
    "web": "Website",
    "mysql": "Datenbank",
    "phpmyadmin": "phpMyAdmin",
    "mailhog": "Test-E-Mail",
}

# Lange Aktionen laufen im Hintergrund – Browser bekommt sofort job_id (kein NetworkError)
ACTION_META: dict[str, dict[str, Any]] = {
    "start": {"label": "Starten", "async": True, "disrupts": True},
    "stop": {"label": "Stoppen", "async": True, "disrupts": True},
    "doctor": {"label": "Prüfen", "async": True, "disrupts": False},
    "repair": {
        "label": "Verbindung reparieren",
        "async": True,
        "disrupts": True,
        "hint": "Startet die Container kurz neu (Website offline für ~30 Sek.).",
    },
    "rebuild": {
        "label": "Neu bauen",
        "async": True,
        "disrupts": True,
        "hint": "Baut die Website neu – kann mehrere Minuten dauern.",
    },
    "logs": {"label": "Protokoll laden", "async": True, "disrupts": False},
    "snapshot_create": {"label": "Sicherung erstellen", "async": True, "disrupts": False},
    "snapshot_restore": {"label": "Wiederherstellen", "async": True, "disrupts": True},
    "snapshot_delete": {"label": "Sicherung löschen", "async": False, "disrupts": False},
    "reset": {"label": "Zurücksetzen", "async": False, "disrupts": True},
}

_JOBS: dict[str, dict[str, Any]] = {}
_JOBS_LOCK = threading.Lock()
_ACTIVE_DISRUPT: str | None = None  # action label while stack may look „down“


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
WSC_VERSION = ENV.get("WSC_VERSION", "")


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


def docker_ok() -> bool:
    r = subprocess.run(
        ["docker", "info"],
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )
    return r.returncode == 0


def site_reachable() -> bool:
    r = subprocess.run(
        [
            "curl",
            "-kfsS",
            "--connect-timeout",
            "2",
            "--max-time",
            "4",
            "-o",
            "/dev/null",
            "-w",
            "%{http_code}",
            "https://wsc.local/",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    code = (r.stdout or "").strip()
    return code in {"200", "301", "302", "303", "401", "403"}


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


def snap_label(name: str) -> str:
    m = re.fullmatch(r"snapshot_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})", name)
    if not m:
        return name
    y, mo, d, h, mi, s = m.groups()
    try:
        dt = datetime(int(y), int(mo), int(d), int(h), int(mi), int(s))
    except ValueError:
        return name
    return dt.strftime("%d.%m.%Y, %H:%M")


def relative_de(dt: datetime) -> str:
    now = datetime.now()
    delta = now - dt
    sec = int(delta.total_seconds())
    if sec < 90:
        return "gerade eben"
    if sec < 3600:
        return f"vor {max(1, sec // 60)} Min."
    if sec < 86400:
        return f"vor {max(1, sec // 3600)} Std."
    days = sec // 86400
    if days == 1:
        return "gestern"
    if days < 14:
        return f"vor {days} Tagen"
    return dt.strftime("%d.%m.%Y")


def fetch_logs(tail: int = 60) -> tuple[int, str]:
    """Nur lesend – stoppt keine Container. Primär Website-Logs."""
    chunks: list[str] = []
    stopped: list[str] = []
    for svc in ("web", "mysql", "phpmyadmin", "mailhog"):
        n = cname(svc)
        label = SVC_LABELS.get(svc, svc)
        if not container_running(n):
            stopped.append(label)
            chunks.append(f"=== {label} – gestoppt (keine Logs) ===")
            continue
        r = subprocess.run(
            ["docker", "logs", "--tail", str(tail), n],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        body = ((r.stdout or "") + (r.stderr or "")).strip()
        # Docker schreibt Logs oft nach stderr
        chunks.append(f"=== {label} ===\n{body or '(leer)'}")
    if stopped:
        chunks.append(
            "Hinweis: Gestoppt: "
            + ", ".join(stopped)
            + ". Mit „Starten“ alle Dienste wieder anschalten."
        )
    return 0, "\n\n".join(chunks)


def _job_get(job_id: str) -> dict[str, Any] | None:
    with _JOBS_LOCK:
        j = _JOBS.get(job_id)
        return dict(j) if j else None


def _active_busy() -> dict[str, Any] | None:
    global _ACTIVE_DISRUPT
    with _JOBS_LOCK:
        for j in _JOBS.values():
            if j.get("status") == "running":
                return {
                    "job_id": j["id"],
                    "action": j["action"],
                    "label": j["label"],
                    "hint": j.get("hint") or f"{j['label']} läuft…",
                    "disrupts": bool(j.get("disrupts")),
                }
    return None


def start_job(
    action: str,
    label: str,
    fn: Callable[[], tuple[int, str]],
    *,
    disrupts: bool = False,
    hint: str = "",
) -> str:
    job_id = secrets.token_hex(6)
    job: dict[str, Any] = {
        "id": job_id,
        "action": action,
        "label": label,
        "hint": hint,
        "disrupts": disrupts,
        "status": "running",
        "output": "",
        "message": f"{label} gestartet…",
        "error": None,
        "started": datetime.now().isoformat(timespec="seconds"),
        "finished": None,
    }
    with _JOBS_LOCK:
        _JOBS[job_id] = job
        # alte Jobs begrenzen
        if len(_JOBS) > 40:
            done = [k for k, v in _JOBS.items() if v.get("status") != "running"]
            for k in done[:20]:
                _JOBS.pop(k, None)

    def runner() -> None:
        global _ACTIVE_DISRUPT
        if disrupts:
            _ACTIVE_DISRUPT = label
        try:
            code, out = fn()
            with _JOBS_LOCK:
                j = _JOBS.get(job_id)
                if not j:
                    return
                j["finished"] = datetime.now().isoformat(timespec="seconds")
                j["output"] = out or ""
                if code == 0:
                    j["status"] = "ok"
                    j["message"] = f"{label}: fertig"
                    j["error"] = None
                else:
                    j["status"] = "error"
                    j["message"] = f"{label}: fehlgeschlagen"
                    j["error"] = (out or "Unbekannter Fehler")[-800:]
        except subprocess.TimeoutExpired:
            with _JOBS_LOCK:
                j = _JOBS.get(job_id)
                if j:
                    j["status"] = "error"
                    j["message"] = f"{label}: Zeitüberschreitung"
                    j["error"] = "Der Vorgang dauerte zu lange. Status prüfen oder erneut versuchen."
                    j["finished"] = datetime.now().isoformat(timespec="seconds")
        except Exception as exc:  # noqa: BLE001 – an UI liefern
            with _JOBS_LOCK:
                j = _JOBS.get(job_id)
                if j:
                    j["status"] = "error"
                    j["message"] = f"{label}: Fehler"
                    j["error"] = f"{exc}\n{traceback.format_exc()[-600:]}"
                    j["output"] = j.get("output") or ""
                    j["finished"] = datetime.now().isoformat(timespec="seconds")
        finally:
            if disrupts:
                _ACTIVE_DISRUPT = None

    threading.Thread(target=runner, name=f"job-{action}", daemon=True).start()
    return job_id


def list_snapshots() -> list[dict]:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for p in sorted(SNAPSHOT_DIR.iterdir(), reverse=True):
        if not p.is_dir() or p.name.startswith("."):
            continue
        size = subprocess.run(
            ["du", "-sh", str(p)], capture_output=True, text=True, check=False
        ).stdout.split()
        label = snap_label(p.name)
        rel = ""
        m = re.fullmatch(r"snapshot_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})", p.name)
        if m:
            try:
                dt = datetime(*map(int, m.groups()))
                rel = relative_de(dt)
            except ValueError:
                rel = ""
        items.append(
            {
                "name": p.name,
                "label": label,
                "relative": rel,
                "size": size[0] if size else "?",
            }
        )
    return items


def build_health(services: list[dict]) -> dict:
    details: list[str] = []
    level = "ok"

    if not docker_ok():
        return {
            "level": "error",
            "title": "Docker läuft nicht",
            "hint": "Docker Desktop / Dienst starten, dann Seite neu laden.",
            "details": ["Docker ist nicht erreichbar."],
        }

    if not ENV_FILE.is_file():
        return {
            "level": "error",
            "title": "Noch nicht eingerichtet",
            "hint": "Im Terminal: ./setup.sh",
            "details": [".env fehlt"],
        }

    if not (ROOT / "certs" / "fullchain.pem").is_file():
        details.append("HTTPS-Zertifikat fehlt")
        level = "warn"

    if not (ROOT / "woltlab" / "global.php").is_file():
        details.append("WoltLab-Dateien unvollständig")
        level = "warn"

    down = [s["label"] for s in services if not s["running"]]
    up_n = sum(1 for s in services if s["running"])
    running = up_n == len(services) and up_n > 0

    if not running:
        if up_n == 0:
            return {
                "level": "warn",
                "title": "Gestoppt",
                "hint": "Mit „Starten“ die Umgebung anschalten.",
                "details": details + (["Alle Dienste sind aus."] if not details else details),
            }
        level = "warn"
        details.append("Nicht alle Dienste laufen: " + ", ".join(down))

    if running and not site_reachable():
        level = "warn"
        details.append("Website https://wsc.local antwortet noch nicht")

    if level == "ok":
        return {
            "level": "ok",
            "title": "Alles bereit",
            "hint": "Website öffnen oder Sicherung anlegen.",
            "details": details,
        }
    if level == "warn":
        return {
            "level": "warn",
            "title": "Hinweis",
            "hint": "„Prüfen“ oder „Netzwerk reparieren“ helfen oft.",
            "details": details or ["Es gibt etwas zu prüfen."],
        }
    return {
        "level": "error",
        "title": "Problem",
        "hint": "Details in der Ausgabe nach „Prüfen“.",
        "details": details or ["Unbekannter Fehler"],
    }


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
echo "Wiederhergestellt: $SNAP"
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
    server_version = "wsc-panel/1.1"

    def log_message(self, fmt: str, *args) -> None:
        pass

    def _check_auth(self) -> bool:
        if self.headers.get("X-Panel-Token") == TOKEN:
            return True
        cookie = self.headers.get("Cookie", "")
        return f"panel_token={TOKEN}" in cookie

    def _json(self, code: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_file(
        self,
        path: Path,
        content_type: str,
        inject_token: bool = False,
        set_auth_cookie: bool = False,
    ) -> None:
        data = path.read_bytes()
        if inject_token:
            html = data.decode("utf-8")
            meta = f'<meta name="panel-token" content="{TOKEN}">'
            html = html.replace("<head>", f"<head>\n  {meta}", 1) if "<head>" in html else meta + html
            data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        if set_auth_cookie:
            self.send_header("Set-Cookie", f"panel_token={TOKEN}; Path=/; HttpOnly; SameSite=Strict")
        if content_type.startswith("image/") or "svg" in content_type:
            self.send_header("Cache-Control", "public, max-age=3600")
        else:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send_file(
                PANEL_DIR / "index.html",
                "text/html; charset=utf-8",
                inject_token=True,
                set_auth_cookie=True,
            )
            return
        if path == "/app.js" or path.startswith("/app.js"):
            self._send_file(PANEL_DIR / "app.js", "application/javascript; charset=utf-8")
            return
        if path == "/i18n.js" or path.startswith("/i18n.js"):
            self._send_file(PANEL_DIR / "i18n.js", "application/javascript; charset=utf-8")
            return
        if path == "/logo.png" or path.startswith("/logo.png"):
            logo = PANEL_DIR / "logo.png"
            if not logo.is_file():
                self._json(404, {"error": "Logo fehlt"})
                return
            self._send_file(logo, "image/png")
            return
        if path == "/logo.svg" or path.startswith("/logo.svg"):
            logo = PANEL_DIR / "logo.svg"
            if not logo.is_file():
                self._json(404, {"error": "Logo fehlt"})
                return
            self._send_file(logo, "image/svg+xml; charset=utf-8")
            return
        if not self._check_auth():
            self._json(401, {"error": "Unauthorized"})
            return
        if path == "/api/status":
            services = []
            for s in ("web", "mysql", "phpmyadmin", "mailhog"):
                n = cname(s)
                services.append(
                    {
                        "id": s,
                        "name": n,
                        "label": SVC_LABELS.get(s, s),
                        "running": container_running(n),
                    }
                )
            health = build_health(services)
            snaps = list_snapshots()
            up_n = sum(1 for x in services if x["running"])
            docker = docker_ok()
            https_ok = (ROOT / "certs" / "fullchain.pem").is_file()
            site_ok = bool(container_running(cname("web")) and site_reachable())
            busy = _active_busy()
            # Während Repair/Rebuild: Status nicht als „kaputt“ verkaufen
            if busy and busy.get("disrupts"):
                health = {
                    "level": "warn",
                    "title": f"Arbeitet: {busy['label']}",
                    "hint": busy.get("hint")
                    or "Bitte warten – Dienste können kurz offline sein.",
                    "details": health.get("details") or [],
                }
            self._json(
                200,
                {
                    "running": container_running(cname("web")),
                    "prefix": NAME_PREFIX,
                    "project": PROJECT,
                    "version": WSC_VERSION,
                    "health": health,
                    "busy": busy,
                    "services": services,
                    "flags": {
                        "docker": docker,
                        "https": https_ok,
                        "site": site_ok,
                        "services_up": up_n,
                        "services_total": len(services),
                    },
                    "last_snapshot": snaps[0] if snaps else None,
                    "snapshot_count": len(snaps),
                    "links": [
                        {"label": "WoltLab öffnen", "url": "https://wsc.local", "primary": True},
                        {"label": "phpMyAdmin", "url": f"http://localhost:{PHPMYADMIN_PORT}"},
                        {"label": "MailHog", "url": f"http://localhost:{MAILHOG_UI_PORT}"},
                    ],
                    "user": ADMIN_USER,
                    "password": ADMIN_PASSWORD,
                    "github": "https://github.com/benjarogit/wsc-local",
                },
            )
            return
        if path == "/api/snapshots":
            self._json(200, {"items": list_snapshots()})
            return
        if path == "/api/job":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            job_id = (qs.get("id") or [""])[0]
            job = _job_get(job_id) if job_id else None
            if not job:
                self._json(404, {"error": "Auftrag nicht gefunden"})
                return
            self._json(200, {"ok": True, "job": job})
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
        meta = ACTION_META.get(action)
        if action == "reset":
            if body.get("confirm") != "RESET":
                self._json(400, {"error": "Bitte RESET tippen zur Bestätigung"})
                return
            args = ["--yes"]
            if body.get("purge"):
                args.append("--purge-all")
            subprocess.Popen(
                ["bash", str(ROOT / "reset.sh"), *args],
                cwd=str(ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self._json(
                200,
                {
                    "ok": True,
                    "output": "Zurücksetzen gestartet.\n"
                    "Das Panel schließt sich gleich.\n"
                    "Danach im Terminal: ./setup.sh",
                    "message": "Zurücksetzen gestartet",
                },
            )
            return

        if not meta:
            self._json(400, {"error": f"Unbekannte Aktion: {action}"})
            return

        # Bereits ein disruptiver Job aktiv?
        busy = _active_busy()
        if busy and busy.get("disrupts") and meta.get("disrupts"):
            self._json(
                409,
                {
                    "error": f"Bitte warten – „{busy['label']}“ läuft noch.",
                    "busy": busy,
                },
            )
            return

        def make_fn() -> Callable[[], tuple[int, str]]:
            if action == "start":
                return lambda: run_tools("start")
            if action == "stop":
                return lambda: run_tools("stop")
            if action == "doctor":
                return lambda: run_tools("doctor")
            if action == "repair":
                return lambda: run_tools("repair", timeout=300)
            if action == "rebuild":
                return lambda: run_tools("rebuild", timeout=900)
            if action == "logs":
                return fetch_logs
            if action == "snapshot_create":
                return lambda: run_tools("create", timeout=600)
            if action == "snapshot_restore":
                snap = safe_snap_name(name)
                if not snap or not (SNAPSHOT_DIR / snap).is_dir():
                    return lambda: (1, "Sicherung nicht gefunden oder ungültig")
                return lambda: _restore_named(snap)
            if action == "snapshot_delete":
                snap = safe_snap_name(name)

                def _del() -> tuple[int, str]:
                    if not snap:
                        return 1, "Ungültiger Sicherungsname"
                    path = SNAPSHOT_DIR / snap
                    if path.is_dir():
                        subprocess.run(["rm", "-rf", str(path)], check=False)
                    return 0, f"Sicherung gelöscht: {snap_label(snap)}"

                return _del
            return lambda: (1, "Interner Fehler")

        fn = make_fn()
        if action == "snapshot_restore":
            snap = safe_snap_name(name)
            if not snap:
                self._json(400, {"error": "Ungültiger Sicherungsname"})
                return
            if not (SNAPSHOT_DIR / snap).is_dir():
                self._json(404, {"error": "Sicherung nicht gefunden"})
                return

        if meta.get("async"):
            job_id = start_job(
                action,
                str(meta["label"]),
                fn,
                disrupts=bool(meta.get("disrupts")),
                hint=str(meta.get("hint") or ""),
            )
            self._json(
                200,
                {
                    "ok": True,
                    "async": True,
                    "job_id": job_id,
                    "message": f"{meta['label']} gestartet…",
                    "output": meta.get("hint")
                    or "Läuft im Hintergrund – Status aktualisiert sich automatisch.",
                },
            )
            return

        # Kurze Sync-Aktionen (z. B. Sicherung löschen)
        try:
            code, out = fn()
        except subprocess.TimeoutExpired:
            self._json(504, {"error": "Zeitüberschreitung – bitte später erneut versuchen"})
            return
        if code != 0:
            self._json(500, {"error": out or "Befehl fehlgeschlagen", "output": out, "message": "Fehler"})
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
