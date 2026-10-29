"""Release metadata checks used by scripts/check.py --release."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check


class ReleaseCheckTests(unittest.TestCase):
    def test_missing_changelog_and_readme_links_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'VERSION').write_text('1.2.3\n', encoding='utf-8')
            (root / 'CHANGELOG.md').write_text('# Änderungen\n\n## 1.2.2 – 2026-01-01\n', encoding='utf-8')
            (root / 'README.md').write_text('v1.2.2\n', encoding='utf-8')
            (root / 'README.en.md').write_text('v1.2.3\n', encoding='utf-8')
            problems = check.release_problems(root)
        self.assertEqual(len(problems), 4)
        self.assertTrue(any('CHANGELOG.md' in problem for problem in problems))
        self.assertTrue(any('README.md' in problem for problem in problems))
        self.assertTrue(any('README.en.md' in problem for problem in problems))

    def test_matching_metadata_has_no_problems(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'VERSION').write_text('1.2.3\n', encoding='utf-8')
            (root / 'CHANGELOG.md').write_text('# Änderungen\n\n## 1.2.3 – 2026-01-01\n', encoding='utf-8')
            for name in ('README.md', 'README.en.md'):
                (root / name).write_text('v1.2.3 wsc-local-1.2.3.zip\n', encoding='utf-8')
            self.assertEqual(check.release_problems(root), [])


if __name__ == '__main__':
    unittest.main()
