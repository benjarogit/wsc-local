#!/usr/bin/env python3
"""One dashboard entry point for Linux, macOS and Windows through WSL2."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from panel_version import panel_version
from host_system import detect_host, open_dashboard, print_report, configure_trust, trust_ready
import shutil
import updater


def workspace_id() -> str:
    return hashlib.sha256(str(ROOT.resolve()).encode()).hexdigest()[:16]


def request(url: str, payload: dict | None = None, token: str = "") -> dict | None:
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode() if payload is not None else None, headers={"Content-Type": "application/json", "X-Panel-Token": token})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=3) as response:
            return json.load(response)
    except (OSError, ValueError, urllib.error.URLError):
        return None


def panel_token() -> str:
    env_file = ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            if line.startswith("PANEL_TOKEN="):
                return line.split("=", 1)[1].strip().strip("\"'")
    if os.environ.get("PANEL_TOKEN"):
        return os.environ["PANEL_TOKEN"]
    path = ROOT / "var/panel-token"
    return path.read_text().strip() if path.is_file() else ""


def stop_older_server(base: str, status: dict) -> None:
    if status.get("active_jobs", 0):
        raise RuntimeError("Eine Einrichtung läuft noch. Warte auf ihren Abschluss und starte die Workbench danach erneut.")
    if status.get("workspace_id"):
        if status["workspace_id"] != workspace_id():
            raise RuntimeError("Dieser Port gehört zu einer anderen Workbench. Mit --port einen anderen Dashboard-Port wählen.")
        stopped = request(base + "/api/server/stop", {"workspace_id": workspace_id()}, panel_token())
        if not stopped or not stopped.get("ok"):
            raise RuntimeError("Der laufende Dashboard-Server konnte nicht sicher beendet werden.")
    else:
        # Compatibility with older launches; never kill an unverified process.
        pid_file = ROOT / "var/panel.pid"
        pid = int(pid_file.read_text().strip())
        proc = Path(f"/proc/{pid}")
        target = str(ROOT / "scripts/panel_server.py")
        if (proc / "cmdline").is_file():
            args = (proc / "cmdline").read_bytes().decode().split("\0")
            owned = target in args or ((proc / "cwd").resolve() == ROOT and "scripts/panel_server.py" in args)
        else:
            command = subprocess.check_output(["ps", "-p", str(pid), "-o", "command="], text=True).strip()
            owned = command.endswith(target) and "python" in shlex.split(command)[0]
        if not owned:
            raise RuntimeError("Der laufende Prozess gehört nicht eindeutig zu diesem Repository. Mit --port einen anderen Dashboard-Port wählen.")
        processes = subprocess.check_output(["ps", "-eo", "ppid=,args="], text=True)
        if any(line.split(None, 1)[0] == str(pid) and any(str(ROOT / name) in line for name in ("wsc", "tools.sh")) for line in processes.splitlines() if line.strip()):
            raise RuntimeError("Ein Dashboard-Vorgang läuft noch. Nach dessen Abschluss erneut starten.")
        os.kill(pid, signal.SIGTERM)
    for _ in range(40):
        try:
            with socket.create_connection(("127.0.0.1", int(base.rsplit(":", 1)[1])), timeout=.3):
                pass
        except OSError:
            return
        time.sleep(.1)
    raise RuntimeError("Der alte Server antwortet noch. Nach dem Abschluss des laufenden Vorgangs erneut starten.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="wsc-local Workbench starten: Linux, macOS, Windows über WSL2")
    parser.add_argument("--no-open", action="store_true", help="Browser nicht automatisch öffnen")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PANEL_PORT", "9099")))
    parser.add_argument("--check", action="store_true", help="Voraussetzungen prüfen und beenden")
    parser.add_argument("--stop", action="store_true", help="Eigenes Dashboard am gewählten Port beenden")
    parser.add_argument("--setup", action="store_true", help="Voraussetzungen prüfen und das Dashboard öffnen")
    args = parser.parse_args(argv)
    if detect_host()["kind"] == "windows":
        print("Unter Windows Start-wsc-local.cmd verwenden. Die Workbench läuft in WSL2.", file=sys.stderr)
        return 2
    if not 1024 <= args.port <= 65535:
        parser.error("Dashboard-Port muss zwischen 1024 und 65535 liegen.")
    if args.check:
        return 0 if print_report() else 1
    if updater.state(ROOT).get("phase") in {"checking","installing"}:
        print("Ein Update läuft. Warte auf den Dashboard-Neustart.", file=sys.stderr)
        return 1
    if args.stop:
        base=f"http://127.0.0.1:{args.port}"
        status=request(base+"/api/version")
        if status: stop_older_server(base,status)
        print("Dashboard beendet.")
        return 0
    if args.setup:
        if shutil.which("mkcert") and not trust_ready():
            try:
                os.environ.update(configure_trust())
            except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
                print(str(exc), file=sys.stderr)
        print_report()
    base = f"http://127.0.0.1:{args.port}"
    version = panel_version()
    status = request(base + "/api/version")
    try:
        if status:
            if status.get("workspace_id") not in (None, workspace_id()):
                raise RuntimeError("Der Port wird von einer anderen Workbench verwendet. Mit --port einen anderen Port wählen.")
            if status.get("version") != version:
                print("Aktualisiert den Dashboard-Server …")
                stop_older_server(base, status)
                status = None
        if not status:
            occupied = False
            try:
                with socket.create_connection(("127.0.0.1", args.port), timeout=.3):
                    occupied = True
            except OSError:
                pass
            if occupied:
                stop_older_server(base, {})
            directory = ROOT / "var"
            directory.mkdir(exist_ok=True)
            with (directory / "panel.log").open("ab") as log:
                process = subprocess.Popen([sys.executable, str(ROOT / "scripts/panel_server.py")], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env={**os.environ, "PANEL_PORT": str(args.port)}, start_new_session=True)
            (directory / "panel.pid").write_text(str(process.pid) + "\n")
            for _ in range(30):
                status = request(base + "/api/version")
                if status and status.get("version") == version and status.get("workspace_id") == workspace_id():
                    break
                if process.poll() is not None:
                    raise RuntimeError(f"Dashboard konnte Port {args.port} nicht öffnen. Einen anderen Port wählen oder var/panel.log ansehen.")
                time.sleep(.1)
            else:
                raise RuntimeError("Dashboard antwortet noch nicht. Details stehen in var/panel.log.")
        url = base + "/?ui=" + version
        print("wsc-local · " + detect_host()["label"])
        print("Dashboard: " + url)
        if not args.no_open and os.environ.get("YES") != "1":
            open_dashboard(url)
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
