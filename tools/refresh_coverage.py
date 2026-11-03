#!/usr/bin/env python3
"""Add blocking-brush metadata to cached imports, then finalize existing graphs."""
import argparse
import json
import os
import pathlib
import subprocess
import sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.finalize_scene import finalize,save

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--enrich-only',action='store_true');args=parser.parse_args()
    env=os.environ.copy();env.update(ATLAS_KEY_FILE=str(ROOT/'data/key.txt'),ATLAS_MAPPING_FILE=str(ROOT/'data/mappings.json'),DOTNET_PROCESSOR_COUNT='2',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    for file in sorted((ROOT/'data/extracted').glob('MAP_*.json')):
        manifest=json.loads(file.read_text())
        if manifest.get('blockingVersion')!=1:
            with (ROOT/'.local'/(file.stem+'-brush.log')).open('w') as log:
                subprocess.run([str(ROOT/'.tools/dotnet/dotnet'),'tools/AssetReader/bin/Release/net10.0/AssetReader.dll','data/install/Paks','export-brush',file.stem,'data/extracted'],cwd=ROOT,env=env,stdout=log,stderr=log,check=True,timeout=600)
            manifest=json.loads(file.read_text())
        scene=ROOT/'data/scenes'/(file.stem+'.json')
        if scene.exists() and not args.enrich_only:
            data=finalize(json.loads(scene.read_text()),manifest,ROOT/'data/extracted');save(data,scene)
            print(file.stem,len(data['edges']),'edges',data['source']['geometryUsable'],flush=True)
        else:print(file.stem,'brush metadata ready',flush=True)
