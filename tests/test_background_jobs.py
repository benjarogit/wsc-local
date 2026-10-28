"""Long backup requests must return immediately and survive a client reload."""
import json
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import panel_server as panel


class BackgroundJobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.release = threading.Event()
        self.started = threading.Event()
        self.calls = []
        panel.JOBS.clear()
        def command(*args):
            self.calls.append(args)
            self.started.set()
            self.release.wait(5)
            return 0, 'verified backup'
        self.patches = [patch.object(panel, 'run_workbench', side_effect=command),
                        patch.object(panel, 'read_project', return_value=({}, Path(self.temp.name), Path(self.temp.name)/'secret')),
                        patch.object(panel, 'WORKBENCH_PROJECTS', Path(self.temp.name))]
        for item in self.patches: item.start()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), panel.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:' + str(self.server.server_port)

    def tearDown(self):
        self.release.set()
        deadline = time.monotonic() + 2
        while any(job['state'] == 'running' for job in panel.JOBS.values()) and time.monotonic() < deadline:
            time.sleep(.01)
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        for item in reversed(self.patches): item.stop()
        self.temp.cleanup()

    def request(self, route, body=None):
        headers={'X-Panel-Token':panel.TOKEN,'X-Workbench-Version':panel.PANEL_VERSION,'Content-Type':'application/json'}
        req=urllib.request.Request(self.base+route, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        try: response=urllib.request.urlopen(req, timeout=2)
        except urllib.error.HTTPError as error: response=error
        with response: return response.status, json.load(response)

    def test_backup_returns_before_completion_and_reconnects(self):
        code, task=self.request('/api/workbench', {'action':'snapshot','name':'project'})
        self.assertEqual(202, code)
        self.assertTrue(self.started.wait(1))
        code, job=self.request('/api/jobs/'+task['job_id'])
        self.assertEqual('running',job['state'])
        self.assertEqual('snapshot',job['action'])
        self.assertIn('gesichert',job['stage'])
        # A second client receives the same task rather than starting a second dump.
        code, second=self.request('/api/workbench', {'action':'snapshot','name':'project'})
        self.assertEqual(task['job_id'],second['job_id'])
        self.release.set()
        for _ in range(100):
            code, job=self.request('/api/jobs/'+task['job_id'])
            if job['state']!='running': break
            time.sleep(.01)
        self.assertEqual('done',job['state'])
        self.assertEqual('verified backup',job['output'])
        self.assertEqual('snapshot',job['action'])

    def test_every_background_action_returns_202_and_uses_the_correct_cli(self):
        expected = {
            'install':lambda n:('install',n), 'start':lambda n:('start',n),
            'stop':lambda n:('stop',n), 'doctor':lambda n:('doctor',n),
            'snapshot':lambda n:('snapshot',n), 'export':lambda n:('export',n),
            'remove':lambda n:('remove',n,'--yes'),
            'recovery_install':lambda n:('recovery','install',n,'--yes'),
            'recovery_remove':lambda n:('recovery','remove',n,'--yes'),
            'tls_enable':lambda n:('tls',n,'enable','--yes'),
            'tls_disable':lambda n:('tls',n,'disable','--yes'),
            'mail_start':lambda n:('service',n,'mail','start'),
            'mail_stop':lambda n:('service',n,'mail','stop'),
            'guide_domain':lambda n:('guide',n,'domain'),
            'guide_directory':lambda n:('guide',n,'directory'),
            'guide_migration':lambda n:('guide',n,'migration'),
            'uploads_apply':lambda n:('uploads',n,'--size','256M','--apply','--yes'),
            'restore':lambda n:('restore',n,str(Path(self.temp.name)/n/'snapshots/20261028_120000'),'--yes'),
        }
        self.assertEqual(set(expected),panel.BACKGROUND_ACTIONS)
        for index,(action,command) in enumerate(expected.items()):
            with self.subTest(action=action):
                name='project-'+str(index)
                snapshot=Path(self.temp.name)/name/'snapshots/20261028_120000'
                snapshot.mkdir(parents=True);(snapshot/'manifest.json').write_text('{}')
                self.release.clear()
                code,task=self.request('/api/workbench',{'action':action,'name':name,'snapshot':snapshot.name,'size':'256M'})
                self.assertEqual(202,code)
                code,job=self.request('/api/jobs/'+task['job_id'])
                self.assertEqual('running',job['state'])
                self.assertEqual(action,job['action'])
                self.release.set()
                for _ in range(100):
                    code,job=self.request('/api/jobs/'+task['job_id'])
                    if job['state']!='running':break
                    time.sleep(.005)
                self.assertEqual('done',job['state'])
                self.assertIn(command(name),self.calls)

    def test_failed_background_tool_returns_its_error(self):
        with patch.object(panel,'run_workbench',return_value=(1,'Recovery download unavailable')):
            code,task=self.request('/api/workbench',{'action':'recovery_install','name':'project'})
            self.assertEqual(202,code)
            for _ in range(100):
                _,job=self.request('/api/jobs/'+task['job_id'])
                if job['state']!='running':break
                time.sleep(.005)
            self.assertEqual('failed',job['state'])
            self.assertEqual('Recovery download unavailable',job['error'])

    def test_jobs_are_discoverable_without_saved_browser_state(self):
        _,task=self.request('/api/workbench',{'action':'guide_directory','name':'project'})
        code,data=self.request('/api/jobs')
        self.assertEqual(200,code)
        self.assertEqual(task['job_id'],data['items'][0]['job_id'])
        self.assertEqual('guide_directory',data['items'][0]['action'])
        self.assertEqual('running',data['items'][0]['state'])

    def test_conflicting_actions_and_restart_are_rejected(self):
        self.request('/api/workbench', {'action':'export','name':'project'})
        code, _=self.request('/api/workbench', {'action':'snapshot','name':'project'})
        self.assertEqual(409,code)
        code, _=self.request('/api/workbench', {'action':'remove','name':'project'})
        self.assertEqual(409,code)
        code, _=self.request('/api/server/stop', {'workspace_id':panel.WORKSPACE_ID})
        self.assertEqual(409,code)

    def test_acp_login_is_background_and_forwards_browser_agent(self):
        def login(name, agent):
            self.assertEqual(name,'project')
            self.assertTrue(agent)
            self.started.set();self.release.wait(5)
            return {'url':'https://project.localhost/once.php','token':'single-use','expires_in':60}
        with patch.object(panel,'prepare_acp_login',side_effect=login):
            code,task=self.request('/api/instances/project/acp-login',{})
            self.assertEqual(code,202);self.assertTrue(self.started.wait(1))
            self.assertEqual(self.request('/api/workbench',{'action':'remove','name':'project'})[0],409)
            self.release.set()
            for _ in range(100):
                _,job=self.request('/api/jobs/'+task['job_id'])
                if job['state']!='running':break
                time.sleep(.01)
            self.assertEqual(job['state'],'done');self.assertEqual(job['result']['token'],'single-use')
            self.assertNotIn('single-use',job['output'])

    def test_host_installer_waits_for_completion(self):
        def install(root):
            self.started.set();self.release.wait(5)
            return {'completed':True}
        with patch.object(panel,'launch_installation',side_effect=install):
            code,task=self.request('/api/system/install',{})
            self.assertEqual(code,202);self.assertTrue(self.started.wait(1))
            self.assertEqual(self.request('/api/system/install',{})[0],409)
            self.assertEqual(self.request('/api/server/stop',{'workspace_id':panel.WORKSPACE_ID})[0],409)
            self.release.set()
            for _ in range(100):
                _,job=self.request('/api/jobs/'+task['job_id'])
                if job['state']!='running':break
                time.sleep(.01)
            self.assertEqual(job['state'],'done');self.assertTrue(job['result']['completed'])

    def test_stale_clients_cannot_start_login_or_host_install(self):
        for path in ('/api/instances/project/acp-login','/api/system/install'):
            request=urllib.request.Request(self.base+path,data=b'{}',headers={'X-Panel-Token':panel.TOKEN})
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(request)
            self.assertEqual(error.exception.code,409)
            error.exception.close()
        self.assertFalse(panel.JOBS)

    def test_restore_validates_selection_before_creating_job(self):
        code, _=self.request('/api/workbench', {'action':'restore','name':'project','snapshot':'../other'})
        self.assertEqual(400,code)
        self.assertFalse(panel.JOBS)
        code, _=self.request('/api/workbench', {'action':'restore','name':'project','snapshot':'20261028_120000'})
        self.assertEqual(404,code)
        self.assertFalse(panel.JOBS)


if __name__=='__main__': unittest.main()
