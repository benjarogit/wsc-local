import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path
from subprocess import CompletedProcess
from threading import Event
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workbench"))
import cli


class StandardHttpsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(cli, "PROJECTS", root / "projects"))
        stack.enter_context(patch.object(cli, "SECRETS", root / "secrets"))
        self.port_taken = stack.enter_context(patch.object(cli, "port_taken", return_value=False))

    def create(self, name, *args):
        cli.create_project(cli.parser().parse_args(["create", name, *args]))
        return cli.read_project(name)

    def test_standard_port_is_reserved_and_only_bound_to_loopback(self):
        old_cfg, old_root, _ = self.create("legacy-ports", "--port", "8100")
        previous = (old_root / "wsc-local.json").read_bytes()
        self.port_taken.side_effect = lambda port: port == 8081
        cfg, root, env = self.create("patchless", "--standard-https", "--port", "8080", "--webserver", "apache")
        self.assertEqual((8080, 443, 8082), (cfg["http_port"], cfg["https_port"], cfg["mail_port"]))
        self.assertEqual("wsc-patchless", cfg["project"])
        self.assertEqual(8101, old_cfg["https_port"])
        self.assertEqual(previous, (old_root / "wsc-local.json").read_bytes())
        self.assertEqual("443", cli.parse_env(env)["HTTPS_PORT"])
        self.assertIn('"127.0.0.1:${HTTPS_PORT}:443"', (root / "compose.yaml").read_text())
        self.assertIn("wsc-patchless_net", (root / "compose.yaml").read_text())
        with self.assertRaisesRegex(ValueError, "443"):
            self.create("second", "--standard-https")
        self.assertFalse((cli.PROJECTS / "second").exists())

    def test_occupied_port_leaves_no_project_files(self):
        self.port_taken.side_effect = lambda port: port == 443
        with self.assertRaisesRegex(ValueError, "443"):
            self.create("taken", "--standard-https")
        cfg, _, _ = self.create("fallback")
        self.assertEqual(8081, cfg["https_port"])
        self.assertFalse((cli.PROJECTS / "taken").exists())
        self.assertFalse((cli.SECRETS / "taken.env").exists())

    def test_concurrent_project_creation_cannot_persist_two_standard_ports(self):
        checking = Event()
        finish = Event()

        def wait_during_reservation(port):
            if port == 443:
                checking.set()
                if not finish.wait(5):
                    raise RuntimeError("test reservation timed out")
            return False

        self.port_taken.side_effect = wait_during_reservation
        with ThreadPoolExecutor(max_workers=1) as executor:
            first = executor.submit(self.create, "first", "--standard-https")
            try:
                self.assertTrue(checking.wait(5))
                with self.assertRaisesRegex(RuntimeError, "Reservierung"):
                    self.create("second", "--standard-https")
            finally:
                finish.set()
            self.assertEqual(443, first.result(timeout=5)[0]["https_port"])
        with self.assertRaisesRegex(ValueError, "443"):
            self.create("second", "--standard-https")
        self.assertFalse((cli.PROJECTS / "second").exists())

    def test_tls_uses_canonical_host_for_both_web_servers(self):
        def fake_mkcert(args, **kwargs):
            if "-cert-file" in args:
                Path(args[args.index("-cert-file") + 1]).write_bytes(b"fixture certificate")
                Path(args[args.index("-key-file") + 1]).write_bytes(b"fixture key")
            return CompletedProcess(args, 0, "", "")

        with patch.object(cli.shutil, "which", return_value="mkcert"), patch.object(cli.subprocess, "run", side_effect=fake_mkcert), patch.object(cli, "project_status", return_value={"running": False}):
            for name, webserver, args, expected in (
                ("apache-test", "apache", ["--standard-https"], "https://apache-test.localhost"),
                ("nginx-test", "nginx-php-fpm", [], "https://nginx-test.localhost:8084"),
            ):
                with self.subTest(webserver=webserver):
                    cfg, root, _ = self.create(name, "--webserver", webserver, *args)
                    cli.local_tls(name, True, confirmed=True)
                    cfg, _, _ = cli.read_project(name)
                    self.assertEqual(expected, cfg["url"])
                    self.assertEqual(f"{name}.localhost", cfg["domain"])
                    vhost = "apache.conf" if webserver == "apache" else "nginx.conf"
                    self.assertIn(cfg["domain"], (root / "config" / vhost).read_text())

    def test_installer_post_uses_selected_authority(self):
        for name, args in (("setup-standard", ["--standard-https"]), ("setup-high", [])):
            with self.subTest(name=name):
                cfg, root, _ = self.create(name, "--suite", "6.3", "--experimental", *args)
                domain = f"{name}.localhost"
                authority = domain if args else f"{domain}:{cfg['https_port']}"
                cfg.update(url=f"https://{authority}", domain=domain, tls_enabled=True)
                (root / "wsc-local.json").write_text(json.dumps(cfg))
                (root / "site/install.php").touch()
                opener = MagicMock()
                opener.open.return_value.__enter__.return_value.read.side_effect = [
                    b"{}", b'{"host_ok":true,"cookie_ok":true,"https_ok":true}', b'{"unlocked":true}',
                    b'<form><input type="hidden" name="step" value="showSystemRequirements"></form>',
                ]
                with patch.object(cli, "action"), patch.object(cli.urllib.request, "build_opener", return_value=opener), patch.object(cli, "_post_setup_step", side_effect=RuntimeError("fixture stop")) as post:
                    with self.assertRaisesRegex(RuntimeError, "fixture stop"):
                        cli._install_woltlab(name)
                self.assertEqual(f"https://{authority}/install.php", post.call_args.args[1])
                self.assertEqual(authority, post.call_args.kwargs["host_header"])

    def test_standard_port_skips_compatibility_patch(self):
        cfg, root, _ = self.create("unpatched", "--suite", "6.3", "--experimental", "--standard-https")
        cli.apply_local_port_compatibility(root, cfg)
        self.assertNotIn("compatibility_patches", cfg)
        self.assertFalse((root / "config/compatibility").exists())

    def test_bind_failure_preserves_settings_and_does_not_stop_services(self):
        _, root, env = self.create("occupied-later", "--standard-https")
        old_config = (root / "wsc-local.json").read_bytes()
        old_env = env.read_bytes()
        message = "Bind for 127.0.0.1:443 failed: port is already allocated"
        with patch.object(cli, "compose", return_value=CompletedProcess([], 1, "", message)) as compose:
            with self.assertRaisesRegex(RuntimeError, "Port 443"):
                cli.action("occupied-later", "start", "up", "-d")
            compose.assert_called_once_with("occupied-later", "up", "-d")
        self.assertEqual(old_env, env.read_bytes())
        self.assertEqual(old_config, (root / "wsc-local.json").read_bytes())
