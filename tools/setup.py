#!/usr/bin/env python3
"""Prepare the pinned offline reader. Run via setup.sh to install Python tools."""
import hashlib
import json
import os
import pathlib
import subprocess
import urllib.request
import zipfile
from prepare_assets import prepare
from extract_key import recover

ROOT=pathlib.Path(__file__).resolve().parents[1]
os.chdir(ROOT)
VERSIONS=json.loads((ROOT/'tools/versions.json').read_text())
ENV=os.environ.copy();ENV.update(DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_PROCESSOR_COUNT='2',CUE4PARSE_SKIP_NATIVE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')


def run(argv,**kw):subprocess.run([str(x) for x in argv],cwd=ROOT,env=ENV,check=True,**kw)
def download(url,path):
    if path.exists():return
    part=path.with_suffix(path.suffix+'.part')
    with urllib.request.urlopen(url,timeout=120) as response,part.open('wb') as target:
        import shutil
        shutil.copyfileobj(response,target)
    part.replace(path)


(ROOT/'.tools').mkdir(exist_ok=True)
dotnet=ROOT/'.tools/dotnet/dotnet'
if not dotnet.exists():
    download('https://dot.net/v1/dotnet-install.sh',ROOT/'.tools/dotnet-install.sh')
    run(['bash',ROOT/'.tools/dotnet-install.sh','--version',VERSIONS['dotnet_sdk'],'--install-dir',ROOT/'.tools/dotnet','--no-path'])
cue=ROOT/'.tools/CUE4Parse'
if not (cue/'.git').exists():
    cue.mkdir(exist_ok=True);run(['git','init',cue]);run(['git','-C',cue,'remote','add','origin',VERSIONS['cue4parse_repository']]);run(['git','-C',cue,'fetch','--depth','1','origin',VERSIONS['cue4parse_commit']]);run(['git','-C',cue,'checkout','--detach','FETCH_HEAD'])
actual=subprocess.check_output(['git','-C',str(cue),'rev-parse','HEAD'],text=True).strip()
if actual!=VERSIONS['cue4parse_commit']:raise SystemExit('Unexpected CUE4Parse checkout version')
run(['git','-C',cue,'diff','--exit-code','--quiet'])
if not (ROOT/'.tools/liboodle-data-shared.so').exists():
    archive=ROOT/'.tools/oodle.zip';download(f"https://github.com/WorkingRobot/OodleUE/releases/download/{VERSIONS['oodle_release']}/gcc-x64-release.zip",archive)
    with zipfile.ZipFile(archive) as z:(ROOT/'.tools/liboodle-data-shared.so').write_bytes(z.read('lib/liboodle-data-shared.so'))
if hashlib.sha256((ROOT/'.tools/liboodle-data-shared.so').read_bytes()).hexdigest()!=VERSIONS['oodle_linux_sha256']:
    raise SystemExit('Unexpected Oodle runtime hash')
prepare()
key=recover(ROOT/'data/install/Shipping.exe');keyfile=ROOT/'data/key.txt';keyfile.write_text(key.hex());keyfile.chmod(0o600)
if not (ROOT/'data/mappings.json').exists():
    run([os.sys.executable,'tools/reflection_emulator.py'])
    run([os.sys.executable,'tools/build_mappings.py'])
run([dotnet,'build','tools/AssetReader','-c','Release','-m:2'])
ENV.update(ATLAS_KEY_FILE=str(keyfile),ATLAS_MAPPING_FILE=str(ROOT/'data/mappings.json'))
run([dotnet,'tools/AssetReader/bin/Release/net10.0/AssetReader.dll','data/install/Paks','list','.umap','data/maps-index.json'])
run([os.sys.executable,'tools/extract_movement.py'])
print('Asset reader ready. Import maps with .venv/bin/python tools/import_maps.py, then run ./run.sh.')
