#!/usr/bin/env python3
"""Build a reproducible source ZIP with a managed-file manifest; optionally publish."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workbench'))
from updater import version, source_path, MANIFEST


def build(root: Path, ref: str, tag: str, destination: Path) -> dict:
    wanted=tag.removeprefix('v');version(tag)
    if tag!='v'+wanted:raise ValueError('Release-Tags müssen vMAJOR.MINOR.PATCH heißen.')
    installed=subprocess.check_output(['git','-C',str(root),'show',ref+':VERSION'],text=True).strip()
    if installed!=wanted:raise ValueError('Tag und VERSION stimmen nicht überein.')
    content=subprocess.check_output(['git','-C',str(root),'archive','--format=zip','--prefix=wsc-local-'+wanted+'/',ref])
    files={};hashes={}
    with zipfile.ZipFile(io.BytesIO(content)) as original:
        for entry in original.infolist():
            if entry.is_dir():continue
            name=entry.filename.removeprefix('wsc-local-'+wanted+'/');source_path(name)
            value=original.read(entry);files[entry.filename]=(entry,value);hashes[name]=hashlib.sha256(value).hexdigest()
    destination.mkdir(parents=True,exist_ok=True)
    target=destination/f'wsc-local-{wanted}.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,(entry,value) in files.items():archive.writestr(entry,value)
        entry=zipfile.ZipInfo('wsc-local-'+wanted+'/'+MANIFEST,(2026,1,1,0,0,0));entry.external_attr=0o100644<<16
        archive.writestr(entry,json.dumps({'version':wanted,'files':hashes},sort_keys=True,indent=2).encode())
    sums=destination/f'wsc-local-{wanted}-SHA256SUMS.txt';sums.write_text(hashlib.sha256(target.read_bytes()).hexdigest()+'  '+target.name+'\n')
    changelog=subprocess.check_output(['git','-C',str(root),'show',ref+':CHANGELOG.md'],text=True)
    sections=re.split(r'^## ',changelog,flags=re.M)
    notes=next((section for section in sections if section.startswith(wanted+' ')),None)
    if not notes:raise ValueError('Release-Hinweise fehlen im Changelog.')
    note_file=destination/'release-notes.md';note_file.write_text('## '+notes,encoding='utf-8')
    return {'zip':target,'checksum':sums,'notes':note_file,'version':wanted}


def publish(tag: str, artifacts: dict) -> None:
    repo=os.environ.get('GITHUB_REPOSITORY','benjarogit/wsc-local')
    command=['gh','release','view',tag,'--repo',repo,'--json','isDraft']
    existing=subprocess.run(command,capture_output=True,text=True)
    if existing.returncode==0 and not json.loads(existing.stdout)['isDraft']:
        print('Release bereits veröffentlicht; keine Änderung.');return
    if existing.returncode:
        subprocess.run(['gh','release','create',tag,'--repo',repo,'--verify-tag','--draft','--title','wsc-local Workbench '+artifacts['version'],'--notes-file',str(artifacts['notes'])],check=True)
    subprocess.run(['gh','release','upload',tag,'--repo',repo,str(artifacts['zip']),str(artifacts['checksum']),'--clobber'],check=True)
    latest=subprocess.run(['gh','api','repos/'+repo+'/releases/latest'],capture_output=True,text=True)
    make_latest=latest.returncode!=0 or version(json.loads(latest.stdout)['tag_name'])<version(tag)
    subprocess.run(['gh','release','edit',tag,'--repo',repo,'--draft=false','--latest='+str(make_latest).lower()],check=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--tag',required=True);parser.add_argument('--ref',default='HEAD');parser.add_argument('--output',default='dist');parser.add_argument('--publish',action='store_true');args=parser.parse_args()
    if args.publish:
        tagged=subprocess.check_output(['git','rev-parse',args.tag+'^{commit}'],text=True).strip()
        checked=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        if tagged!=checked:raise ValueError('Der Release-Tag wurde nach der Prüfung verändert.')
        packaged=subprocess.check_output(['git','rev-parse',args.ref+'^{commit}'],text=True).strip()
        if packaged!=checked:raise ValueError('Das Release-Paket muss aus dem geprüften Commit stammen.')
    artifacts=build(ROOT,args.ref,args.tag,Path(args.output))
    if args.publish:publish(args.tag,artifacts)
    print('Release-Paket:',artifacts['zip'])
