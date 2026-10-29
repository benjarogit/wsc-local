#!/usr/bin/env python3
"""Local verification harness for the Workbench.

Runs the same portable checks as CI, optionally including the Chromium suite.
The release workflow remains authoritative for the full platform matrix.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(label: str, command: list[str]) -> None:
    print(f'\n== {label} ==', flush=True)
    print('$ ' + ' '.join(command), flush=True)
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode:
        raise SystemExit(f'{label} fehlgeschlagen (Exit {result.returncode}).')


def main() -> int:
    parser = argparse.ArgumentParser(description='Workbench-Prüfungen lokal ausführen')
    parser.add_argument('--ui', action='store_true', help='zusätzlich die Chromium-Tests ausführen')
    args = parser.parse_args()

    run('Python-Tests', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'])
    run('Python-Syntax', [sys.executable, '-m', 'compileall', '-q', 'workbench', 'scripts', 'tests'])

    node = shutil.which('node')
    if not node:
        raise SystemExit('Node.js fehlt. Installiere Node.js für die JavaScript-Prüfungen.')
    for path in sorted((ROOT/'panel').glob('*.js')):
        run(f'JavaScript-Syntax: {path.name}', [node, '--check', str(path)])

    bash = shutil.which('bash')
    if bash:
        entries = [
            'scripts/install-host.sh', 'setup.sh', 'start.sh', 'panel.sh',
            'scripts/legacy/setup.sh', 'scripts/legacy/start.sh',
        ]
        run('Bash-Einstiegspunkte', [bash, '-n', *entries])

    git = shutil.which('git')
    if git:
        run('Git-Whitespace', [git, 'diff', '--check'])

    if args.ui:
        npm = shutil.which('npm')
        if not npm:
            raise SystemExit('npm fehlt. Installiere Node.js und führe npm ci aus.')
        if not (ROOT/'node_modules'/'playwright').exists():
            raise SystemExit('Playwright fehlt. Führe zuerst npm ci und npx playwright install chromium aus.')
        run('Chromium-Tests', [npm, 'run', 'test:ui'])

    print('\nAlle Prüfungen bestanden.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
