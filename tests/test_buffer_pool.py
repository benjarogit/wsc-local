import sys
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "workbench"), str(ROOT / "scripts")]
import cli
import host_system


class BufferPoolTests(unittest.TestCase):
    def _isolated(self, temp: str):
        root = Path(temp)
        return (
            patch.object(cli, "PROJECTS", root / "projects"),
            patch.object(cli, "SECRETS", root / "secrets"),
            patch.object(cli, "DATA", root),
            patch.object(cli, "port_taken", return_value=False),
        )

    def test_default_compose_keeps_the_image_default(self):
        with tempfile.TemporaryDirectory() as temp:
            with self._isolated(temp)[0], self._isolated(temp)[1], self._isolated(temp)[2], self._isolated(temp)[3]:
                cli.create_project(cli.parser().parse_args(["create", "pool"]))
                cfg, root, _ = cli.read_project("pool")
                self.assertEqual(128, cli.buffer_pool_mib(cfg))
                self.assertNotIn("innodb-buffer-pool-size", (root / "compose.yaml").read_text(encoding="utf-8"))

    def test_optional_size_is_passed_to_the_database(self):
        with tempfile.TemporaryDirectory() as temp:
            with self._isolated(temp)[0], self._isolated(temp)[1], self._isolated(temp)[2], self._isolated(temp)[3]:
                cli.create_project(cli.parser().parse_args(["create", "pool", "--buffer-pool", "256"]))
                _, root, _ = cli.read_project("pool")
                self.assertIn('command: ["--innodb-buffer-pool-size=256M"]', (root / "compose.yaml").read_text(encoding="utf-8"))

    def test_invalid_size_is_rejected(self):
        with self.assertRaises(SystemExit):
            cli.parser().parse_args(["buffer-pool", "pool", "64"])
        with self.assertRaises(ValueError):
            cli.buffer_pool_mib({"buffer_pool_mib": "1G"})

    def test_stopped_database_is_not_started(self):
        with tempfile.TemporaryDirectory() as temp:
            with self._isolated(temp)[0], self._isolated(temp)[1], self._isolated(temp)[2], self._isolated(temp)[3]:
                cli.create_project(cli.parser().parse_args(["create", "pool"]))
                with patch.object(cli, "project_status", return_value={"services": [{"name": "database", "state": "exited"}]}), patch.object(cli, "compose") as compose:
                    message = cli.set_buffer_pool("pool", 512)
                compose.assert_not_called()
                cfg, root, _ = cli.read_project("pool")
                self.assertEqual(512, cfg["buffer_pool_mib"])
                self.assertIn("innodb-buffer-pool-size=512M", (root / "compose.yaml").read_text(encoding="utf-8"))
                self.assertIn("nicht gestartet", message)

    def test_failed_recreate_restores_the_previous_size(self):
        with tempfile.TemporaryDirectory() as temp:
            with self._isolated(temp)[0], self._isolated(temp)[1], self._isolated(temp)[2], self._isolated(temp)[3]:
                cli.create_project(cli.parser().parse_args(["create", "pool"]))
                failed = CompletedProcess(args=[], returncode=1, stdout="", stderr="Datenbankstart fehlgeschlagen")
                with patch.object(cli, "project_status", return_value={"services": [{"name": "database", "state": "running"}]}), patch.object(cli, "compose", return_value=failed):
                    with self.assertRaises(RuntimeError):
                        cli.set_buffer_pool("pool", 256)
                cfg, root, _ = cli.read_project("pool")
                self.assertEqual(128, cli.buffer_pool_mib(cfg))
                self.assertNotIn("innodb-buffer-pool-size", (root / "compose.yaml").read_text(encoding="utf-8"))

    def test_system_check_hints_without_blocking_the_device(self):
        with tempfile.TemporaryDirectory() as temp:
            with self._isolated(temp)[0], self._isolated(temp)[1], self._isolated(temp)[2], self._isolated(temp)[3]:
                cli.create_project(cli.parser().parse_args(["create", "pool"]))
                check = cli.buffer_pool_system_check()
                self.assertEqual("hint", check["status"])
                self.assertTrue(check["help"])
                with patch.object(cli, "project_status", return_value={"services": []}):
                    cli.set_buffer_pool("pool", 256)
                self.assertEqual("ready", cli.buffer_pool_system_check()["status"])
        extra = lambda: [{"id": "buffer-pool", "label": "Datenbank-Buffer-Pool", "status": "hint", "detail": "Hinweis", "help": "Hilfe"}]
        host_system.EXTRA_CHECKS.append(extra)
        try:
            with patch.object(host_system, "detect_host", return_value={"kind": "linux", "label": "Linux", "architecture": "x64", "supported": True}), patch.object(host_system.shutil, "which", return_value="/usr/bin/docker"), patch.object(host_system, "_run", return_value=(True, "linux|29")), patch.object(host_system, "trust_ready", return_value=True):
                report = host_system.system_report()
            self.assertTrue(report["ready"])
            self.assertIn("hint", [item["status"] for item in report["checks"]])
        finally:
            host_system.EXTRA_CHECKS.remove(extra)


if __name__ == "__main__":
    unittest.main()
