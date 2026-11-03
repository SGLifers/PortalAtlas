#!/usr/bin/env python3
"""Recover representative material colors without rebuilding map geometry/graphs."""
import argparse
import fcntl
import os
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('maps',nargs='*',default=['MAP_Academy'])
    args=parser.parse_args()
    for mid in args.maps:
        if not re.fullmatch(r'MAP_[A-Za-z0-9_]+',mid) or not (ROOT/'data/scenes'/f'{mid}.json').is_file():
            parser.error(f'Import the map geometry first: {mid}')
    local=ROOT/'.local';local.mkdir(exist_ok=True)
    with (local/'import.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('Another asset import is active; retry after it finishes.')
        env=os.environ.copy();env.update(ATLAS_KEY_FILE=str(ROOT/'data/key.txt'),ATLAS_MAPPING_FILE=str(ROOT/'data/mappings.json'),DOTNET_PROCESSOR_COUNT='2',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        for mid in args.maps:
            print(f'Reading material colors: {mid}',flush=True)
            with (local/(mid+'-colors.log')).open('w') as log:
                subprocess.run([str(ROOT/'.tools/dotnet/dotnet'),str(ROOT/'tools/AssetReader/bin/Release/net10.0/AssetReader.dll'),str(ROOT/'data/install/Paks'),'export-colors',mid,str(ROOT/'data/appearance')],cwd=ROOT,env=env,stdout=log,stderr=log,check=True,timeout=1800)
            print(f'Saved data/appearance/{mid}.json',flush=True)


if __name__=='__main__':main()
