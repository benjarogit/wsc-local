"""Host checks and TLS/browser integration for Linux, macOS and Windows/WSL2."""
from __future__ import annotations

import json
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Any

TRUST_FILE = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "wsc-local/host-trust.json"


def certificate_root() -> Path | None:
    executable = shutil.which("mkcert.exe") if detect_host()["kind"] == "wsl2" else shutil.which("mkcert")
    if not executable:
        return None
    okay, root = _run([executable, "-CAROOT"])
    if not okay:
        return None
    if detect_host()["kind"] == "wsl2":
        okay, root = _run(["wslpath", "-u", root])
        if not okay:
            return None
    return Path(root)


def trust_ready() -> bool:
    root = certificate_root()
    try:
        recorded = json.loads(TRUST_FILE.read_text())
        return bool(root and recorded.get("sha256") == hashlib.sha256((root / "rootCA.pem").read_bytes()).hexdigest())
    except (OSError, ValueError):
        return False


def detect_host(system: str | None = None, release: str | None = None, env: dict[str, str] | None = None) -> dict[str, Any]:
    system = system if system is not None else platform.system()
    release = release if release is not None else platform.release()
    env = dict(os.environ) if env is None else env
    wsl = system == "Linux" and ("microsoft" in release.lower() or bool(env.get("WSL_DISTRO_NAME")))
    wsl2 = wsl and ("wsl2" in release.lower() or "microsoft-standard" in release.lower())
    kind = "wsl2" if wsl2 else "wsl1" if wsl else "macos" if system == "Darwin" else "linux" if system == "Linux" else "windows" if system == "Windows" else "unsupported"
    labels = {"wsl2": "Windows über WSL2", "wsl1": "Windows über WSL1", "macos": "macOS", "linux": "Linux", "windows": "Windows", "unsupported": system}
    return {"kind": kind, "label": labels[kind], "architecture": platform.machine(), "supported": kind in {"linux", "macos", "wsl2"}}


