"""Installation language follows the explicit UI choice, otherwise the CLI locale."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workbench'))
import cli

class InstallationLanguageTests(unittest.TestCase):
    def test_explicit_language_wins_over_host_locale(self):
        self.assertEqual(cli.resolve_install_language('en',{'LC_ALL':'de_DE.UTF-8'}),'en')
        self.assertEqual(cli.resolve_install_language('de',{'LC_ALL':'en_US.UTF-8'}),'de')
        for value in ('fr','EN','en_US','',None):
            if value is not None:
                with self.assertRaises(ValueError):cli.resolve_install_language(value)

    def test_system_locale_precedence_and_default(self):
        for env,expected in [({'LC_ALL':'en_GB.UTF-8','LANG':'de_DE.UTF-8'},'en'),({'LC_MESSAGES':'de_DE','LANG':'en_US'},'de'),({'LANG':'en-US'},'en'),({'LANG':'C.UTF-8'},'de'),({'LANG':'fr_FR'},'de')]:
            with self.subTest(env=env):self.assertEqual(cli.resolve_install_language(env=env),expected)
        with patch.object(cli.locale,'getlocale',return_value=('en_US','UTF-8')):self.assertEqual(cli.resolve_install_language(env={}),'en')
        with patch.object(cli.locale,'getlocale',return_value=(None,None)):self.assertEqual(cli.resolve_install_language(env={}),'de')

    def test_selected_language_is_saved_before_installer_runs_and_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'site').mkdir();cfg={'name':'example'}
            def install(name):
                self.assertEqual(json.loads((root/'wsc-local.json').read_text())['installation_language'],'en')
                return 'installed'
            with patch.object(cli,'read_project',return_value=(cfg,root,root/'secret')),patch.object(cli,'_install_woltlab',side_effect=install):
                self.assertEqual(cli.install_woltlab('example','en'),'installed')
                with patch.dict(cli.os.environ,{'LC_ALL':'de_DE.UTF-8'}):self.assertEqual(cli.install_woltlab('example'),'installed')
            self.assertEqual(cfg['installation_language'],'en')

    def test_invalid_language_does_not_change_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'site').mkdir()
            with patch.object(cli,'read_project',return_value=({},root,root/'secret')),patch.object(cli,'_install_woltlab') as install:
                with self.assertRaises(ValueError):cli.install_woltlab('example','fr')
                install.assert_not_called()
            self.assertFalse((root/'wsc-local.json').exists());self.assertFalse((root/'installation-state.json').exists())

    def test_rendered_site_and_admin_language_must_match(self):
        for page,expected in [('<html dir="ltr" lang="en">','en'),("<HTML lang='de-DE'>",'de')]:cli.verify_page_language(page,expected)
        for page in ('<html lang="de">','<html>','<html data-lang="en">'):
            with self.assertRaises(RuntimeError):cli.verify_page_language(page,'en')

    def test_cli_accepts_explicit_language(self):
        self.assertEqual(cli.parser().parse_args(['install','example','--language','en']).language,'en')
        self.assertIsNone(cli.parser().parse_args(['install','example']).language)

if __name__=='__main__':unittest.main()
