#!/usr/bin/env python3
"""Copy read-only installed assets into the ignored local extraction cache."""
import argparse
import hashlib
import json
import pathlib
import shutil
import struct
import subprocess
import uuid

ROOT=pathlib.Path(__file__).resolve().parents[1]


def inventory():
    folder=ROOT/'data/install/Paks';rows=[]
    for p in sorted(folder.iterdir()):
        if p.suffix not in ('.pak','.utoc','.ucas','.sig'):continue
        row={'file':p.name,'bytes':p.stat().st_size}
        if p.suffix=='.utoc':
            content=p.read_bytes()
            if content[:16]!=b'-==--==--==--==-':raise ValueError('Unexpected IoStore header: '+p.name)
            if len(content)<144:raise ValueError('Truncated archive header: '+p.name)
            row.update(tocVersion=content[16],sha256=hashlib.sha256(content).hexdigest())
        rows.append(row)
    if not any(r['file']=='global.utoc' for r in rows):raise ValueError('Missing global IoStore container')
    for row in rows:
        if row['file'].endswith('.utoc') and not (folder/(row['file'][:-5]+'.ucas')).is_file():
            raise ValueError('Missing IoStore data companion: '+row['file'])
    target=ROOT/'data/install/Shipping.exe'
    if not target.is_file():raise ValueError('Missing shipping executable')
    info={'files':rows,'executableSha256':hashlib.sha256(target.read_bytes()).hexdigest(),
          'archiveBytes':sum(x['bytes'] for x in rows)}
    (ROOT/'data/install/inventory.json').write_text(json.dumps(info,indent=2))
    return info


def prepare(game_dir=None,image=None):
    destination=ROOT/'data/install';destination.mkdir(parents=True,exist_ok=True)
    if not (destination/'Paks/global.utoc').exists():
        if game_dir:
            source=pathlib.Path(game_dir).resolve()
            if (source/'PortalWars2').is_dir():source=source/'PortalWars2'
            if not (source/'Content/Paks').is_dir():raise ValueError('Expected PortalWars2/Content/Paks in the installation')
            shutil.copytree(source/'Content/Paks',destination/'Paks')
            shutil.copy2(source/'Binaries/Win64/PortalWars2-Win64-Shipping.exe',destination/'Shipping.exe')
        else:
            image=image or json.loads((ROOT/'tools/versions.json').read_text())['game_image']
            name='portal-atlas-copy-'+uuid.uuid4().hex[:10]
            subprocess.run(['docker','create','--name',name,'--network','none','--read-only','--entrypoint','/bin/true',image],check=True,stdout=subprocess.DEVNULL)
            try:
                subprocess.run(['docker','cp',name+':/game/PortalWars2/Content/Paks',str(destination/'Paks')],check=True)
                subprocess.run(['docker','cp',name+':/game/PortalWars2/Binaries/Win64/PortalWars2-Win64-Shipping.exe',str(destination/'Shipping.exe')],check=True)
            finally:subprocess.run(['docker','rm',name],check=True,stdout=subprocess.DEVNULL)
    info=inventory();print('Prepared',len(info['files']),'archive files;',round(info['archiveBytes']/1024**3,1),'GiB')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game-dir');p.add_argument('--image');a=p.parse_args();prepare(a.game_dir,a.image)
