"""Custom-code Git helpers stay outside site/ and refuse unsafe pushes."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workbench"))
import code_repo
import cli


def run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True)


class CodeRepoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.projects = self.home / "projects"
        self.projects.mkdir()
        self.name = "demo"
        self.root = self.projects / self.name
        self.root.mkdir()
        (self.root / "site").mkdir()
        (self.root / "site" / "config.inc.php").write_text("<?php secret", encoding="utf-8")
        self.cfg = {
            "schema": 1,
            "name": self.name,
            "project": "wsc-demo",
            "suite_version": "6.2",
            "php_version": "8.4",
            "profile_status": "supported",
            "url": "https://demo.localhost:8081",
        }
        (self.root / "wsc-local.json").write_text(json.dumps(self.cfg, indent=2) + "\n", encoding="utf-8")
        self.env = patch.dict(os.environ, {"WSC_LOCAL_HOME": str(self.home), "XDG_CONFIG_HOME": str(self.home / "config")})
        self.env.start()
        cli.DATA = self.home
        cli.PROJECTS = self.projects
        cli.SECRETS = self.home / "config" / "wsc-local" / "secrets"
        cli.SECRETS.mkdir(parents=True)

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_init_creates_code_repo_without_touching_site(self):
        message = code_repo.init_code(self.name, self.cfg, self.root)
        self.assertIn(str(self.root / "code"), message)
        self.assertTrue((self.root / "code" / ".git").exists())
        self.assertTrue((self.root / "code" / "packages" / ".gitkeep").exists())
        self.assertTrue((self.root / "code" / "AGENTS.md").is_file())
        self.assertEqual("<?php secret", (self.root / "site" / "config.inc.php").read_text(encoding="utf-8"))
        listed = run(self.root / "code", "git", "ls-files").stdout
        self.assertNotIn("site/", listed)
        self.assertNotIn("config.inc.php", listed)
        status = code_repo.code_status(self.name, self.cfg, self.root)
        self.assertTrue(status["enabled"])
        self.assertEqual(status["path"], str(self.root / "code"))

    def test_commit_rejects_secret_files(self):
        code_repo.init_code(self.name, self.cfg, self.root)
        target = self.root / "code" / "config.inc.php"
        target.write_text("<?php leaked", encoding="utf-8")
        with self.assertRaises(ValueError) as raised:
            code_repo.commit_code(self.name, self.cfg, self.root, "add secret")
        self.assertIn("config.inc.php", str(raised.exception))
        self.assertIn("gestoppt", str(raised.exception))

    def test_push_requires_confirmation_and_managed_origin(self):
        code_repo.init_code(self.name, self.cfg, self.root)
        with self.assertRaises(ValueError) as missing:
            code_repo.push_code(self.name, self.cfg, self.root, confirmed=False)
        self.assertIn("Bestätigung", str(missing.exception))
        with self.assertRaises(ValueError) as unmanaged:
            code_repo.push_code(self.name, self.cfg, self.root, confirmed=True)
        self.assertIn("kein von der Workbench verwaltetes", str(unmanaged.exception))
        self.cfg["code_github"] = {
            "owner": "example",
            "name": "wsc-demo",
            "url": "https://github.com/example/wsc-demo",
        }
        run(self.root / "code", "git", "remote", "add", "origin", "https://github.com/other/foreign.git")
        with self.assertRaises(ValueError) as foreign:
            code_repo.push_code(self.name, self.cfg, self.root, confirmed=True)
        self.assertIn("origin zeigt auf", str(foreign.exception))

    def test_worktree_lives_outside_code(self):
        code_repo.init_code(self.name, self.cfg, self.root)
        real_which = shutil.which

        def which(name: str):
            if name in {"cursor", "code"}:
                return None
            return real_which(name)

        with patch.object(shutil, "which", side_effect=which):
            message = code_repo.add_worktree(self.name, self.cfg, self.root, "agent-1")
        worktree = self.root / "worktrees" / "agent-1"
        self.assertTrue(worktree.is_dir())
        self.assertIn(str(worktree), message)
        self.assertFalse(str(worktree).startswith(str(self.root / "code") + os.sep) or worktree == self.root / "code")
        status = code_repo.code_status(self.name, json.loads((self.root / "wsc-local.json").read_text()), self.root)
        self.assertEqual(status["worktrees"][0]["branch"], "agent-1")
        self.assertEqual(status["worktrees"][0]["path"], str(worktree))

    def test_worktree_list_accepts_resolved_symlink_paths(self):
        real = self.home / "real"
        linked = real / "worktrees" / "agent-1"
        linked.mkdir(parents=True)
        alias = self.home / "alias"
        try:
            alias.symlink_to(real, target_is_directory=True)
        except OSError:
            self.skipTest("Symlinks sind auf diesem System nicht verfügbar.")
        self.assertTrue(code_repo._inside(linked, alias / "worktrees"))
        self.assertFalse(code_repo._inside(self.home / "elsewhere", alias / "worktrees"))

    def test_github_create_refuses_existing_foreign_repo_name(self):
        code_repo.init_code(self.name, self.cfg, self.root)

        def fake_gh(*args, check=True, timeout=60):
            del timeout
            if args[:2] == ("auth", "status"):
                return subprocess.CompletedProcess(args, 0, "", "")
            if args[:2] == ("repo", "view"):
                return subprocess.CompletedProcess(args, 0, '{"name":"wsc-demo"}', "")
            raise AssertionError(args)

        with patch.object(code_repo, "gh", side_effect=fake_gh), patch.object(code_repo, "require_gh", return_value="gh"):
            with self.assertRaises(ValueError) as raised:
                code_repo.github_create(self.name, self.cfg, self.root)
        self.assertIn("existiert bereits", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
