"""Regression coverage for local login boundaries and OS terminal installers."""
import http.cookiejar
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workbench'))
import acp_login
import host_install

class LoginTests(unittest.TestCase):
    def test_remote_origins_and_php_interpolation_are_rejected(self):
        for url in ('https://example.com', 'https://local.test', 'https://localhost.evil.test','https://user@localhost','file:///localhost','https://$bad.localhost','https://bad".localhost'):
            with self.subTest(url=url),self.assertRaises(ValueError): acp_login.local_origin(url)
        self.assertEqual(acp_login.local_origin('https://project.localhost:8081'),('https','project.localhost',8081))
        redirects=acp_login.LocalRedirects(('https','project.localhost',8081))
        with self.assertRaises(ValueError):redirects.redirect_request(None,None,302,'',{},'https://other.localhost:8081/acp/')

    def test_bridge_uses_hash_and_expiry_without_admin_password(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'site').mkdir();secret=root/'secret';secret.write_text('WSC_ADMIN_PASSWORD=never-embed-this\n')
            jar=http.cookiejar.CookieJar();jar.set_cookie(http.cookiejar.Cookie(0,'wsc_cookieHash','session-secret',None,False,'project.localhost',False,False,'/',True,True,None,True,None,None,{'HttpOnly':None,'SameSite':'Lax'},False))
            with patch.object(acp_login,'read_project',return_value=({'url':'https://project.localhost:8081'},root,secret)),patch.object(acp_login,'project_status',return_value={'site_ready':True,'running':True}),patch.object(acp_login,'authenticate',return_value=jar),patch.object(acp_login.threading,'Timer') as timer:
                data=acp_login.prepare('project','browser-agent')
            script=next((root/'site').glob('wsc-local-acp-*.php')).read_text()
            self.assertNotIn('never-embed-this',script);self.assertNotIn(data['token'],script)
            self.assertIn("$_SERVER['REQUEST_METHOD']",script);self.assertIn('hash_equals',script);self.assertIn('unlink(__FILE__)',script);self.assertIn('time() >',script)
            self.assertNotIn('session-secret',script);self.assertEqual(data['expires_in'],60)
            timer.return_value.start.assert_called_once()

class InstallerTests(unittest.TestCase):
    def test_linux_arguments_preserve_space_and_metacharacters(self):
        root=Path('/tmp/a project $safe');state=root/'var/state'
        with patch.object(host_install.shutil,'which',side_effect=lambda executable:'/bin/xterm' if executable=='xterm' else None):
            command=host_install.terminal_command(root,state,'linux')
        self.assertEqual(command,['xterm','-e','bash',str(root/'scripts/install-host.sh'),'--status',str(state),'--pause'])
    def test_macos_does_not_interpolate_shell_or_applescript_paths(self):
        command=host_install.terminal_command(Path('/tmp/Müller " quote $name'),Path('/tmp/status'),'macos')
        self.assertEqual(command[0],'osascript');self.assertIn('\\"',command[2]);self.assertIn("'",command[2]);self.assertIn('Müller',command[2])
    def test_wsl_uses_explicit_distro_and_encoded_command(self):
        with patch.dict(host_install.os.environ,{'WSL_DISTRO_NAME':'Ubuntu Test'}):
            command=host_install.terminal_command(Path('/mnt/c/Project name'),Path('/tmp/status'),'wsl2')
        self.assertEqual(command[0],'powershell.exe');self.assertIn('-EncodedCommand',command[-1]);self.assertNotIn('Project name',command[-1])
    def test_unsupported_hosts_never_offer_install(self):
        for kind in ('unsupported','windows','wsl1'):
            self.assertFalse(host_install.installation_plan({'kind':kind})['supported'])
    def test_no_terminal_has_a_runnable_fallback(self):
        with patch.object(host_install.shutil,'which',return_value=None),self.assertRaisesRegex(RuntimeError,'setup.sh'):
            host_install.terminal_command(Path('/tmp/repo'),Path('/tmp/status'),'linux')
    def test_terminal_launch_does_not_claim_installer_success(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(host_install,'installation_plan',return_value={'supported':True,'command':'setup'}),patch.object(host_install,'terminal_command',return_value=['terminal']),patch.object(host_install.subprocess,'Popen') as process:
            process.return_value.poll.return_value=0
            with self.assertRaisesRegex(RuntimeError,'keinen Abschluss'):
                host_install.launch_installation(Path(directory),timeout=0)
            self.assertEqual(list((Path(directory)/'var/host-setup').iterdir()),[])

if __name__=='__main__':unittest.main()
