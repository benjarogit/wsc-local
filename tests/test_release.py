import importlib.util
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('release_builder',ROOT/'scripts/release.py');release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'repo';self.root.mkdir()
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        (self.root/'VERSION').write_text('1.2.0\n');(self.root/'wsc').write_text('entry point')
        (self.root/'CHANGELOG.md').write_text('# Changes\n\n## 1.2.0 – 2026-10-28\n\nNew update feature\n\n## 1.1.0\nOld\n')
        subprocess.run(['git','-C',str(self.root),'add','.'],check=True)
        subprocess.run(['git','-C',str(self.root),'-c','user.name=Test','-c','user.email=test@example.test','commit','-qm','release'],check=True)
    def tearDown(self):self.temp.cleanup()
    def test_package_uses_committed_source_and_includes_verified_manifest(self):
        (self.root/'wsc').write_text('uncommitted secret');(self.root/'.env').write_text('PASSWORD=private')
        package=release.build(self.root,'HEAD','v1.2.0',Path(self.temp.name)/'dist')
        with zipfile.ZipFile(package['zip']) as z:
            self.assertEqual(z.read('wsc-local-1.2.0/wsc'),b'entry point')
            self.assertNotIn('wsc-local-1.2.0/.env',z.namelist())
            manifest=json.loads(z.read('wsc-local-1.2.0/.wsc-local-release.json'));self.assertEqual(manifest['version'],'1.2.0')
        self.assertIn('New update feature',package['notes'].read_text());self.assertNotIn('Old',package['notes'].read_text())
    def test_mismatched_or_unstable_tag_cannot_be_packaged(self):
        for tag in ('v1.3.0','v1.2.0-beta','1.2.0','v1.2.0;echo'):
            with self.subTest(tag=tag),self.assertRaises(ValueError):release.build(self.root,'HEAD',tag,Path(self.temp.name)/'dist')

if __name__=='__main__':unittest.main()
