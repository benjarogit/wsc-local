#!/usr/bin/env python3
"""Local verification harness for the Workbench.

Runs the same portable checks as CI, optionally including the Chromium suite.
With --release it also validates the release metadata and builds the package
once, so a broken tag fails locally instead of in the release workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = '.wsc-local-release.json'


def run(label: str, command: list[str]) -> None:
    print(f'\n== {label} ==', flush=True)
    print('$ ' + ' '.join(command), flush=True)
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode:
        raise SystemExit(f'{label} fehlgeschlagen (Exit {result.returncode}).')


def release_problems(root: Path) -> list[str]:
    """Return release metadata problems without touching the repository."""
    version = (root / 'VERSION').read_text(encoding='utf-8').strip()
    problems: list[str] = []
    changelog = (root / 'CHANGELOG.md').read_text(encoding='utf-8')
    if not re.search(rf'^## {re.escape(version)} [–-] ', changelog, re.M):
        problems.append(f'CHANGELOG.md hat keinen Abschnitt "## {version} – <Datum>".')
    for name in ('README.md', 'README.en.md'):
        text = (root / name).read_text(encoding='utf-8')
        if f'v{version}' not in text:
            problems.append(f'{name} verweist nicht auf v{version}.')
        if f'wsc-local-{version}.zip' not in text:
            problems.append(f'{name} verlinkt nicht wsc-local-{version}.zip.')
    return problems


def release_check(git: str | None) -> None:
    problems = release_problems(ROOT)
    if problems:
        raise SystemExit('Release-Prüfung fehlgeschlagen:\n- ' + '\n- '.join(problems))
    if git:
        dirty = subprocess.run([git, 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        if dirty:
            raise SystemExit('Die Release-Prüfung braucht einen sauberen Arbeitsstand. Erst committen, dann erneut ausführen.')
    version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
    with tempfile.TemporaryDirectory(prefix='wsc-release-check-') as directory:
        run('Release-Paket (Probe)', [sys.executable, 'scripts/release.py', '--tag', 'v' + version, '--ref', 'HEAD', '--output', directory])
        archive = Path(directory) / f'wsc-local-{version}.zip'
        if not archive.is_file():
            raise SystemExit('Die Release-Probe hat kein ZIP erzeugt.')
        base = f'wsc-local-{version}/'
        with zipfile.ZipFile(archive) as package:
            manifest = json.loads(package.read(base + MANIFEST))
            if manifest.get('version') != version:
                raise SystemExit('Der Dateikatalog der Release-Probe hat die falsche Version.')
            for name, digest in manifest['files'].items():
                if hashlib.sha256(package.read(base + name)).hexdigest() != digest:
                    raise SystemExit(f'Die Prüfsumme von {name} stimmt in der Release-Probe nicht.')


def main() -> int:
    parser = argparse.ArgumentParser(description='Workbench-Prüfungen lokal ausführen')
    parser.add_argument('--ui', action='store_true', help='zusätzlich die Chromium-Tests ausführen')
    parser.add_argument('--release', action='store_true', help='Release-Metadaten prüfen und das ZIP probeweise bauen (braucht einen sauberen Commit)')
    args = parser.parse_args()

    run('Python-Tests', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'])
    run('Python-Syntax', [sys.executable, '-m', 'compileall', '-q', 'workbench', 'scripts', 'tests'])

    node = shutil.which('node')
    if not node:
        raise SystemExit('Node.js fehlt. Installiere Node.js für die JavaScript-Prüfungen.')
    for path in sorted((ROOT / 'panel').glob('*.js')):
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
        if not (ROOT / 'node_modules' / 'playwright').exists():
            raise SystemExit('Playwright fehlt. Führe zuerst npm ci und npx playwright install chromium aus.')
        run('Chromium-Tests', [npm, 'run', 'test:ui'])

    if args.release:
        release_check(git)

    print('\nAlle Prüfungen bestanden.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
