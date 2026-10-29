import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workbench'))
import updater as u


def bundle(files, v='1.2.0', extra=None):
    files={**files,'VERSION':(v+'\n').encode()}
    manifest={'version':v,'files':{name:hashlib.sha256(value).hexdigest() for name,value in files.items()}}
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as z:
        for name,value in {**files,u.MANIFEST:json.dumps(manifest).encode()}.items():
            item=zipfile.ZipInfo('wsc-local-'+v+'/'+name);item.external_attr=0o100644<<16;z.writestr(item,value)
        if extra:extra(z)
    return output.getvalue()

MINIMUM={'wsc':b'old entry\n','workbench/cli.py':b'# old cli\n','workbench/launcher.py':b'# launcher\n','scripts/panel_server.py':b'# server\n'}


def metadata(v='1.2.0'):
    return {'tag_name':'v'+v,'draft':False,'prerelease':False,'body':'Release notes','assets':[{'name':name,'browser_download_url':u.RELEASES+'/download/v'+v+'/'+name} for name in ('wsc-local-'+v+'.zip','wsc-local-'+v+'-SHA256SUMS.txt')]}


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'program';self.root.mkdir()
        self.before={**MINIMUM,'VERSION':b'1.1.0\n','obsolete.txt':b'obsolete'}
        for name,value in self.before.items():
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
        (self.root/u.MANIFEST).write_text(json.dumps({'version':'1.1.0','files':{name:hashlib.sha256(value).hexdigest() for name,value in self.before.items()}}))
        self.new={**MINIMUM,'workbench/cli.py':b'# new cli\n','new.txt':b'new'}
        self.payload=bundle(self.new)
        self.sums=hashlib.sha256(self.payload).hexdigest().encode()+b'  wsc-local-1.2.0.zip\n'
        self.patches=[patch.object(u,'api',return_value=metadata()),patch.object(u,'download',side_effect=lambda url,limit=u.MAX_DOWNLOAD:self.sums if url.endswith('.txt') else self.payload)]
        for item in self.patches:item.start()
    def tearDown(self):
        for item in reversed(self.patches):item.stop()
        self.temp.cleanup()
    def test_pending_restart_and_multiple_dashboards_do_not_lose_recovery_state(self):
        u.write_state(self.root,id='first-update',phase='restarting',backup='keep-this',target='1.2.0')
        with self.assertRaisesRegex(RuntimeError,'nicht abgeschlossen'):u.apply(self.root,'1.2.0')
        self.assertEqual(u.state(self.root)['backup'],'keep-this')
        u.write_state(self.root,phase='done')
        with patch.object(u,'dashboard_instances',return_value=[{'port':9099},{'port':9199}]),self.assertRaisesRegex(RuntimeError,'Mehrere Dashboards'):u.apply(self.root,'1.2.0')
        self.assertEqual(u.current(self.root),'1.1.0')

    def test_local_control_api_does_not_send_credentials_through_proxy(self):
        with patch.object(u.urllib.request,'ProxyHandler',wraps=u.urllib.request.ProxyHandler) as handler,patch.object(u.urllib.request,'build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.read.return_value=b'{"ok":true}'
            self.assertTrue(u.local_api(9099,'/api/test',{'test':True},'private-token')['ok'])
            handler.assert_called_once_with({})

    def test_versions_and_release_urls_are_strict(self):
        for value in ('1.2','1.2.0-rc1','v01.2.0','1.2.0;ls'):
            with self.assertRaises(ValueError):u.version(value)
        for url in ('http://github.com/file','https://github.com.evil.test/file','https://user@github.com/file','https://example.com/file'):
            with self.assertRaises(ValueError):u.trusted_url(url)
        u.trusted_url('https://release-assets.githubusercontent.com/file')
        data=metadata();data['assets'][0]['browser_download_url']='https://github.com/another/repo/file'
        with self.assertRaises(ValueError):u.release_info(data)
    def test_zip_update_preserves_private_and_unknown_files_and_rolls_back(self):
        for name in ('.env','var/panel-token','certs/ca.pem','snapshots/backup','notes.txt'):
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'private')
        result=u.apply(self.root,'1.2.0')
        self.assertEqual(u.current(self.root),'1.2.0');self.assertEqual(u.state(self.root)['phase'],'installed')
        self.assertFalse((self.root/'obsolete.txt').exists());self.assertTrue((self.root/'new.txt').exists())
        u.rollback(self.root)
        self.assertEqual(u.current(self.root),'1.1.0');self.assertEqual((self.root/'obsolete.txt').read_bytes(),b'obsolete')
        self.assertFalse((self.root/'new.txt').exists())
        for name in ('.env','var/panel-token','certs/ca.pem','snapshots/backup','notes.txt'):self.assertEqual((self.root/name).read_bytes(),b'private')
    def test_checksum_mismatch_changes_no_program_files(self):
        self.sums=b'0'*64+b'  wsc-local-1.2.0.zip\n'
        with self.assertRaisesRegex(ValueError,'SHA-256'):u.apply(self.root,'1.2.0')
        self.assertEqual(u.current(self.root),'1.1.0');self.assertFalse((self.root/'new.txt').exists())
    def test_local_modifications_and_new_file_collisions_are_preserved(self):
        (self.root/'wsc').write_bytes(b'my custom version')
        self.assertFalse(u.plan(self.root)['can_apply'])
        with self.assertRaisesRegex(ValueError,'Codeänderungen'):u.apply(self.root,'1.2.0')
        self.assertEqual((self.root/'wsc').read_bytes(),b'my custom version')
        (self.root/'wsc').write_bytes(self.before['wsc']);(self.root/'new.txt').write_bytes(b'my personal note')
        with self.assertRaisesRegex(ValueError,'kollidiert'):u.apply(self.root,'1.2.0')
        self.assertEqual((self.root/'new.txt').read_bytes(),b'my personal note')
    def test_traversal_symlinks_and_protected_paths_are_rejected(self):
        for name in ('../escape','.env','var/panel-token','C:/bad','a/../bad','a\\bad','a//bad'):
            with self.subTest(name=name),self.assertRaises(ValueError):u.unpack_release(bundle({**MINIMUM,name:b'bad'}),'1.2.0')
        def symlink(z):
            info=zipfile.ZipInfo('wsc-local-1.2.0/link');info.external_attr=0o120777<<16;z.writestr(info,b'/tmp/outside')
        with self.assertRaises(ValueError):u.unpack_release(bundle(MINIMUM,extra=symlink),'1.2.0')
    def test_failed_file_install_restores_previous_program(self):
        original=Path.replace;failed=[False]
        def replace(path,target):
            if path.name.startswith('new.txt.update-') and not failed[0]:failed[0]=True;raise OSError('disk error')
            return original(path,target)
        with patch.object(Path,'replace',replace),self.assertRaises(OSError):u.apply(self.root,'1.2.0')
        self.assertEqual(u.current(self.root),'1.1.0');self.assertEqual(u.state(self.root)['phase'],'rolled_back')
        self.assertEqual((self.root/'workbench/cli.py').read_bytes(),MINIMUM['workbench/cli.py'])
    def test_cache_is_bounded_and_network_failure_is_not_reported_current(self):
        first=u.check(self.root);second=u.check(self.root)
        self.assertTrue(first['available']);self.assertEqual(first['checked_at'],second['checked_at']);u.api.assert_called_once()
        with patch.object(u,'api',side_effect=RuntimeError('offline')),self.assertRaisesRegex(RuntimeError,'offline'):u.check(self.root,True)
    def test_no_downgrade_and_exclusive_lock(self):
        (self.root/'var').mkdir();(self.root/'var/update.lock').write_text('running')
        with self.assertRaisesRegex(RuntimeError,'gesperrt'):u.apply(self.root,'1.2.0')
        (self.root/'var/update.lock').unlink()
        with self.assertRaisesRegex(ValueError,'neuer'):u.apply(self.root,'1.0.0')
        self.assertEqual(u.current(self.root),'1.1.0')
    def test_stale_update_lock_from_a_dead_process_is_recovered(self):
        lock=self.root/'var/update.lock';lock.parent.mkdir()
        lock.write_text('99999999\n\n')
        with self.assertRaisesRegex(ValueError,'neuer'):u.apply(self.root,'1.0.0')
        self.assertFalse(lock.exists())
    def test_complete_update_lock_is_kept_while_its_process_is_alive(self):
        lock=self.root/'var/update.lock';lock.parent.mkdir()
        lock.write_text(f'{os.getpid()}\n{u._process_start_time(os.getpid())}\n')
        with self.assertRaisesRegex(RuntimeError,'gesperrt'):u.apply(self.root,'1.2.0')
        self.assertTrue(lock.exists())
    def test_old_incomplete_update_lock_is_recovered_after_a_crash(self):
        lock=self.root/'var/update.lock';lock.parent.mkdir()
        lock.write_text('running')
        old=time.time()-u.LOCK_INCOMPLETE_SECONDS-1
        os.utime(lock,(old,old))
        with self.assertRaisesRegex(ValueError,'neuer'):u.apply(self.root,'1.0.0')
        self.assertFalse(lock.exists())
    def test_missing_free_space_does_not_start_file_replacement(self):
        with patch.object(u.shutil,'disk_usage',return_value=shutil._ntuple_diskusage(1,1,0)),self.assertRaisesRegex(ValueError,'Speicherplatz'):u.apply(self.root,'1.2.0')
        self.assertEqual(u.current(self.root),'1.1.0')
    @unittest.skipUnless(shutil.which('git'),'Git required')
    def test_real_git_fast_forward_and_local_changes_guard(self):
        repository=Path(self.temp.name)/'upstream';repository.mkdir()
        subprocess.run(['git','init','-q',str(repository)],check=True)
        for name,value in self.before.items():
            path=repository/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
        (repository/'.gitignore').write_text('var/\n')
        def commit(message):
            subprocess.run(['git','-C',str(repository),'add','.'],check=True)
            subprocess.run(['git','-C',str(repository),'-c','user.name=Tests','-c','user.email=test@example.test','commit','-qm',message],check=True)
        commit('old');subprocess.run(['git','-C',str(repository),'tag','v1.1.0'],check=True)
        clone=Path(self.temp.name)/'checkout';subprocess.run(['git','clone','-q',str(repository),str(clone)],check=True)
        (repository/'VERSION').write_text('1.2.0\n');(repository/'new.txt').write_text('new');commit('release');subprocess.run(['git','-C',str(repository),'tag','v1.2.0'],check=True)
        target=subprocess.check_output(['git','-C',str(repository),'rev-parse','HEAD'],text=True).strip()
        with patch.object(u,'GIT_URL',str(repository)),patch.object(u,'tag_commit',return_value=target):u.apply(clone,'1.2.0')
        self.assertEqual(u.current(clone),'1.2.0');u.rollback(clone);self.assertEqual(u.current(clone),'1.1.0')
        (clone/'wsc').write_text('local edits')
        with self.assertRaisesRegex(ValueError,'Codeänderungen'):u.apply(clone,'1.2.0')
        self.assertEqual((clone/'wsc').read_text(),'local edits')

if __name__=='__main__':unittest.main()
