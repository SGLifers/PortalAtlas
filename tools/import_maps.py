#!/usr/bin/env python3
"""Import one or more installed arena maps; resumes completed revisions."""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import time

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from server.map_variants import expanded_features,feature_root
EXCLUDED={'MAP_Biome6','MAP_Biome6_Sanctum','MAP_Creative_EmptySpace','MAP_Creative_FlatEarth','MAP_Creative_Simulation','MAP_Creative_WetOcean','MAP_Simulation','MAP_Ozone','MAP_Ozone_Graffiti'}


def available():
    return expanded_features(set(re.findall(r'/GameFeatures/Maps/(MAP_[^/]+)/',(ROOT/'data/maps-index.json').read_text())))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('maps',nargs='*');p.add_argument('--all-arenas',action='store_true');p.add_argument('--force',action='store_true');p.add_argument('--refresh',action='store_true',help='Reuse extracted geometry and refresh stale scene models');a=p.parse_args()
    maps=[m for m in available() if m not in EXCLUDED] if a.all_arenas else (a.maps or ['MAP_Academy','MAP_Abyss','MAP_Grit','MAP_Oasis'])
    unknown=set(maps)-set(available())
    if unknown:raise SystemExit('Unknown map features: '+', '.join(sorted(unknown)))
    env=os.environ.copy();env.update(ATLAS_KEY_FILE=str(ROOT/'data/key.txt'),ATLAS_MAPPING_FILE=str(ROOT/'data/mappings.json'),DOTNET_PROCESSOR_COUNT='2',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    local=ROOT/'.local';local.mkdir(exist_ok=True);report={};fail=False
    import fcntl
    lock=(local/'import.lock').open('w')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise SystemExit('Another import process is active')
    for mid in maps:
        feature,selected_root=feature_root(mid)
        scene=ROOT/'data/scenes'/(mid+'.json')
        existing=json.loads(scene.read_text()) if scene.exists() else None
        if existing and not a.force and (not a.refresh or (existing.get('modelVersion',0)>=5 and existing.get('finalizeVersion')==1)):
            report[mid]={'status':'ready','walls':len(existing['nodes']),'edges':len(existing['edges']),'geometryUsable':existing['source'].get('geometryUsable',False)}
            print('Already imported',mid,flush=True);continue
        print('Importing',mid,flush=True);started=time.monotonic()
        try:
            with (local/(mid+'.log')).open('w') as log:
                manifest=ROOT/'data/extracted'/(feature+'.json')
                command='export-feature' if a.force or not manifest.exists() else 'export-terrain'
                if existing and existing['source'].get('coverage',{}).get('missingStreaming'):command='export-feature'
                if command=='export-feature' or json.loads(manifest.read_text()).get('terrainVersion',0)<1:
                    subprocess.run([str(ROOT/'.tools/dotnet/dotnet'),'tools/AssetReader/bin/Release/net10.0/AssetReader.dll','data/install/Paks',command,feature,'data/extracted'],cwd=ROOT,env=env,check=True,timeout=1800,stdout=log,stderr=log)
                if json.loads(manifest.read_text()).get('blockingVersion')!=1:
                    subprocess.run([str(ROOT/'.tools/dotnet/dotnet'),'tools/AssetReader/bin/Release/net10.0/AssetReader.dll','data/install/Paks','export-brush',feature,'data/extracted'],cwd=ROOT,env=env,check=True,timeout=600,stdout=log,stderr=log)
                command=[sys.executable,'tools/compile_scene.py',feature]
                if selected_root:command+=['--root',selected_root,'--scene-id',mid]
                subprocess.run(command,cwd=ROOT,env=env,check=True,timeout=3600,stdout=log,stderr=log)
            data=json.loads(scene.read_text());report[mid]={'status':'ready','walls':len(data['nodes']),'edges':len(data['edges']),'geometryUsable':data['source']['geometryUsable'],'seconds':round(time.monotonic()-started,1)}
        except Exception as exc:report[mid]={'status':'failed','error':str(exc)};fail=True
        (ROOT/'data/import-report.json').write_text(json.dumps(report,indent=2));print(mid,report[mid],flush=True)
    (ROOT/'data/import-report.json').write_text(json.dumps(report,indent=2))
    return 1 if fail else 0


if __name__=='__main__':raise SystemExit(main())
