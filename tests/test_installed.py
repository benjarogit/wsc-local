"""Installed package and style lists stay read-only."""
import json
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workbench"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cli
import panel_server as panel


XML = """<?xml version="1.0"?>
<resultset>
  <row>
    <field name="kind">package</field>
    <field name="identifier">com.woltlab.wcf</field>
    <field name="title">WoltLab Suite Core</field>
    <field name="version">6.2.8</field>
    <field name="flag_a">1</field>
    <field name="extra">WoltLab GmbH</field>
    <field name="flag_b">0</field>
  </row>
  <row>
    <field name="kind">style</field>
    <field name="identifier">com.example.style</field>
    <field name="title">Blau &amp; Meer</field>
    <field name="version">1.0.0</field>
    <field name="flag_a">0</field>
    <field name="extra"></field>
    <field name="flag_b">1</field>
  </row>
</resultset>
"""


class InstalledListTests(unittest.TestCase):
    def test_rows_keep_application_and_style_state(self):
        rows = cli.parse_installed_rows(XML)
        self.assertEqual(rows["packages"][0]["name"], "WoltLab Suite Core")
        self.assertTrue(rows["packages"][0]["application"])
        self.assertEqual(rows["styles"][0]["name"], "Blau & Meer")
        self.assertTrue(rows["styles"][0]["disabled"])
        self.assertFalse(rows["styles"][0]["default"])
        text = cli.format_installed({"ready": True, "packages": rows["packages"], "styles": rows["styles"]})
        self.assertIn("Anwendung", text)
        self.assertIn("Deaktiviert", text)
        self.assertIn("Kein aktiver Stil.", text)

    def test_prefix_must_be_a_woltlab_table_prefix(self):
        with self.assertRaises(ValueError):
            cli._installed_sql("wcf1_;DROP TABLE ")

    def test_stopped_database_is_not_queried(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "site").mkdir()
            (root / "site" / "global.php").write_text("<?php\n", encoding="utf-8")
            with patch.object(cli, "read_project", return_value=({"database": "mariadb"}, root, root / "secret")), \
                 patch.object(cli, "project_status", return_value={"services": [{"name": "database", "state": "exited"}]}), \
                 patch.object(cli, "compose") as compose:
                data = cli.installed_content("demo")
        self.assertEqual("database_stopped", data["reason"])
        compose.assert_not_called()

    def test_running_database_uses_the_configured_prefix(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "site").mkdir()
            (root / "site" / "global.php").write_text("<?php\n", encoding="utf-8")
            (root / "site" / "config.inc.php").write_text("define('WCF_N', 1);\n", encoding="utf-8")
            seen = []

            def compose(name, *args, **kwargs):
                seen.append(args[-1])
                return subprocess.CompletedProcess(args, 0, XML, "")

            with patch.object(cli, "read_project", return_value=({"database": "mariadb"}, root, root / "secret")), \
                 patch.object(cli, "project_status", return_value={"services": [{"name": "database", "state": "running"}]}), \
                 patch.object(cli, "compose", side_effect=compose):
                data = cli.installed_content("demo")
        self.assertTrue(data["ready"])
        self.assertIn("wcf1_package", seen[0])
        self.assertNotIn("DROP", seen[0])
        self.assertEqual("com.woltlab.wcf", data["packages"][0]["identifier"])


class InstalledApiTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), panel.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.patch = patch.object(panel, "installed_content", return_value={"ready": True, "reason": "", "packages": [], "styles": []})
        self.installed = self.patch.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.patch.stop()

    def test_get_returns_the_list_for_a_known_project(self):
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.server.server_port}/api/instances/demo/installed",
            headers={"X-Panel-Token": panel.TOKEN},
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            body = json.load(response)
        self.assertEqual(200, response.status)
        self.assertTrue(body["ready"])
        self.installed.assert_called_once_with("demo")


if __name__ == "__main__":
    unittest.main()
