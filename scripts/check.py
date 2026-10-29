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
RELEASE_URL = 'https://github.com/benjarogit/wsc-local/releases'
LATEST_URL = RELEASE_URL + '/latest'
ZIP_URL = LATEST_URL + '/download/wsc-local.zip'
PINNED_RELEASE = re.compile(r'/releases/(?:tag|download)/v\d+\.\d+\.\d+')
PINNED_ARCHIVE = re.compile(r'wsc-local-\d+\.\d+\.\d+\.zip')


def run(label: str, command: list[str]) -> None:
    print(f'\n== {label} ==', flush=True)
    print('$ ' + ' '.join(command), flush=True)
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode:
        raise SystemExit(f'{label} fehlgeschlagen (Exit {result.returncode}).')


def release_problems(root: Path) -> list[str]:
    """Return release metadata problems without touching the repository.

    The README files must not pin a version: they link the latest release and a
    stable ZIP name, so a release needs no documentation commit.
    """
    version = (root / 'VERSION').read_text(encoding='utf-8').strip()
    problems: list[str] = []
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        problems.append(f'VERSION enthält keine gültige Version: {version!r}.')
    changelog = (root / 'CHANGELOG.md').read_text(encoding='utf-8')
    if not re.search(rf'^## {re.escape(version)} [–-] ', changelog, re.M):
        problems.append(f'CHANGELOG.md hat keinen Abschnitt "## {version} – <Datum>".')
    for name in ('README.md', 'README.en.md'):
        text = (root / name).read_text(encoding='utf-8')
        if LATEST_URL not in text:
            problems.append(f'{name} verlinkt nicht die jeweils neueste Veröffentlichung ({LATEST_URL}).')
        if ZIP_URL not in text:
            problems.append(f'{name} verlinkt nicht den stabilen ZIP-Download ({ZIP_URL}).')
        pinned = sorted(set(PINNED_RELEASE.findall(text)) | set(PINNED_ARCHIVE.findall(text)))
        if pinned:
            problems.append(f'{name} enthält feste Versionsverweise ({", ".join(pinned)}); die Version wird automatisch angezeigt.')
    return problems


def metadata_check() -> None:
    problems = release_problems(ROOT)
    if problems:
        raise SystemExit('Release-Metadaten fehlerhaft:\n- ' + '\n- '.join(problems))


def release_check(git: str | None) -> None:
    metadata_check()
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
        alias = Path(directory) / 'wsc-local.zip'
        if not alias.is_file() or alias.read_bytes() != archive.read_bytes():
            raise SystemExit('Der stabile Download wsc-local.zip fehlt oder weicht vom Release-ZIP ab.')
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
    parser.add_argument('--metadata', action='store_true', help='nur die Release-Metadaten prüfen')
    parser.add_argument('--release', action='store_true', help='Release-Metadaten prüfen und das ZIP probeweise bauen (braucht einen sauberen Commit)')
    args = parser.parse_args()

    if args.metadata:
        metadata_check()
        print('Release-Metadaten in Ordnung.')
        return 0

    run('Python-Tests', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'])
    run('Python-Syntax', [sys.executable, '-m', 'compileall', '-q', 'workbench', 'scripts', 'tests'])

    node = shutil.which('node')
    if not node:
        raise SystemExit('Node.js fehlt. Installiere Node.js für die JavaScript-Prüfungen.')
    for path in sorted((ROOT / 'panel').glob('*.js')):
        run(f'JavaScript-Syntax: {path.name}', [node, '--check', str(path)])

    bash = shutil.which('bash')
    git = shutil.which('git')
    if bash:
        entries = [
            'scripts/install-host.sh', 'setup.sh', 'start.sh', 'panel.sh',
            'scripts/legacy/setup.sh', 'scripts/legacy/start.sh',
        ]
        run('Bash-Einstiegspunkte', [bash, '-n', *entries])

    ruff = shutil.which('ruff')
    if ruff:
        run('Python-Lint (ruff)', [ruff, 'check', '--select', 'E9,F63,F7,F82,F821', 'workbench', 'scripts', 'tests'])
    else:
        print('\nruff nicht installiert; Python-Lint übersprungen.')

    shellcheck = shutil.which('shellcheck')
    if shellcheck and git:
        shell_scripts = subprocess.check_output([git, 'ls-files', '*.sh'], cwd=ROOT, text=True).split()
        run('Bash-Lint (shellcheck)', [shellcheck, '-S', 'warning', '-e', 'SC1111', '-x', *shell_scripts])
    elif not shellcheck:
        print('\nshellcheck nicht installiert; Bash-Lint übersprungen.')

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
