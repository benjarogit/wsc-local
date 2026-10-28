"""Fixed platform installers, launched in the user's OS terminal (never web sudo)."""
from __future__ import annotations
import json
import os
import shlex
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from host_system import detect_host

ROOT = Path(__file__).resolve().parent.parent


def installation_plan(host: dict | None = None) -> dict:
    host = host or detect_host()
    kind = host['kind']
    supported = kind in {'linux', 'macos', 'wsl2'}
    if kind == 'linux':
        supported = any(shutil.which(tool) for tool in ('apt-get', 'dnf', 'pacman'))
    steps = {
        'linux': ['Fehlende Python-, mkcert- und NSS-Pakete über die Linux-Paketverwaltung installieren.', 'Fehlendes Docker für die lokale Entwicklung installieren und starten; gegebenenfalls die Docker-Gruppe mit administrativen Rechten einrichten.', 'Lokale HTTPS-Zertifizierungsstelle einrichten und Voraussetzungen erneut prüfen.'],
        'macos': ['Bei Bedarf Homebrew einrichten und fehlende Python-, mkcert- und NSS-Pakete installieren.', 'Fehlendes Docker Desktop installieren und öffnen. Die erste Freigabe erfolgt in Docker Desktop.', 'Lokale HTTPS-Zertifizierungsstelle einrichten und Voraussetzungen erneut prüfen.'],
        'wsl2': ['Fehlende Linux-Pakete innerhalb deiner WSL2-Distribution installieren.', 'Fehlendes Docker Desktop und mkcert unter Windows über winget installieren.', 'Die erste Docker-Desktop-Freigabe und WSL-Integration bestätigen; gemeinsame HTTPS-Zertifizierungsstelle einrichten.'],
    }.get(kind, [])
    return {'supported': supported, 'platform': kind, 'steps': steps, 'command': 'bash ' + shlex.quote(str(ROOT / 'setup.sh')) + ' --install-deps'}


def terminal_command(root: Path, status: Path, kind: str | None = None) -> list[str]:
    kind = kind or detect_host()['kind']
    command = ['bash', str(root / 'scripts/install-host.sh'), '--status', str(status), '--pause']
    if kind == 'macos':
        # AppleScript string escaping is distinct from shell argument quoting.
        line = shlex.join(command)
        return ['osascript', '-e', 'tell application "Terminal" to do script ' + json.dumps(line, ensure_ascii=False), '-e', 'tell application "Terminal" to activate']
    if kind == 'wsl2':
        distro = os.environ.get('WSL_DISTRO_NAME')
        if not distro: raise RuntimeError('Die WSL2-Distribution konnte nicht ermittelt werden.')
        args = ['wsl.exe', '--distribution', distro, '--exec', *command]
        # Encoded PowerShell command preserves paths/distro names without interpolation.
        import base64
        expression = '& ' + ' '.join("'" + value.replace("'", "''") + "'" for value in args)
        launch = 'Start-Process powershell.exe -ArgumentList ' + "'-NoProfile','-EncodedCommand','" + base64.b64encode(expression.encode('utf-16le')).decode() + "'"
        return ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', launch]
    if kind == 'linux':
        for executable, args in [('x-terminal-emulator',['-e']), ('gnome-terminal',['--']), ('konsole',['-e']), ('xfce4-terminal',['--disable-server','-x']), ('xterm',['-e'])]:
            if shutil.which(executable): return [executable,*args,*command]
    raise RuntimeError('Kein Systemterminal verfügbar. Starte im Terminal: ' + installation_plan()['command'])


def launch_installation(root: Path = ROOT, timeout: float = 3600) -> dict:
    plan = installation_plan()
    if not plan['supported']: raise RuntimeError('Für dieses System steht keine automatische Einrichtung bereit. Anleitung: docs/platforms.md')
    directory = root / 'var' / 'host-setup'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    status = directory / (uuid.uuid4().hex + '.status')
    # Reserve a private, regular file; never follow a pre-existing user path.
    descriptor = os.open(status, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        command = terminal_command(root, status)
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = status.read_text().strip()
            if value:
                if value != '0': raise RuntimeError('Die Einrichtung wurde nicht abgeschlossen. Beachte die Hinweise im Systemterminal und starte danach die Systemprüfung erneut.')
                return {'completed': True}
            if process.poll() not in (None, 0): raise RuntimeError('Das Systemterminal konnte nicht geöffnet werden. Starte: ' + plan['command'])
            time.sleep(1)
        raise RuntimeError('Die Terminaleinrichtung meldet keinen Abschluss. Prüfe das Terminal und starte die Systemprüfung erneut.')
    finally:
        status.unlink(missing_ok=True)
