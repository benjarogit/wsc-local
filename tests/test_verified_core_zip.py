import hashlib
import io
import json
import sys
import tarfile
import tempfile
import unittest
import zipfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workbench"))
import cli


class VerifiedCoreZipTests(unittest.TestCase):
    source = "https://example.org/vendor/suite"
    commit = "a" * 40

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.data = Path(folder.name)
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(cli, "DATA", self.data))
        stack.enter_context(patch.object(cli, "PROJECTS", self.data / "projects"))
        stack.enter_context(patch.object(cli, "SECRETS", self.data / "secrets"))
        stack.enter_context(patch.object(cli, "port_taken", return_value=False))
        cli.create_project(cli.parser().parse_args(["create", "verified", "--suite", "6.3", "--experimental"]))
        _, self.root, _ = cli.read_project("verified")
        self.site = self.root / "site"
        self.original_config = (self.root / "wsc-local.json").read_bytes()
        self.original_site = {p.name: p.read_bytes() for p in self.site.iterdir()}
        self.source_zip = self.data / "fixture.zip"

    def archive(self, *, package=True, extra=False):
        bundle = io.BytesIO()
        with tarfile.open(fileobj=bundle, mode="w:gz") as setup:
            name = "install/packages/com.woltlab.wcf.tar" if package else "missing"
            member = tarfile.TarInfo(name)
            member.size = 7
            setup.addfile(member, io.BytesIO(b"fixture"))
        with zipfile.ZipFile(self.source_zip, "w") as archive:
            archive.writestr("install.php", "<?php /* install fixture */")
            archive.writestr("test.php", "<?php /* test fixture */")
            archive.writestr("WCFSetup.tar.gz", bundle.getvalue())
            if extra:
                archive.writestr("extra.txt", "unexpected")
        return hashlib.sha256(self.source_zip.read_bytes()).hexdigest()

    def assert_project_untouched(self):
        self.assertEqual(self.original_config, (self.root / "wsc-local.json").read_bytes())
        self.assertEqual(self.original_site, {p.name: p.read_bytes() for p in self.site.iterdir()})

    def test_import_pins_archive_path_hash_and_source(self):
        checksum = self.archive()
        cli.import_core_zip("verified", self.source_zip, checksum.upper(), self.source, self.commit.upper())
        cfg, _, _ = cli.read_project("verified")
        label = cfg["core_version"]
        cache = self.data / "downloads" / f"{label}-core.zip"
        self.assertEqual(self.source_zip.read_bytes(), cache.read_bytes())
        self.assertEqual(checksum, cfg["core_sha256"])
        self.assertEqual(self.source, cfg["core_source"])
        self.assertEqual(self.commit, cfg["core_source_commit"])
        self.assertTrue((self.site / "install.php").is_file())
        self.assertFalse((self.site / "global.php").exists())
        self.assertEqual(self.original_site, {n: (self.site / n).read_bytes() for n in self.original_site})
        self.assertEqual([cache], list(cache.parent.glob(f"{label}-*.zip")))

    def test_bad_digest_fails_before_unpacking(self):
        self.archive()
        with patch.object(cli, "install_zip") as unpack:
            with self.assertRaisesRegex(ValueError, "SHA-256-Prüfung"):
                cli.import_core_zip("verified", self.source_zip, "b" * 64, self.source, self.commit)
            unpack.assert_not_called()
        self.assert_project_untouched()
        self.assertEqual([], list((self.data / "downloads").iterdir()))

    def test_ordinary_zip_cannot_invalidate_verified_project_provenance(self):
        checksum = self.archive()
        cli.import_core_zip("verified", self.source_zip, checksum, self.source, self.commit)
        expected = {p.name: p.read_bytes() for p in self.site.iterdir()}
        self.archive(package=False)
        with self.assertRaisesRegex(ValueError, "nicht mit einem anderen ZIP überschreiben"):
            cli.install_zip(self.source_zip, self.site)
        self.assertEqual(expected, {p.name: p.read_bytes() for p in self.site.iterdir()})

    def test_rejects_missing_nested_core_package(self):
        checksum = self.archive(package=False)
        with self.assertRaisesRegex(ValueError, "kein eindeutiges reguläres WoltLab-Core-Paket"):
            cli.import_core_zip("verified", self.source_zip, checksum, self.source, self.commit)
        self.assert_project_untouched()

    def test_rejects_extra_zip_members_before_unpacking(self):
        checksum = self.archive(extra=True)
        with patch.object(cli, "install_zip") as unpack:
            with self.assertRaisesRegex(ValueError, "darf nur"):
                cli.import_core_zip("verified", self.source_zip, checksum, self.source, self.commit)
            unpack.assert_not_called()
        self.assert_project_untouched()

    def test_never_overwrites_site_with_existing_files(self):
        checksum = self.archive()
        existing = self.site / "global.php"
        existing.write_bytes(b"existing fixture")
        with self.assertRaisesRegex(ValueError, "neues Projekt"):
            cli.import_core_zip("verified", self.source_zip, checksum, self.source, self.commit)
        self.assertEqual(b"existing fixture", existing.read_bytes())
        self.assertFalse((self.site / "install.php").exists())

    def test_metadata_publication_failure_rolls_back_installer_files(self):
        checksum = self.archive()
        replace = Path.replace

        def fail_metadata(path, target):
            if path.name == "wsc-local.json":
                raise OSError("fixture failure")
            return replace(path, target)

        with patch.object(Path, "replace", fail_metadata):
            with self.assertRaisesRegex(OSError, "fixture failure"):
                cli.import_core_zip("verified", self.source_zip, checksum, self.source, self.commit)
        self.assert_project_untouched()
        cli.import_core_zip("verified", self.source_zip, checksum, self.source, self.commit)
        self.assertEqual(checksum, json.loads((self.root / "wsc-local.json").read_bytes())["core_sha256"])

    def test_suite_installation_does_not_race_zip_publication(self):
        with cli.project_write_lock(self.root / cli.CORE_ZIP_IMPORT_LOCK, "fixture"):
            with patch.object(cli, "_prepare_woltlab_installation") as prepare:
                with self.assertRaisesRegex(RuntimeError, "Core-Import"):
                    cli.install_woltlab("verified")
                prepare.assert_not_called()
        self.assert_project_untouched()

    def test_download_refuses_verified_project_before_network_access(self):
        checksum = self.archive()
        cli.import_core_zip("verified", self.source_zip, checksum, self.source, self.commit)
        with patch.object(cli.urllib.request, "urlopen") as request:
            with self.assertRaisesRegex(ValueError, "nicht mit einem anderen ZIP überschreiben"):
                cli.download_core_project("verified", "6.3")
            request.assert_not_called()

    def test_interrupted_publication_resumes_only_the_matching_archive(self):
        checksum = self.archive()
        replace = Path.replace

        def interrupt_after_first(path, target):
            if Path(target) == self.site / "test.php":
                raise KeyboardInterrupt
            return replace(path, target)

        with patch.object(Path, "replace", interrupt_after_first), self.assertRaises(KeyboardInterrupt):
            cli.import_core_zip("verified", self.source_zip, checksum, self.source, self.commit)
        self.assertTrue((self.root / cli.CORE_ZIP_IMPORT_PENDING).is_file())
        self.assertTrue((self.site / "WCFSetup.tar.gz").is_file())
        self.assertFalse((self.site / "install.php").exists())
        with self.assertRaisesRegex(ValueError, "unterbrochen"):
            cli.install_woltlab("verified")
        with self.assertRaisesRegex(ValueError, "unterbrochen"):
            cli.action("verified", "start", "up", "-d")
        with self.assertRaisesRegex(ValueError, "unterbrochen"):
            cli.import_core_zip("verified", self.source_zip, checksum, self.source, "b" * 40)
        cli.import_core_zip("verified", self.source_zip, checksum, self.source, self.commit)
        self.assertFalse((self.root / cli.CORE_ZIP_IMPORT_PENDING).exists())
        self.assertTrue((self.site / "install.php").is_file())
