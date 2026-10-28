import argparse
import hashlib
import io
import tarfile
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'workbench'), str(ROOT / 'scripts')]
import host_system
import launcher
import cli


class PlatformTests(unittest.TestCase):
    def test_linux_macos_and_wsl2_are_supported(self):
        cases = [('Linux','6.1','linux'),('Darwin','24.0','macos'),('Linux','6.6-microsoft-standard-WSL2','wsl2')]
        for system, release, kind in cases:
            with self.subTest(kind=kind):
                info = host_system.detect_host(system, release, {})
                self.assertTrue(info['supported'])
                self.assertEqual(kind, info['kind'])

    def test_wsl1_and_native_windows_require_wsl2(self):
        for system, release in [('Windows','10'),('Linux','4.4-Microsoft')]:
            self.assertFalse(host_system.detect_host(system, release, {})['supported'])

    def test_windows_ca_path_is_passed_as_one_argument(self):
        calls = []
        def run(command, timeout=8):
            calls.append(command)
            return (True, r'C:\Users\Test Person\AppData\Local\mkcert') if command[0] == 'mkcert.exe' else (True, '/mnt/c/Users/Test Person/AppData/Local/mkcert')
        with patch.object(host_system, 'detect_host', return_value={'kind':'wsl2'}), patch.object(host_system.shutil, 'which', return_value='mkcert.exe'), patch.object(host_system, '_run', side_effect=run):
            self.assertEqual(Path('/mnt/c/Users/Test Person/AppData/Local/mkcert'), host_system.certificate_root())
        self.assertEqual(3, len(calls[1]))
        self.assertIn('Test Person', calls[1][2])

    def test_changed_ca_requires_new_trust_step(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'rootCA.pem').write_bytes(b'first')
            marker = root/'trust.json'; marker.write_text(json.dumps({'sha256':hashlib.sha256(b'first').hexdigest()}))
            with patch.object(host_system,'certificate_root',return_value=root), patch.object(host_system,'TRUST_FILE',marker):
                self.assertTrue(host_system.trust_ready())
                (root/'rootCA.pem').write_bytes(b'changed')
                self.assertFalse(host_system.trust_ready())

    def test_launcher_refuses_other_workspace(self):
        with patch.object(launcher,'request') as request:
            with self.assertRaises(RuntimeError):
                launcher.stop_older_server('http://127.0.0.1:9099',{'workspace_id':'someone-else'})
            request.assert_not_called()

    def test_launcher_preserves_running_install(self):
        with patch.object(launcher,'request') as request:
            with self.assertRaises(RuntimeError):
                launcher.stop_older_server('http://127.0.0.1:9099',{'active_jobs':1})
            request.assert_not_called()

    def test_missing_dependencies_are_actionable(self):
        with patch.object(host_system,'detect_host',return_value={'kind':'macos','label':'macOS','architecture':'arm64','supported':True}), patch.object(host_system.shutil,'which',return_value=None):
            report = host_system.system_report()
        self.assertFalse(report['ready'])
        self.assertTrue(all(check['help'] for check in report['checks'] if check['status']=='missing'))


class ProjectPortabilityTests(unittest.TestCase):
    def test_project_stop_and_remove_include_optional_services(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch.object(cli,'PROJECTS',root/'projects'), patch.object(cli,'SECRETS',root/'secrets'), patch.object(cli,'DATA',root), patch.object(cli,'port_taken',return_value=False):
                cli.create_project(cli.parser().parse_args(['create','cleanup']))
                with patch.object(cli.subprocess,'run') as run:
                    for command in ('stop', 'down'):
                        cli.compose('cleanup',command)
                        arguments=run.call_args.args[0]
                        self.assertEqual(['--profile','*',command],arguments[-3:])

    def test_shared_profile_recreates_with_new_secrets_and_reserved_ports(self):
        with tempfile.TemporaryDirectory(prefix='wsc profiles ') as temp:
            root=Path(temp)/('Projekt mit # und -' if sys.platform=='win32' else 'Projekt mit # und :'); root.mkdir()
            with patch.object(cli,'PROJECTS',root/'projects'), patch.object(cli,'SECRETS',root/'secrets'), patch.object(cli,'DATA',root), patch.object(cli,'port_taken',return_value=False):
                args=cli.parser().parse_args(['create','first'])
                cli.create_project(args)
                cfg,first,secret=cli.read_project('first')
                shared={key:cfg[key] for key in ('schema','suite_version','php_version','webserver','database')}
                profile=root/'team-profile.json';profile.write_text(json.dumps(shared))
                cli.create_project(cli.parser().parse_args(['create','second','--profile',str(profile)]))
                other,second,other_secret=cli.read_project('second')
                self.assertFalse({cfg['http_port'],cfg['https_port'],cfg['mail_port']} & {other['http_port'],other['https_port'],other['mail_port']})
                self.assertNotEqual(cli.parse_env(secret)['MYSQL_PASSWORD'],cli.parse_env(other_secret)['MYSQL_PASSWORD'])
                document=cli.compose_text(first,cfg)
                self.assertIn('source: '+json.dumps(str(first/'site').replace('\\','/')),document)
                self.assertNotIn('MYSQL_PASSWORD',json.dumps(shared))
                if sys.platform != 'win32' and shutil.which('docker'):
                    result=subprocess.run(['docker','compose','--project-directory',str(first),'--env-file',str(secret),'-f',str(first/'compose.yaml'),'config','--quiet'],capture_output=True,text=True)
                    self.assertEqual(0,result.returncode,result.stderr)


class ImportProfileTests(unittest.TestCase):
    def test_development_export_keeps_php_and_allows_explicit_import(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);archive=root/'project.tar.gz'
            cfg={'suite_version':'6.3','php_version':'8.5','database':'mariadb','webserver':'nginx-php-fpm'}
            payload=json.dumps(cfg).encode()
            with tarfile.open(archive,'w:gz') as bundle:
                info=tarfile.TarInfo('wsc-local.json');info.size=len(payload);bundle.addfile(info,io.BytesIO(payload))
            with patch.object(cli,'PROJECTS',root/'projects'),patch.object(cli,'SECRETS',root/'secrets'),patch.object(cli,'DATA',root),patch.object(cli,'port_taken',return_value=False),patch.object(cli,'restore',return_value='restored') as restore:
                self.assertEqual('restored',cli.import_bundle(archive,'imported'))
                config,_,_=cli.read_project('imported')
                self.assertEqual('6.3',config['suite_version'])
                self.assertEqual('8.5',config['php_version'])
                restore.assert_called_once_with('imported',archive.resolve(),yes=True)


class ExportTests(unittest.TestCase):
    def test_export_copy_has_placeholders_and_source_is_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            site=Path(temp);config=site/'config.inc.php'
            original="<?php\n$dbHost='database';\n$dbPort=0;\n$dbUser='wsc';\n$dbPassword='local-secret';\n$dbName='woltlab';\n"
            config.write_text(original)
            cli.redact_export_database_config(site)
            result=config.read_text()
            self.assertNotIn('local-secret',result)
            self.assertIn("$dbPassword = 'CHANGE_ME';",result)

    def test_unrecognized_export_config_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            site=Path(temp);config=site/'config.inc.php';original="<?php require 'private.php';"
            config.write_text(original)
            with self.assertRaises(ValueError):cli.redact_export_database_config(site)
            self.assertEqual(original,config.read_text())


if __name__ == '__main__':
    unittest.main()
