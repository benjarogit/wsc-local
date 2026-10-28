"""Real ZIP update and dashboard handoff in a disposable program directory."""
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from test_updater import bundle,metadata
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import panel_server as panel
import updater

@unittest.skipIf(sys.platform=='win32', 'Dashboard restart runs on Linux/macOS or inside WSL2')
class UpdateRestartTests(unittest.TestCase):
    def test_update_restarts_actual_dashboard_preserving_runtime_and_personal_data(self):
        self.run_handoff(False)

    def test_broken_replacement_rolls_back_and_restarts_previous_dashboard(self):
        self.run_handoff(True)

    def run_handoff(self, broken):
        with tempfile.TemporaryDirectory(prefix='wsc restart ') as directory:
            root=Path(directory)/'program';root.mkdir()
            names=set(subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines())|{'workbench/updater.py','panel/updates.js'}
            files={name:(ROOT/name).read_bytes() for name in names if (ROOT/name).is_file()}
            files['VERSION']=b'1.2.0\n'
            for name,value in files.items():
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
            (root/updater.MANIFEST).write_text(json.dumps({'version':'1.2.0','files':{name:hashlib.sha256(value).hexdigest() for name,value in files.items()}}))
            (root/'var/panel-token').write_text(panel.TOKEN)
            (root/'personal-note.txt').write_text('preserve me')
            replacement={**files}
            if broken:replacement['scripts/panel_server.py']=b'not valid Python !!!'
            payload=bundle(replacement,'1.2.1');sums=hashlib.sha256(payload).hexdigest().encode()+b'  wsc-local-1.2.1.zip\n'
            server=ThreadingHTTPServer(('127.0.0.1',0),panel.Handler);port=server.server_port
            def serve():
                try:server.serve_forever()
                finally:server.server_close()
            patches=[patch.object(panel,'ROOT',root),patch.object(panel,'PORT',port),patch.object(panel,'WORKSPACE_ID',hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:16]),patch.object(panel,'RELEASE_VERSION','1.2.0'),patch.object(panel,'workbench_instances',return_value=[]),patch.object(panel,'system_report',return_value={'ready':True,'host':{'kind':'linux','label':'Linux','architecture':'test'},'checks':[]}),patch.dict(os.environ,{'WSC_LOCAL_HOME':str(Path(directory)/'data'),'XDG_CONFIG_HOME':str(Path(directory)/'config')}),patch.object(updater,'api',return_value=metadata('1.2.1')),patch.object(updater,'download',side_effect=lambda url,limit=updater.MAX_DOWNLOAD:sums if url.endswith('.txt') else payload)]
            for item in patches:item.start()
            panel.JOBS.clear();panel.UPDATING=False;panel.STOPPING=False
            thread=threading.Thread(target=serve,daemon=True);thread.start()
            try:
                headers={'X-Panel-Token':panel.TOKEN,'X-Workbench-Version':panel.PANEL_VERSION,'Content-Type':'application/json'}
                request=urllib.request.Request(f'http://127.0.0.1:{port}/api/updates/apply',data=json.dumps({'version':'1.2.1','confirm':True}).encode(),headers=headers)
                if os.environ.get('WSC_UPDATE_BROWSER_TEST') and not broken:
                    subprocess.run(['node',str(ROOT/'tests/browser/update-live.cjs'),f'http://127.0.0.1:{port}/'],cwd=ROOT,check=True,timeout=90)
                else:
                    with urllib.request.urlopen(request,timeout=10) as response:self.assertEqual(response.status,202)
                deadline=time.monotonic()+45
                while time.monotonic()<deadline:
                    state=updater.state(root)
                    if state.get('phase') in {'done','failed','rolled_back'}:break
                    time.sleep(.1)
                self.assertEqual(state.get('phase'),'rolled_back' if broken else 'done',state)
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/version',timeout=3) as response:status=json.load(response)
                self.assertEqual(status['release_version'],'1.2.0' if broken else '1.2.1')
                self.assertEqual((root/'var/panel-token').read_text(),panel.TOKEN)
                self.assertEqual((root/'personal-note.txt').read_text(),'preserve me')
                self.assertEqual((root/'VERSION').read_text().strip(),'1.2.0' if broken else '1.2.1')
            finally:
                try:updater.stop_dashboard(root,port,panel.TOKEN)
                except (OSError,ValueError,RuntimeError):server.shutdown();server.server_close()
                thread.join(3)
                for item in reversed(patches):item.stop()
                panel.UPDATING=False;panel.STOPPING=False;panel.JOBS.clear()

if __name__=='__main__':unittest.main()
