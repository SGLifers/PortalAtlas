#!/usr/bin/env python3
"""Filter candidate edges against asset blocking brushes and verify dependencies."""
import argparse
import hashlib
import json
import pathlib
import re
import sys
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from server.geometry import InstanceBVH,transform
from tools.collision import simple_collision,collision_policy


def clean(value):
    if isinstance(value,dict):return {re.sub(r'\[\d+\]$','',k):clean(v) for k,v in value.items()}
    if isinstance(value,list):return [clean(v) for v in value]
    return value


def blocks(row,channel):
    if not row.get('enabled',True) or not collision_policy(row,{'body':row.get('body')}):return False
    defaults=(row.get('body') or {}).get('Properties',{}).get('DefaultInstance',{})
    collision=defaults| (row.get('collision') or {})
    for response in collision.get('CollisionResponses',{}).get('ResponseArray',[]):
        if response.get('Channel')==channel:return str(response.get('Response','')).rsplit('::',1)[-1] in ('2','Block','ECR_Block')
    profile=collision.get('CollisionProfileName','')
    if profile.startswith('InvisibleWall') and channel=='PortalLauncher':return False
    return True


def finalize(scene,manifest,extracted):
    arrays={};actual_to_virtual={}
    for package in manifest['packages']:
        array=clean(json.loads((extracted/'packages'/(package['id']+'.json')).read_text()))
        world=next((o for o in array if o['Type']=='World'),None)
        if world:arrays[world['Package']]=array;actual_to_virtual[package['path']]=world['Package']
    active={scene['rootPackage']:np.eye(4)};queue=[scene['rootPackage']];missing=[]
    while queue:
        name=queue.pop(0)
        for obj in arrays.get(name,[]):
            if obj['Type']!='LevelStreamingAlwaysLoaded':continue
            props=obj.get('Properties',{});dest=props.get('WorldAsset',{}).get('AssetPathName','').split('.')[0]
            if not dest:continue
            if dest not in arrays:missing.append(dest);continue
            if dest not in active:active[dest]=active[name]@transform(props.get('LevelTransform'));queue.append(dest)
    for name in scene['source']['levels']:
        if '/_Generated_/' in name:active[name]=active.get(name.split('/_Generated_/')[0],np.eye(4))
    shapes={};rows=[];channel_owners={'Pawn':set(),'PortalLauncher':set()};errors=[];counts=0
    for row in clean(manifest.get('blockingVolumes',[])):
        package=actual_to_virtual.get(row['package'])
        if package not in active:continue
        counts+=1;channels=[ch for ch in channel_owners if blocks(row,ch)]
        if not channels:continue
        verts,idx,kind=simple_collision({'body':row.get('body')},np.zeros((0,3)),np.zeros((0,3),dtype=np.uint32))
        if not len(idx):errors.append(row['name']);continue
        key=row['name'];shapes[key]=(verts,idx);owner=len(rows)
        rows.append({'id':owner,'mesh':key,'matrix':(active[package]@transform(row['transform'])).tolist()})
        for channel in channels:channel_owners[channel].add(owner)
    trees={ch:InstanceBVH(shapes,[r for r in rows if r['id'] in owners]) for ch,owners in channel_owners.items()}
    coverage=scene['source'].setdefault('coverage',{})
    expected=sum('BlockingVolume' in o['Type'] for name in active for o in arrays.get(name,[]))
    coverage.update(blockingVolumesExpected=expected,blockingVolumesRead=counts,missingStreaming=sorted(set(missing)),blockingErrors=errors)
    known=manifest.get('blockingVersion')==1 and expected==counts and not errors
    scene['source']['edgesBeforeBlockingVolumes']=scene['source'].get('edgesBeforeBlockingVolumes',len(scene['edges']))
    if missing or not known:
        scene['edges']=[];scene['source']['geometryUsable']=False
        issue={'scope':'coverage','error':'Required streaming levels or blocking brushes are missing; routes withheld.'}
        if issue not in scene['issues']:scene['issues'].append(issue)
    else:
        edges=[];radius=scene['model'].get('navRadius',.45)
        for edge in scene['edges']:
            path=np.asarray(edge['path'],dtype=float)
            if edge['kind']=='portal':
                blocked=trees['PortalLauncher'].hit(path[1],path[2]) is not None
            else:
                delta=path[-1]-path[0];length=np.linalg.norm(delta[:2]);side=np.array([-delta[1],delta[0],0])*radius/max(length,1e-6)
                offsets=(np.zeros(3),side,-side,np.array([0,0,.8]),np.array([0,0,-.5])) if edge['kind']!='walk' else tuple(v+[0,0,h] for v in (np.zeros(3),side,-side) for h in (.4,.9,1.6))
                blocked=any(trees['Pawn'].hit(a+offset,b+offset) is not None for a,b in zip(path,path[1:]) for offset in offsets)
            if not blocked:edges.append(edge)
        scene['edges']=edges
    scene['source']['blockingFilteredEdges']=scene['source']['edgesBeforeBlockingVolumes']-len(scene['edges'])
    scene['finalizeVersion']=1
    return scene


def save(scene,path):
    scene.pop('revision',None);scene['revision']=hashlib.sha256(json.dumps(scene,sort_keys=True).encode()).hexdigest()[:16]
    temporary=path.with_suffix('.json.tmp');temporary.write_text(json.dumps(scene,separators=(',',':'),allow_nan=False));temporary.replace(path)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('maps',nargs='*');parser.add_argument('--all',action='store_true');args=parser.parse_args()
    paths=sorted((ROOT/'data/scenes').glob('MAP_*.json')) if args.all else [ROOT/'data/scenes'/(m+'.json') for m in args.maps]
    for path in paths:
        manifest=json.loads((ROOT/'data/extracted'/(path.stem+'.json')).read_text());scene=finalize(json.loads(path.read_text()),manifest,ROOT/'data/extracted');save(scene,path)
        print(path.stem,len(scene['edges']),'edges',scene['source']['coverage'],flush=True)
