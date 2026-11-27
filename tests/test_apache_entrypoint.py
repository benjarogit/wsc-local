"""Verify numeric Apache workers are resolved before starting the server."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ENTRYPOINT = Path(__file__).resolve().parents[1] / "workbench" / "runtime" / "apache" / "entrypoint.sh"


@unittest.skipUnless(os.name == "posix" and shutil.which("sh"), "POSIX shell required")
class ApacheEntrypointTests(unittest.TestCase):
    def start(self, uid="1000", gid="1000", known="", failed_command=""):
        with tempfile.TemporaryDirectory() as directory:
            executables = Path(directory)
            stub = """#!/bin/sh
command=${0##*/}
if [ "$command" = getent ]; then
    case "$KNOWN" in *"$1"*) exit 0;; esac
    exit 2
fi
printf '%s %s\n' "$command" "$*"
if [ "$command" = "$FAILED_COMMAND" ]; then
    exit 1
fi
if [ "$command" = apache2-foreground ]; then
    printf '%s %s\n' "$APACHE_RUN_USER" "$APACHE_RUN_GROUP"
fi
"""
            for command in ("getent", "groupadd", "useradd", "apache2-foreground"):
                path = executables / command
                path.write_text(stub, encoding="utf-8")
                path.chmod(0o755)
            env = dict(os.environ, PATH=directory, HOST_UID=uid, HOST_GID=gid,
                       KNOWN=known, FAILED_COMMAND=failed_command)
            return subprocess.run(["/bin/sh", str(ENTRYPOINT)], env=env, capture_output=True, text=True, timeout=10)

    def test_missing_worker_identity_is_created(self):
        result = self.start()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.splitlines(), [
            "groupadd --gid 1000 wsc-local-gid-1000",
            "useradd --uid 1000 --gid 1000 --no-user-group --no-create-home --no-log-init "
            "--shell /usr/sbin/nologin wsc-local-uid-1000",
            "apache2-foreground ",
            "#1000 #1000",
        ])

    def test_known_user_and_group_are_reused(self):
        result = self.start(uid="33", gid="33", known="passwd group")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.splitlines(), ["apache2-foreground ", "#33 #33"])

    def test_known_group_is_not_recreated_for_a_new_user(self):
        result = self.start(uid="501", gid="20", known="group")
        self.assertEqual(result.returncode, 0)
        self.assertIn("useradd --uid 501 --gid 20", result.stdout)
        self.assertNotIn("groupadd", result.stdout)
        self.assertTrue(result.stdout.endswith("#501 #20\n"))

    def test_invalid_or_root_worker_uid_prevents_server_start(self):
        for uid, gid in (("0", "1000"), ("nobody", "1000"), ("1000", "-1")):
            with self.subTest(uid=uid, gid=gid):
                result = self.start(uid=uid, gid=gid)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")

    def test_failed_identity_registration_prevents_server_start(self):
        for command in ("groupadd", "useradd"):
            with self.subTest(command=command):
                result = self.start(failed_command=command)
                self.assertEqual(result.returncode, 1)
                self.assertNotIn("apache2-foreground", result.stdout)
