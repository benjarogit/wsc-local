"""Stable-release updates. Standalone so a private copy can recover a failed update."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'benjarogit/wsc-local'
API = 'https://api.github.com/repos/' + REPOSITORY
GIT_URL = 'https://github.com/' + REPOSITORY + '.git'
RELEASES = 'https://github.com/' + REPOSITORY + '/releases'
MANIFEST = '.wsc-local-release.json'
PROTECTED = {'.git', '.env', 'var', 'snapshots', 'certs', 'woltlab', '.wsc-local', 'node_modules'}
MAX_DOWNLOAD = 128 * 1024 * 1024
LOCK_STALE_SECONDS = 24 * 60 * 60
LOCK_INCOMPLETE_SECONDS = 60


def _process_start_time(pid: int) -> str:
    """Kernel start time of a process, used to detect reused PIDs."""
    try:
        stat = Path(f'/proc/{pid}/stat').read_text(encoding='ascii', errors='replace')
        return stat.rsplit(')', 1)[1].split()[19]
    except (OSError, IndexError):
        return ''


def _pid_alive(pid: int) -> bool:
    if pid < 1:
        return False
    if os.name == 'nt':
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return ctypes.windll.kernel32.GetLastError() == 5  # Access denied: process exists.
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


def _lock_holder(lock: Path) -> tuple[int, str] | None:
    try:
        lines = lock.read_text(encoding='utf-8').splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    try:
        pid = int(lines[0])
    except (IndexError, ValueError):
        return None
    return pid, (lines[1] if len(lines) > 1 else '')


def _lock_is_stale(lock: Path) -> bool:
    try:
        age = time.time() - lock.stat().st_mtime
    except FileNotFoundError:
        return True
    holder = _lock_holder(lock)
    if holder is None:
        # A process may have created the file but not written its owner yet.
        return age > LOCK_INCOMPLETE_SECONDS
    pid, start = holder
    if start and _process_start_time(pid) not in {'', start}:
        return True
    if not _pid_alive(pid):
        return True
    return age > LOCK_STALE_SECONDS


def _acquire_lock(lock: Path) -> int:
    lock.parent.mkdir(parents=True, exist_ok=True)
    descriptor = None
    for _ in range(3):
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            break
        except FileExistsError:
            if not _lock_is_stale(lock):
                raise RuntimeError('Ein Update ist bereits gesperrt. Prüfe den letzten Update-Status und die Wiederherstellung.') from None
            try:
                lock.unlink()
            except FileNotFoundError:
                pass
    if descriptor is None:
        raise RuntimeError('Ein Update ist bereits gesperrt. Prüfe den letzten Update-Status und die Wiederherstellung.')
    inode = os.fstat(descriptor).st_ino
    with os.fdopen(descriptor, 'w') as stream:
        stream.write(f'{os.getpid()}\n{_process_start_time(os.getpid())}\n')
    try:
        stolen = lock.stat().st_ino != inode
    except FileNotFoundError:
        stolen = True
    if stolen:
        raise RuntimeError('Ein Update ist bereits gesperrt. Prüfe den letzten Update-Status und die Wiederherstellung.')
    return inode


def _release_lock(lock: Path, inode: int) -> None:
    try:
        if lock.stat().st_ino == inode:
            lock.unlink()
    except FileNotFoundError:
        pass


def version(value: str) -> tuple[int, int, int]:
    if not isinstance(value,str) or not re.fullmatch(r'v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)',value):
        raise ValueError('Ungültige Release-Version.')
    return tuple(map(int,value.removeprefix('v').split('.')))


def current(root: Path = ROOT) -> str:
    value = (root/'VERSION').read_text().strip()
    version(value)
    return value


def state(root: Path = ROOT) -> dict:
    try: return json.loads((root/'var/update-state.json').read_text())
    except (OSError,ValueError): return {}


def write_state(root: Path, **values) -> dict:
    data = {**state(root), **values, 'updated_at': time.time()}
    atomic_json(root/'var/update-state.json', data)
    return data


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temporary.open('x',encoding='utf-8') as stream: json.dump(data,stream,ensure_ascii=False,indent=2)
        temporary.chmod(0o600);temporary.replace(path)
    finally: temporary.unlink(missing_ok=True)


def trusted_url(url: str) -> str:
    parsed=urllib.parse.urlsplit(url)
    host=parsed.hostname or ''
    if parsed.scheme!='https' or parsed.username or parsed.password or parsed.port not in (None,443) or not (host in {'github.com','api.github.com'} or host.endswith('.githubusercontent.com')):
        raise ValueError('Das Update verweist nicht auf einen erlaubten GitHub-Download.')
    return url


class TrustedRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        trusted_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def download(url: str, limit: int = MAX_DOWNLOAD) -> bytes:
    trusted_url(url)
    opener=urllib.request.build_opener(TrustedRedirects())
    try:
        request=urllib.request.Request(url,headers={'User-Agent':'wsc-local-updater','Accept':'application/vnd.github+json' if url.startswith(API) else 'application/octet-stream'})
        with opener.open(request,timeout=20) as response:
            trusted_url(response.geturl());data=response.read(limit+1)
        if len(data)>limit:raise ValueError('Der Update-Download überschreitet die erlaubte Größe.')
        return data
    except urllib.error.HTTPError as error:
        code=error.code;error.close()
        raise RuntimeError(f'GitHub ist derzeit nicht erreichbar (HTTP {code}). Prüfe die Verbindung oder versuche es später erneut.') from None
    except (OSError,urllib.error.URLError) as error:
        raise RuntimeError('Die Update-Prüfung konnte GitHub nicht erreichen. Prüfe deine Internetverbindung und versuche es erneut.') from error


def api(path: str) -> dict:
    return json.loads(download(API+path,4*1024*1024))


def release_info(data: dict) -> dict:
    if not isinstance(data,dict) or not isinstance(data.get('assets',[]),list) or any(not isinstance(item,dict) for item in data.get('assets',[])):raise ValueError('GitHub hat keine gültigen Release-Daten geliefert.')
    tag=data.get('tag_name','');version(tag);v=tag.removeprefix('v')
    if tag!='v'+v or data.get('draft') or data.get('prerelease'):raise ValueError('Es wurde kein stabiles Release gefunden.')
    assets={item.get('name',''):item for item in data.get('assets',[]) if isinstance(item.get('name',''),str)}
    names=[f'wsc-local-{v}.zip',f'wsc-local-{v}-SHA256SUMS.txt']
    urls=[]
    for name in names:
        url=assets.get(name,{}).get('browser_download_url','')
        expected=f'{RELEASES}/download/{tag}/{name}'
        if url!=expected:raise ValueError('Dieses Release enthält kein vollständiges, geprüftes Updatepaket. Öffne die manuelle Anleitung.')
        urls.append(url)
    return {'version':v,'tag':tag,'url':RELEASES+'/tag/'+tag,'zip_url':urls[0],'checksum_url':urls[1],'notes':str(data.get('body',''))[:20000]}


def check(root: Path = ROOT, force: bool = False) -> dict:
    installed=current(root);cache=root/'var/update-check.json'
    result=None
    if not force:
        try:
            cached=json.loads(cache.read_text())
            if 0<=time.time()-cached['checked_at']<21600:result=cached
        except (OSError,ValueError,KeyError,TypeError):pass
    if result is None:
        result={'release':release_info(api('/releases/latest')),'checked_at':time.time()}
        atomic_json(cache,result)
    selected=result['release'];version(selected['version'])
    return {'current':installed,'latest':selected['version'],'available':version(selected['version'])>version(installed),'checked_at':result['checked_at'],'release_url':selected['url'],'notes':selected['notes'],'mode':installation_mode(root),'state':state(root)}


def _git(root: Path, *arguments: str, okay: bool = True) -> subprocess.CompletedProcess:
    result=subprocess.run(['git','-c','core.hooksPath='+str(root/'var/empty-hooks'),'-C',str(root),*arguments],capture_output=True,text=True,timeout=180,env={**os.environ,'GIT_TERMINAL_PROMPT':'0'})
    if okay and result.returncode:raise RuntimeError('Git konnte das Update nicht ausführen. Lokale Änderungen und Branch-Stand prüfen; die manuelle Anleitung bleibt verfügbar.')
    return result


def installation_mode(root: Path) -> str:
    if not shutil.which('git'):return 'zip'
    result=_git(root,'rev-parse','--show-toplevel',okay=False)
    return 'git' if result.returncode==0 and Path(result.stdout.strip()).resolve()==root.resolve() else 'zip'


def source_path(value: str) -> str:
    path=PurePosixPath(value)
    if not value or str(path)!=value or '\\' in value or '\0' in value or path.is_absolute() or any(part in {'..','.'} or ':' in part for part in value.split('/')):
        raise ValueError('Unsicherer Dateipfad im Updatepaket.')
    if path.parts[0] in PROTECTED and not (len(path.parts)==2 and path.name=='.gitkeep' and path.parts[0]!='.git'):
        raise ValueError('Das Update versucht lokale Daten zu ersetzen.')
    return str(path)


def safe_target(root: Path, name: str) -> Path:
    target=root/source_path(name)
    for item in (target,*target.parents):
        if item==root:break
        if item.is_symlink():raise ValueError('Ein Updatepfad ist eine Verknüpfung. Verwende die manuelle Anleitung.')
    return target


def old_files(root: Path) -> dict:
    manifest=root/MANIFEST
    if manifest.is_file():
        data=json.loads(manifest.read_text())
        if data.get('version')!=current(root):raise ValueError('Das Installationsmanifest passt nicht zur Versionsnummer.')
        return {source_path(name):{'sha256':digest} for name,digest in data['files'].items()}
    # v1.1 ZIPs predate the installation manifest. Compare against their official Git tree.
    commit=tag_commit('v'+current(root))
    tree=api('/git/commits/'+commit)['tree']['sha']
    data=api('/git/trees/'+tree+'?recursive=1')
    if data.get('truncated'):raise ValueError('Der Dateikatalog des installierten Releases ist unvollständig.')
    files={}
    for item in data.get('tree',[]):
        if item.get('type')=='blob':
            if item.get('mode') not in {'100644','100755'}:raise ValueError('Nicht unterstützte Datei im Release.')
            files[source_path(item['path'])]={'git_blob':item['sha']}
    if 'VERSION' not in files or 'wsc' not in files:raise ValueError('Der Release-Dateikatalog ist unvollständig.')
    return files


def matches(path: Path, expected: dict) -> bool:
    if not path.is_file() or path.is_symlink():return False
    value=path.read_bytes()
    if 'sha256' in expected:return hashlib.sha256(value).hexdigest()==expected['sha256']
    if path.suffix.lower() in {'.ps1','.cmd'}:value=value.replace(b'\r\n',b'\n')
    return hashlib.sha1(b'blob '+str(len(value)).encode()+b'\0'+value).hexdigest()==expected.get('git_blob')


def tag_commit(tag: str) -> str:
    version(tag)
    obj=api('/git/ref/tags/'+tag)['object']
    for _ in range(4):
        if obj['type']=='commit' and re.fullmatch(r'[a-f0-9]{40}',obj['sha']):return obj['sha']
        if obj['type']!='tag':break
        obj=api('/git/tags/'+obj['sha'])['object']
    raise ValueError('Der Release-Tag verweist nicht auf einen gültigen Commit.')


def manual_guide(root: Path, target: str = '') -> dict:
    installed=current(root);mode=installation_mode(root)
    steps=['Laufende Workbench-Vorgänge abschließen und während des Dateiaustauschs keine Dashboard-Aktionen ausführen. WoltLab-Projekte können weiterlaufen.']
    if mode=='git':
        steps+=['Lokale Codeänderungen separat sichern oder committen. Keine Dateien oder Änderungen löschen.','Im Projektordner git pull --ff-only ausführen. Bei einem abweichenden Branch die Git-Meldung klären.','Danach ./start.sh starten; unter Windows Start-wsc-local.cmd verwenden.']
    else:
        steps+=['Den bisherigen Programmordner vollständig als Rückfall kopieren. Lokale Codeanpassungen separat sichern.','Das neue Release-ZIP separat entpacken. Nur dessen Programmdateien in den bisherigen Programmordner übernehmen. Persönliche .env-, var-, certs-, snapshots- und woltlab-Daten unverändert lassen; Ordner zusammenführen statt ersetzen.','Im bisherigen Programmordner ./start.sh bzw. Start-wsc-local.cmd starten. Der Starter beendet den alten eigenen Dashboard-Prozess und öffnet die aktualisierte Oberfläche.']
    steps+=['Die Versionsnummer prüfen und die bestehenden Projekte öffnen. Die getrennt gespeicherten Projektdateien und Zugangsdaten bleiben erhalten.']
    return {'mode':mode,'current':installed,'target':target,'steps':steps,'url':RELEASES+'/latest'}


def dashboard_instances(root: Path) -> list[dict]:
    result=[]
    for record in (root/'var/panel-runtimes').glob('*.json'):
        try:
            item=json.loads(record.read_text());os.kill(int(item['pid']),0)
            result.append(item)
        except (OSError,ValueError,KeyError):continue
    return result


def plan(root: Path = ROOT, force: bool = False) -> dict:
    result=check(root,force);problems=[]
    if not result['available']:problems.append('Es ist keine neuere stabile Version verfügbar.')
    if state(root).get('phase') in {'checking','installing','installed','restarting','restoring'}:problems.append('Ein Update oder dessen Neustart ist noch nicht abgeschlossen.')
    if len(dashboard_instances(root))>1:problems.append('Mehrere Dashboards dieses Programmordners laufen. Zusätzliche Instanzen vor dem Update beenden.')
    if result['available'] and result['mode']=='git':
        if _git(root,'status','--porcelain','--untracked-files=no').stdout.strip():problems.append('Lokale Codeänderungen gefunden. Sichere sie und nutze die Anleitung.')
    elif result['available']:
        try:
            for name,expected in old_files(root).items():
                if not matches(safe_target(root,name),expected):
                    problems.append('Lokale oder fehlende Programmdateien gefunden. Die manuelle Anleitung schützt deine Anpassungen.');break
        except (OSError,ValueError,RuntimeError,KeyError):problems.append('Der installierte Dateistand konnte nicht verifiziert werden. Nutze die manuelle Anleitung.')
    return {**result,'can_apply':not problems,'problems':problems,'guide':manual_guide(root,result['latest'])}


def unpack_release(payload: bytes, wanted: str) -> tuple[dict,dict]:
    files={};modes={};seen=set();prefix='wsc-local-'+wanted+'/'
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        if len(archive.infolist())>20000 or sum(i.file_size for i in archive.infolist())>256*1024*1024:raise ValueError('Das entpackte Update ist zu groß.')
        for item in archive.infolist():
            if not item.filename.startswith(prefix):raise ValueError('Das Update hat einen unerwarteten Wurzelordner.')
            if item.is_dir():continue
            name=item.filename[len(prefix):]
            source_path(name)
            if name.casefold() in seen or (item.external_attr>>16)&0o170000==0o120000:raise ValueError('Doppelte Datei oder Verknüpfung im Update.')
            seen.add(name.casefold())
            files[name]=archive.read(item);modes[name]=0o755 if (item.external_attr>>16)&0o111 else 0o644
    manifest=json.loads(files.pop(MANIFEST).decode())
    if manifest.get('version')!=wanted or files.get('VERSION',b'').decode().strip()!=wanted:raise ValueError('Paket und Release-Version stimmen nicht überein.')
    expected=manifest.get('files',{})
    if set(expected)!=set(files) or any(hashlib.sha256(value).hexdigest()!=expected[name] for name,value in files.items()):raise ValueError('Die Dateiprüfsummen des Updates stimmen nicht überein.')
    if not {'wsc','workbench/cli.py','workbench/launcher.py','scripts/panel_server.py'}.issubset(files):raise ValueError('Das Update ist unvollständig.')
    files[MANIFEST]=json.dumps(manifest,indent=2).encode();modes[MANIFEST]=0o644
    return files,modes


def apply(root: Path, wanted: str, operation_id: str = '') -> dict:
    root=root.resolve();version(wanted)
    if state(root).get('phase') in {'checking','installing','installed','restarting','restoring'}:raise RuntimeError('Ein Update ist noch nicht abgeschlossen. Prüfe den Status und die Wiederherstellung.')
    if len(dashboard_instances(root))>1:raise RuntimeError('Mehrere Dashboards dieses Programmordners laufen. Zusätzliche Instanzen vor dem Update beenden.')
    lock=root/'var/update.lock'
    inode=_acquire_lock(lock)
    changed=False
    try:
        write_state(root,id=operation_id or uuid.uuid4().hex,phase='checking',target=wanted,mode='',backup='',files=[],created_files=[],old_commit='',error='')
        selected=release_info(api('/releases/tags/v'+wanted))
        installed=current(root)
        if version(wanted)<=version(installed):raise ValueError('Das Update muss neuer als die installierte Version sein.')
        mode=installation_mode(root)
        if mode=='git' and _git(root,'status','--porcelain','--untracked-files=no').stdout.strip():raise ValueError('Lokale Codeänderungen verhindern das automatische Update. Nutze die Anleitung.')
        sums=download(selected['checksum_url'],16384).decode()
        entries={name.lstrip('*'):digest for digest,name in re.findall(r'^([a-fA-F0-9]{64})\s+([^\r\n]+)$',sums,re.M)}
        digest=entries.get('wsc-local-'+wanted+'.zip','').lower()
        payload=download(selected['zip_url'])
        if not digest or hashlib.sha256(payload).hexdigest()!=digest:raise ValueError('Die SHA-256-Prüfung des Updatepakets ist fehlgeschlagen.')
        files,modes=unpack_release(payload,wanted)
        backup=root/'var/update-backups'/uuid.uuid4().hex;backup.mkdir(parents=True)
        recovery=root/'var/update-recovery.py';shutil.copyfile(Path(__file__),recovery)
        values={'id':operation_id or uuid.uuid4().hex,'phase':'installing','old_version':installed,'target':wanted,'mode':mode,'backup':str(backup),'error':'','created_files':[],'files':[]}
        if mode=='git':
            before=_git(root,'rev-parse','HEAD').stdout.strip()
            _git(root,'fetch','--no-tags','--',GIT_URL,'refs/tags/v'+wanted)
            after=_git(root,'rev-parse','FETCH_HEAD^{commit}').stdout.strip()
            if after!=tag_commit('v'+wanted) or _git(root,'show',after+':VERSION').stdout.strip()!=wanted:raise ValueError('Der Git-Tag passt nicht zum verifizierten Release.')
            if _git(root,'merge-base','--is-ancestor',before,after,okay=False).returncode:raise ValueError('Der lokale Branch ist vom Release abgewichen. Verwende die manuelle Anleitung.')
            names=_git(root,'diff','--name-only',before,after).stdout.splitlines()
            for name in names:source_path(name);safe_target(root,name)
            tracked=set(_git(root,'ls-files').stdout.splitlines())
            if any(safe_target(root,name).exists() and name not in tracked for name in names):raise ValueError('Eine lokale Datei kollidiert mit dem Update. Verwende die Anleitung.')
            values['old_commit']=before;write_state(root,**values);changed=True
            _git(root,'merge','--ff-only','--no-edit',after)
        else:
            previous=old_files(root)
            for name,expected in previous.items():
                if not matches(safe_target(root,name),expected):raise ValueError('Lokale Codeänderungen verhindern das automatische Update. Nutze die Anleitung.')
            managed=set(previous)|{MANIFEST}
            for name in files:
                if safe_target(root,name).exists() and name not in managed:raise ValueError('Eine lokale Datei kollidiert mit dem Update. Nutze die Anleitung.')
            needed=sum(len(value) for value in files.values())+sum((root/name).stat().st_size for name in previous)+16*1024*1024
            if shutil.disk_usage(root).free<needed:raise ValueError('Für Update und Wiederherstellung ist zu wenig Speicherplatz frei.')
            for name in managed:
                path=safe_target(root,name)
                if path.is_file():
                    saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,saved)
            values.update(files=sorted(managed|set(files)),created_files=sorted(name for name in files if not (root/name).exists()),new_hashes={name:hashlib.sha256(value).hexdigest() for name,value in files.items()},old_hashes={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in managed if (root/name).is_file()})
            write_state(root,**values);changed=True
            for name,value in files.items():
                path=safe_target(root,name)
                old_hash=values['old_hashes'].get(name)
                if (old_hash and (not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=old_hash)) or (not old_hash and path.exists()):raise ValueError('Eine Programmdatei wurde während des Updates geändert. Die Wiederherstellung schützt diese Änderung.')
                path.parent.mkdir(parents=True,exist_ok=True)
                temporary=path.with_name(path.name+'.update-'+values['id'])
                try:temporary.write_bytes(value);temporary.chmod(modes[name]);temporary.replace(path)
                finally:temporary.unlink(missing_ok=True)
            for name in managed-set(files):
                path=safe_target(root,name)
                if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()!=values['old_hashes'][name]:raise ValueError('Eine Programmdatei wurde während des Updates geändert.')
                path.unlink(missing_ok=True)
        write_state(root,phase='installed')
        return {'version':wanted,'recovery':str(recovery),'id':values['id']}
    except Exception as error:
        if changed:
            try:rollback(root);write_state(root,error='Das Update wurde abgebrochen. Der bisherige Programmstand wurde wiederhergestellt. '+str(error))
            except Exception as recovery_error:write_state(root,phase='failed',error=str(error)+' Wiederherstellung: '+str(recovery_error))
        else:write_state(root,phase='failed',error=str(error),target=wanted,id=operation_id or uuid.uuid4().hex)
        raise
    finally:_release_lock(lock,inode)


def rollback(root: Path, phase: str = 'rolled_back') -> None:
    data=state(root)
    if data.get('mode')=='git':
        if not re.fullmatch(r'[a-f0-9]{40}',data.get('old_commit','')):raise ValueError('Ungültiger Wiederherstellungs-Commit.')
        _git(root,'reset','--keep',data['old_commit'])
    elif data.get('mode')=='zip':
        backup=Path(data['backup']).resolve()
        if not backup.is_relative_to((root/'var/update-backups').resolve()):raise ValueError('Ungültiger Wiederherstellungsordner.')
        for name in data['files']:
            target=safe_target(root,name)
            allowed={data.get('old_hashes',{}).get(name),data.get('new_hashes',{}).get(name)}
            if target.exists() and (not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() not in allowed):raise RuntimeError('Eine Programmdatei wurde zwischenzeitlich geändert. Die manuelle Wiederherstellung bewahrt diese Änderung.')
        for name in data['files']:
            target=safe_target(root,name);saved=backup/source_path(name)
            if saved.is_file():target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(saved,target)
            elif name in data['created_files']:target.unlink(missing_ok=True)
    else:raise ValueError('Kein vollständiger Wiederherstellungsstand vorhanden.')
    write_state(root,phase=phase)


def runtime(root: Path) -> dict | None:
    try:
        data=json.loads((root/'var/panel-runtime.json').read_text())
        os.kill(int(data['pid']),0)
        return data
    except ProcessLookupError:return None
    except (ValueError,KeyError):raise RuntimeError('Die Dashboard-Laufzeitdatei ist ungültig. Prüfe den Prozess vor dem Update.') from None
    except OSError:
        if (root/'var/panel.pid').is_file():
            try:os.kill(int((root/'var/panel.pid').read_text()),0)
            except (ProcessLookupError,ValueError):return None
            return {'port':int(os.environ.get('PANEL_PORT','9099'))}
    return None


def local_api(port: int, path: str, data: dict | None = None, token: str = '') -> dict:
    if not isinstance(port,int) or isinstance(port,bool) or not 1<=port<=65535 or not path.startswith('/api/'):
        raise ValueError('Ungültige lokale Dashboard-Adresse.')
    request=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json','X-Panel-Token':token})
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request,timeout=3) as response:return json.load(response)


def stop_dashboard(root: Path, port: int, token: str) -> None:
    expected=hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:16]
    status=local_api(port,'/api/version')
    if status.get('workspace_id')!=expected or status.get('active_jobs'):raise RuntimeError('Die Workbench ist beschäftigt oder der Port gehört zu einer anderen Installation.')
    local_api(port,'/api/server/stop',{'workspace_id':expected},token)
    for _ in range(100):
        try:
            with socket.create_connection(('127.0.0.1',port),timeout=.2):pass
        except OSError:return
        time.sleep(.1)
    raise RuntimeError('Das Dashboard konnte nicht beendet werden.')


def restart(root: Path, port: int, token: str = '', stop: bool = True) -> None:
    if stop:stop_dashboard(root,port,token)
    target=state(root)['target']
    write_state(root,phase='restarting')
    def launch(expected: str) -> bool:
        log=root/'var/update-restart.log'
        with log.open('ab') as stream:
            process=subprocess.Popen([sys.executable,str(root/'workbench/launcher.py'),'--no-open','--port',str(port)],cwd=root,stdin=subprocess.DEVNULL,stdout=stream,stderr=stream,start_new_session=True,env={key:value for key,value in os.environ.items() if key!='WSC_UPDATE_PANEL_TOKEN'})
        workspace=hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:16]
        for _ in range(150):
            try:
                info=local_api(port,'/api/version')
                if info.get('release_version')==expected and info.get('workspace_id')==workspace:return True
            except (OSError,ValueError):pass
            if process.poll() not in (None,0):break
            time.sleep(.2)
        return False
    if launch(target):write_state(root,phase='done',error='');return
    # Stop only our own idle replacement, if it reached the API before failing health checks.
    try:stop_dashboard(root,port,token)
    except (OSError,ValueError,RuntimeError):pass
    rollback(root,phase='restoring')
    restored=launch(state(root)['old_version'])
    write_state(root,phase='rolled_back' if restored else 'failed',error='Das neue Dashboard konnte nicht starten. Der bisherige Programmstand wurde wiederhergestellt.' if restored else 'Der Dashboard-Neustart ist fehlgeschlagen. Öffne var/update-restart.log und die Wiederherstellungsanleitung.')


def cli_update(args) -> int:
    root=ROOT
    if args.guide:
        guide=manual_guide(root)
        for index,step in enumerate(guide['steps'],1):print(f'{index}. {step}')
        print(guide['url']);return 0
    result=plan(root,force=args.check)
    if args.json:print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    print(f"wsc-local {result['current']} · Latest: {result['latest']}")
    if args.guide:
        for index,step in enumerate(result['guide']['steps'],1):print(f'{index}. {step}')
        print(result['guide']['url']);return 0
    if args.check or not result['available']:
        print('Neue Version verfügbar: ./wsc update' if result['available'] else 'Keine neuere stabile Version verfügbar.');return 0
    if not result['can_apply']:raise RuntimeError(' '.join(result['problems'])+' Anleitung: ./wsc update --guide')
    print('Programmdateien aktualisieren, Wiederherstellungsstand anlegen und Dashboard neu starten. Projektdateien und Zugangsdaten bleiben erhalten.')
    if not args.yes and input('Update installieren? [j/N] ').strip().lower() not in {'j','y','ja','yes'}:return 0
    running=runtime(root);port=running['port'] if running else None
    token=os.environ.get('PANEL_TOKEN','')
    if not token and (root/'var/panel-token').is_file():token=(root/'var/panel-token').read_text().strip()
    if (root/'.env').is_file():
        for line in (root/'.env').read_text().splitlines():
            if line.startswith('PANEL_TOKEN='):token=line.split('=',1)[1].strip().strip('"\'')
    if port:stop_dashboard(root,port,token)
    try:apply(root,result['latest'])
    except Exception as error:
        if port:
            subprocess.Popen([sys.executable,str(root/'workbench/launcher.py'),'--no-open','--port',str(port)],cwd=root,start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        raise RuntimeError(state(root).get('error') or str(error)) from error
    if port:restart(root,port,stop=False)
    else:write_state(root,phase='done')
    final=state(root)
    if final['phase']!='done':raise RuntimeError(final['error'])
    print('Update installiert: wsc-local '+current(root));return 0


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--restart',nargs=2,metavar=('ROOT','PORT'));parser.add_argument('--rollback')
    arguments=parser.parse_args()
    try:
        if arguments.restart:
            time.sleep(1)
            restart(Path(arguments.restart[0]).resolve(),int(arguments.restart[1]),os.environ.get('WSC_UPDATE_PANEL_TOKEN',''))
        elif arguments.rollback:
            destination=Path(arguments.rollback).resolve()
            lock=destination/'var/update.lock'
            inode=_acquire_lock(lock)
            try:
                rollback(destination)
            finally:
                _release_lock(lock,inode)
    except Exception as error:
        if arguments.restart:write_state(Path(arguments.restart[0]),phase='failed',error=str(error))
        print(str(error),file=sys.stderr);sys.exit(1)
