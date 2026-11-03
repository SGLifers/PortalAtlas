#!/usr/bin/env python3
"""Recover serialized movement defaults and navigation dimensions, with provenance."""
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.compile_scene import clean


def main():
    env=os.environ.copy();env.update(ATLAS_KEY_FILE=str(ROOT/'data/key.txt'),ATLAS_MAPPING_FILE=str(ROOT/'data/mappings.json'),DOTNET_PROCESSOR_COUNT='2')
    sources={
        'character':'PortalWars2/Content/Player/BP_Character_Base.uasset',
        'sprint':'PortalWars2/Plugins/GameFeatures/Editions/EDT_Splitgate/Content/Player/Movement/Data/CT_Sprint.uasset',
        'launch':'PortalWars2/Content/Blueprints/Environment/LevelInteractables/Data/CT_PortalLaunchWall.uasset',
        'clamber':'PortalWars2/Plugins/GameFeatures/Editions/EDT_Splitgate/Content/Player/Movement/Data/CT_Clamber.uasset'}
    inputs=ROOT/'data/movement';inputs.mkdir(exist_ok=True)
    reader=[str(ROOT/'.tools/dotnet/dotnet'),'tools/AssetReader/bin/Release/net10.0/AssetReader.dll','data/install/Paks']
    data={}
    with (inputs/'reader.log').open('w') as log:
        for key,path in sources.items():
            dest=inputs/(key+'.json');subprocess.run(reader+['dump',path,str(dest)],cwd=ROOT,env=env,stdout=log,stderr=log,check=True)
            data[key]=clean(json.loads(dest.read_text()))
        config=inputs/'DefaultEngine.ini';subprocess.run(reader+['raw','PortalWars2/Config/DefaultEngine.ini',str(config)],cwd=ROOT,env=env,stdout=log,stderr=log,check=True)
    movement=next(x['Properties'] for x in data['character'] if x['Type']=='PortalWarsCharacterMovementComponentV2')
    curves={}
    for key in ('sprint','launch','clamber'):
        for asset in data[key]:
            for row,curve in asset.get('Rows',{}).items():
                keys=curve.get('Keys',[])
                if keys and all(k['Value']==keys[0]['Value'] for k in keys):curves[row]=keys[0]['Value']
    text=config.read_text(errors='replace')
    def config_number(name,default):
        m=re.search(r'\b'+re.escape(name)+r'=([\d.]+)',text)
        return float(m[1])/100 if m else default
    result={'walkSpeed':movement['MaxWalkSpeed']/100,'strafeWalkSpeed':movement['StrafeWalkSpeed']/100,
        'sprintMultiplier':curves.get('DataRegistry.Movement.Sprint.SpeedMultiplier'),
        'navRadius':config_number('AgentRadius',.45),'navHeight':config_number('AgentHeight',2.),
        'navStepHeight':config_number('AgentStepHeight',.3),'curves':curves,'sources':sources,
        'qualification':'Serialized base-character defaults and edition curve tables. Active mode modifiers are not resolved; effective speeds and execution times are not measured.'}
    if result['sprintMultiplier']:result['baseSprintSpeed']=result['walkSpeed']*result['sprintMultiplier']
    temp=ROOT/'data/movement-model.json.tmp';temp.write_text(json.dumps(result,indent=2));temp.replace(ROOT/'data/movement-model.json')
    print('Recovered base walk speed',result['walkSpeed'],'m/s; sprint multiplier',result['sprintMultiplier'])


if __name__=='__main__':main()
