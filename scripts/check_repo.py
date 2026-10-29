#!/usr/bin/env python3
"""Repository hygiene checks for the tracked files.

Guards against committed runtime data and credentials, oversized files,
careless text formatting, invalid JSON and broken relative Markdown links.
The script only reads; it never changes files.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 2 * 1024 * 1024

# Project data, backups, certificates and build output stay outside the repository.
RUNTIME_ROOTS = ('var/', 'snapshots/', 'certs/', 'woltlab/', 'node_modules/', 'dist/', '__pycache__/', '.wsc-local/')
RUNTIME_KEEP = {'var/.gitkeep', 'snapshots/.gitkeep', 'certs/.gitkeep', 'woltlab/.gitkeep'}
FORBIDDEN_SUFFIXES = ('.pyc', '.pyo', '.zip', '.log', '.pem', '.key', '.crt', '.p12', '.pfx', '.db', '.sqlite', '.sql')
FORBIDDEN_NAMES = {'.env'}
BINARY_SUFFIXES = ('.png', '.jpg', '.jpeg', '.gif', '.ico', '.webp', '.woff', '.woff2', '.ttf', '.otf', '.pdf')
CRLF_SUFFIXES = ('.ps1', '.cmd', '.bat')
TEXT_SKIP_DIRS = ('panel/vendor/',)


def tracked_files(root: Path) -> list[str]:
    output = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root)
    return [name for name in output.decode('utf-8').split('\0') if name]


def path_problem(name: str) -> str | None:
    """Return a reason when a tracked path must not be committed."""
    if name in RUNTIME_KEEP:
        return None
    if any(name.startswith(prefix) for prefix in RUNTIME_ROOTS):
        return 'Laufzeit- oder Projektdatei gehört nicht ins Repository'
    if Path(name).name in FORBIDDEN_NAMES:
        return 'Zugangsdatei gehört nicht ins Repository'
    if name.lower().endswith(FORBIDDEN_SUFFIXES):
        return 'Dateityp gehört nicht ins Repository'
    return None


def text_problems(name: str, data: bytes) -> list[str]:
    """Return formatting problems for a tracked text file."""
    if name.endswith(BINARY_SUFFIXES) or any(name.startswith(prefix) for prefix in TEXT_SKIP_DIRS):
        return []
    problems: list[str] = []
    if b'\r\n' in data and not name.endswith(CRLF_SUFFIXES):
        problems.append('Windows-Zeilenenden (CRLF) statt LF')
    text = data.decode('utf-8', 'replace')
    for number, line in enumerate(text.splitlines(), 1):
        if line != line.rstrip():
            problems.append(f'Zeile {number}: Leerzeichen am Zeilenende')
            break
    if data and not data.endswith(b'\n'):
        problems.append('kein Zeilenumbruch am Dateiende')
    return problems


def link_problems(text: str, base: Path) -> list[str]:
    """Return relative Markdown links that do not resolve."""
    problems: list[str] = []
    for target in re.findall(r'\]\(([^)\s]+)', text):
        if re.match(r'[a-z][a-z0-9+.-]*:', target) or target.startswith('#'):
            continue
        path = urllib.parse.unquote(target.split('#')[0])
        if path and not (base / path).exists():
            problems.append(target)
    return problems


def repository_problems(root: Path) -> list[str]:
    problems: list[str] = []
    for name in tracked_files(root):
        path = root / name
        reason = path_problem(name)
        if reason:
            problems.append(f'{name}: {reason}.')
            continue
        if not path.is_file():
            problems.append(f'{name}: Eintrag ist keine reguläre Datei.')
            continue
        size = path.stat().st_size
        if size > MAX_BYTES:
            problems.append(f'{name}: {size / 1024 / 1024:.1f} MB ist zu groß für das Repository.')
        for detail in text_problems(name, path.read_bytes()):
            problems.append(f'{name}: {detail}.')
        if name.endswith('.json'):
            try:
                json.loads(path.read_text(encoding='utf-8'))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                problems.append(f'{name}: ungültiges JSON ({error}).')
        if name.endswith('.md'):
            for target in link_problems(path.read_text(encoding='utf-8'), path.parent):
                problems.append(f'{name}: relativer Verweis {target!r} führt ins Leere.')
    return problems


def main() -> int:
    try:
        problems = repository_problems(ROOT)
    except (OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Repository-Prüfung nicht möglich: {error}')
    if problems:
        print('Repository-Prüfung fehlgeschlagen:', file=sys.stderr)
        for problem in problems:
            print(f'- {problem}', file=sys.stderr)
        return 1
    count = len(tracked_files(ROOT))
    print(f'Repository-Prüfung in Ordnung ({count} Dateien).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