def _run(command: list[str], timeout: int = 8) -> tuple[bool, str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        return result.returncode == 0, result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return False, ""


def system_report() -> dict[str, Any]:
    host = detect_host()
    checks: list[dict[str, Any]] = []
    def add(key: str, label: str, okay: bool, detail: str, help_text: str, url: str = "") -> None:
        checks.append({"id": key, "label": label, "status": "ready" if okay else "missing", "detail": detail, "help": "" if okay else help_text, "url": url})
    add("host", "Betriebssystem", host["supported"], host["label"], "Windows: Start-wsc-local.cmd verwenden und eine WSL2-Distribution einrichten. Linux und macOS werden direkt unterstützt.", "https://learn.microsoft.com/windows/wsl/install")
    add("python", "Python", sys.version_info >= (3, 10), platform.python_version(), "Python 3.10 oder neuer installieren. macOS: brew install python; Ubuntu/WSL: sudo apt install python3.", "https://www.python.org/downloads/")
    docker = shutil.which("docker")
    okay, engine = _run([docker, "info", "--format", "{{.OSType}}|{{.ServerVersion}}"], 8) if docker else (False, "")
    linux_engine = okay and engine.startswith("linux|")
    engine_detail = "Linux-Container · Docker " + engine.split("|", 1)[1] if linux_engine else "Docker fehlt" if not docker else "Docker antwortet nicht oder verwendet Windows-Container"
    add("docker", "Docker", linux_engine, engine_detail, "Docker Desktop bzw. Docker Engine starten. Unter Windows Linux-Container und die WSL-Integration für deine Distribution aktivieren.", "https://docs.docker.com/desktop/")
    compose_ok, version = _run([docker, "compose", "version", "--short"]) if docker else (False, "")
    add("compose", "Docker Compose", compose_ok, "Version " + version if compose_ok else "Compose-Plugin fehlt", "Das Docker-Compose-Plugin installieren; bei Docker Desktop ist es enthalten.", "https://docs.docker.com/compose/install/")
    mkcert = bool(shutil.which("mkcert"))
    hint = "mkcert installieren. macOS: brew install mkcert nss. Ubuntu/WSL: sudo apt install mkcert libnss3-tools. Andere Linux-Systeme: offizielle Installationsanleitung öffnen."
    add("mkcert", "Lokales HTTPS", mkcert, "mkcert verfügbar" if mkcert else "mkcert fehlt", hint, "https://github.com/FiloSottile/mkcert#installation")
    trusted = mkcert and trust_ready()
    add("trust", "HTTPS-Freigabe", trusted, "Zertifizierungsstelle eingerichtet" if trusted else "Einmalige Freigabe erforderlich", "Im Terminal ./setup.sh starten. Dabei wird die lokale Zertifizierungsstelle eingerichtet; eine Systemabfrage kann erscheinen.")
    if host["kind"] in {"wsl1", "wsl2"}:
        windows_mkcert = bool(shutil.which("mkcert.exe"))
        add("windows_tls", "HTTPS im Windows-Browser", windows_mkcert, "Windows-mkcert verfügbar" if windows_mkcert else "Gemeinsame Zertifizierungsstelle noch nicht verfügbar", "Zusätzlich mkcert in Windows installieren und WSL danach neu öffnen. Die Workbench verwendet dann dieselbe Zertifizierungsstelle für Windows und WSL.", "https://github.com/FiloSottile/mkcert#windows")
    return {"host": host, "ready": all(check["status"] == "ready" for check in checks), "checks": checks}


def tls_environment() -> dict[str, str]:
    """Use one CA in WSL and Windows so the user's actual browser trusts TLS."""
    env = os.environ.copy()
    if detect_host()["kind"] != "wsl2":
        return env
    windows_mkcert = shutil.which("mkcert.exe")
    if not windows_mkcert:
        raise RuntimeError("Für HTTPS im Windows-Browser wird mkcert auch unter Windows benötigt. Installiere es dort und öffne WSL erneut. Anleitung: https://github.com/FiloSottile/mkcert#windows")
    installed = subprocess.run([windows_mkcert, "-install"], capture_output=True, text=True, timeout=120, check=False)
    if installed.returncode:
        raise RuntimeError("Die lokale Zertifizierungsstelle konnte in Windows nicht eingerichtet werden. Bestätige die Windows-Systemabfrage und versuche es erneut.")
    root = subprocess.run([windows_mkcert, "-CAROOT"], capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    converted = subprocess.run(["wslpath", "-u", root], capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    if not Path(converted).is_dir():
        raise RuntimeError("Die gemeinsame Zertifizierungsstelle von Windows und WSL ist nicht erreichbar.")
    env["CAROOT"] = converted
    return env


def configure_trust() -> dict[str, str]:
    """Run the one-time trust step in the user's terminal, before daemonizing."""
    executable = shutil.which("mkcert")
    if not executable:
        raise RuntimeError("mkcert fehlt. Die Installationshinweise stehen in der Systemprüfung.")
    env = tls_environment()
    print("Einmalige HTTPS-Freigabe: Bestätige bei Bedarf die Systemabfrage.", flush=True)
    result = subprocess.run([executable, "-install"], env=env, check=False)
    if result.returncode:
        raise RuntimeError("HTTPS-Freigabe nicht abgeschlossen. ./setup.sh im Terminal erneut starten.")
    root = subprocess.check_output([executable, "-CAROOT"], text=True, env=env).strip()
    fingerprint = hashlib.sha256((Path(root) / "rootCA.pem").read_bytes()).hexdigest()
    TRUST_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRUST_FILE.write_text(json.dumps({"sha256": fingerprint, "host": detect_host()["kind"]}) + "\n")
    TRUST_FILE.chmod(0o600)
    return env


def open_dashboard(url: str) -> None:
    try:
        if detect_host()["kind"] == "wsl2" and shutil.which("powershell.exe"):
            subprocess.Popen(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", "Start-Process", url], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            webbrowser.open(url)
    except OSError:
        pass  # The launcher always prints the local address as well.


def print_report(as_json: bool = False) -> bool:
    report = system_report()
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"wsc-local · Systemprüfung · {report['host']['label']}")
        for check in report["checks"]:
            print(f"{'OK' if check['status'] == 'ready' else 'FEHLT'}  {check['label']}: {check['detail']}")
            if check["help"]:
                print(f"       {check['help']}")
        print("Bereit für WoltLab." if report["ready"] else "Voraussetzungen ergänzen und die Prüfung erneut starten.")
    return report["ready"]
