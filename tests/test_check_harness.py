"""Release metadata and repository hygiene checks used by CI."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check
import check_repo


class ReleaseCheckTests(unittest.TestCase):
    def write(self, root, name, text):
        (root / name).write_text(text, encoding='utf-8')

    def test_missing_changelog_section_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, 'VERSION', '1.2.3\n')
            self.write(root, 'CHANGELOG.md', '# Änderungen\n\n## 1.2.2 – 2026-01-01\n')
            for name in ('README.md', 'README.en.md'):
                self.write(root, name, check.LATEST_URL + '\n' + check.ZIP_URL + '\n')
            problems = check.release_problems(root)
        self.assertEqual(len(problems), 1)
        self.assertIn('CHANGELOG.md', problems[0])

    def test_pinned_readme_version_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, 'VERSION', '1.2.3\n')
            self.write(root, 'CHANGELOG.md', '# Änderungen\n\n## 1.2.3 – 2026-01-01\n')
            self.write(
                root,
                'README.md',
                '**Version: [v1.2.3](https://github.com/benjarogit/wsc-local/releases/tag/v1.2.3)**\n',
            )
            self.write(root, 'README.en.md', check.LATEST_URL + '\n' + check.ZIP_URL + '\n')
            problems = check.release_problems(root)
        self.assertEqual(len(problems), 3)
        self.assertTrue(all('README.md' in problem for problem in problems))
        self.assertTrue(any('feste Versionsverweise' in problem for problem in problems))

    def test_invalid_version_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, 'VERSION', 'current\n')
            self.write(root, 'CHANGELOG.md', '# Änderungen\n')
            for name in ('README.md', 'README.en.md'):
                self.write(root, name, check.LATEST_URL + '\n' + check.ZIP_URL + '\n')
            problems = check.release_problems(root)
        self.assertTrue(any('keine gültige Version' in problem for problem in problems))

    def test_matching_metadata_has_no_problems(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, 'VERSION', '1.2.3\n')
            self.write(root, 'CHANGELOG.md', '# Änderungen\n\n## 1.2.3 – 2026-01-01\n')
            for name in ('README.md', 'README.en.md'):
                self.write(root, name, check.LATEST_URL + '\n' + check.ZIP_URL + '\n')
            self.assertEqual(check.release_problems(root), [])


class RepositoryCheckTests(unittest.TestCase):
    def test_runtime_and_credential_paths_are_rejected(self):
        self.assertIsNone(check_repo.path_problem('var/.gitkeep'))
        self.assertIsNone(check_repo.path_problem('panel/app.js'))
        self.assertIsNone(check_repo.path_problem('.env.example'))
        for name in (
            'var/projects/demo/.env',
            'snapshots/20260101_backup.tar',
            'certs/local.pem',
            'woltlab/wsc/global.php',
            'node_modules/playwright/index.js',
            '.env',
            'logs/update.log',
            'release.zip',
        ):
            self.assertIsNotNone(check_repo.path_problem(name), name)

    def test_text_hygiene_finds_careless_formatting(self):
        self.assertEqual(check_repo.text_problems('panel/app.js', b'const a = 1;\n'), [])
        self.assertEqual(check_repo.text_problems('Start-wsc-local.ps1', b'Write-Host ok\r\n'), [])
        self.assertTrue(check_repo.text_problems('panel/app.js', b'const a = 1;  \n'))
        self.assertTrue(check_repo.text_problems('panel/app.js', b'const a = 1;'))
        self.assertTrue(check_repo.text_problems('start.sh', b'#!/bin/sh\r\n'))
        self.assertEqual(check_repo.text_problems('panel/vendor/icons.svg', b'<svg/>'), [])

    def test_relative_markdown_links_must_resolve(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / 'docs').mkdir()
            (base / 'docs' / 'guide.md').write_text('Hallo\n', encoding='utf-8')
            text = '[ok](docs/guide.md) [anchor](#top) [web](https://example.test) [bad](docs/missing.md)'
            self.assertEqual(check_repo.link_problems(text, base), ['docs/missing.md'])


if __name__ == '__main__':
    unittest.main()
