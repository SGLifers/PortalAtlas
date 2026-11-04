#!/usr/bin/env python3
"""Recover representative material colors without rebuilding map geometry/graphs."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.audit_colors import audit,ready_maps


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('maps',nargs='*')
    parser.add_argument('--all-arenas',action='store_true',help='All already-imported standalone arena/training maps')
    parser.add_argument('--refresh',action='store_true',help='Re-export even when current appearance passes validation')
    args=parser.parse_args()
    if args.maps and args.all_arenas:parser.error('Choose map IDs or --all-arenas, not both.')
    maps=ready_maps(ROOT) if args.all_arenas else list(dict.fromkeys(args.maps or ['MAP_Academy']))
    if not maps:parser.error('Import map geometry before importing colors.')
    for mid in maps:
        if not re.fullmatch(r'MAP_[A-Za-z0-9_]+',mid) or not (ROOT/'data/scenes'/f'{mid}.json').is_file():
            parser.error(f'Import the map geometry first: {mid}')
    local=ROOT/'.local';local.mkdir(exist_ok=True)
    destination=ROOT/'data/appearance';destination.mkdir(exist_ok=True)
    report={'maps':{},'passed':True}
    with (local/'import.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('Another asset import is active; retry after it finishes.')
        env=os.environ.copy();env.update(ATLAS_KEY_FILE=str(ROOT/'data/key.txt'),ATLAS_MAPPING_FILE=str(ROOT/'data/mappings.json'),DOTNET_PROCESSOR_COUNT='2',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        for index,mid in enumerate(maps,1):
            started=time.monotonic();path=destination/f'{mid}.json';scene=json.loads((ROOT/'data/scenes'/f'{mid}.json').read_text())
            try:
                data=None
                if path.exists() and not args.refresh:
                    try:
                        candidate=json.loads(path.read_text());validation=audit(scene,candidate,ROOT/'data/extracted')
                        if validation['passed']:data=candidate
                    except (OSError,ValueError,KeyError,TypeError):pass
                reused=data is not None
                if not reused:
                    print(f'[{index}/{len(maps)}] Reading material colors: {mid}',flush=True)
                    with tempfile.TemporaryDirectory(prefix='color-import-',dir=local) as staging:
                        with (local/(mid+'-colors.log')).open('w') as log:
                            subprocess.run([str(ROOT/'.tools/dotnet/dotnet'),str(ROOT/'tools/AssetReader/bin/Release/net10.0/AssetReader.dll'),str(ROOT/'data/install/Paks'),'export-colors',mid,staging],cwd=ROOT,env=env,stdout=log,stderr=log,check=True,timeout=1800)
                        data=json.loads((Path(staging)/f'{mid}.json').read_text())
                    validation=audit(scene,data,ROOT/'data/extracted')
                    if not validation['passed']:
                        (local/f'{mid}-colors-rejected.json').write_text(json.dumps(data,separators=(',',':')))
                        raise ValueError('; '.join(validation['errors']))
                data['coverage']={key:validation[key] for key in ('visibleTriangles','coloredTriangles','triangleCoveragePercent')}
                temp=path.with_suffix('.json.tmp')
                try:temp.write_text(json.dumps(data,separators=(',',':')));os.replace(temp,path)
                finally:temp.unlink(missing_ok=True)
                report['maps'][mid]={**validation,'status':'reused' if reused else 'imported','seconds':round(time.monotonic()-started,1)}
                print(f"[{index}/{len(maps)}] {mid}: {validation['resolvedMaterials']}/{validation['materials']} colors, {validation['triangleCoveragePercent']}% mesh triangles ({'cached' if reused else 'imported'})",flush=True)
            except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:
                report['maps'][mid]={'status':'failed','passed':False,'error':str(error),'seconds':round(time.monotonic()-started,1)};report['passed']=False
                print(f'[{index}/{len(maps)}] FAILED {mid}: {error}',flush=True)
            target=ROOT/'data/color-import-report.json';temp=target.with_suffix('.json.tmp')
            try:temp.write_text(json.dumps(report,indent=2));os.replace(temp,target)
            finally:temp.unlink(missing_ok=True)
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
