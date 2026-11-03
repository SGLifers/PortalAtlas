#!/usr/bin/env python3
"""Compile extracted assets into a wall graph and browser scene, in metres."""
import argparse
import hashlib
import json
import math
import pathlib
import re
import sys
import time

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from server.geometry import TriangleBVH, transform, vector, points
import numpy as np


def clean(value):
    if isinstance(value,dict):return {re.sub(r'\[\d+\]$','',k):clean(v) for k,v in value.items()}
    if isinstance(value,list):return [clean(v) for v in value]
    return value


def load_mesh(path):
    data=path.read_bytes();count,index_count=np.frombuffer(data,dtype='<u4',count=2)
    vertices=np.frombuffer(data,dtype='<f4',count=int(count)*3,offset=8).reshape(-1,3)/100.
    indices=np.frombuffer(data,dtype='<u4',count=int(index_count),offset=8+int(count)*12).reshape(-1,3)
    return vertices,indices


def source_package(array):
    world=next((x for x in array if x['Type']=='World'),None)
    return world.get('Package') if world else None


def compile_scene(feature, extracted, output):
    started=time.monotonic();manifest=json.loads((extracted/(feature+'.json')).read_text())
    package_data={};path_to_virtual={};virtual_to_path={};issues=list(manifest['errors'])
    for p in manifest['packages']:
        a=clean(json.loads((extracted/'packages'/(p['id']+'.json')).read_text()))
        virtual=source_package(a)
        if virtual:package_data[virtual]=a;path_to_virtual[p['path']]=virtual;virtual_to_path[virtual]=p['path']
    roots=[v for v in package_data if 'main' in v.rsplit('/',1)[-1].lower() and '/Sublevels/' not in v]
    if not roots:roots=[min(package_data,key=lambda v:(v.count('/'),len(v)))] if package_data else []
    root=min(roots,key=lambda v:(v.count('/'),len(v))) if roots else ''
    active={root:np.eye(4)} if root else {};queue=[root] if root else []
    while queue:
        v=queue.pop(0)
        for obj in package_data.get(v,[]):
            if obj['Type']!='LevelStreamingAlwaysLoaded':continue
            prop=obj.get('Properties',{});dest=prop.get('WorldAsset',{}).get('AssetPathName','').split('.')[0]
            if dest and dest in package_data and dest not in active:
                active[dest]=active[v]@transform(prop.get('LevelTransform'));queue.append(dest)
    # World Partition generated cells are cooked geometry rather than optional
    # menu/lighting sublevels. Preserve their source package paths explicitly.
    generated=[v for v in package_data if '/_Generated_/' in v]
    if generated:
        for v in generated:active.setdefault(v,np.eye(4))
    if len(active)==1 and len(package_data)>1 and not generated:
        issues.append({'scope':'streaming','error':'Only the root level is selected; no additional levels were silently enabled.'})
    meshes={m['id']:m for m in manifest['meshes']};mesh_cache={}
    def mesh(mid):
        if mid not in mesh_cache:mesh_cache[mid]=load_mesh(extracted/'meshes'/(mid+'.bin'))
        return mesh_cache[mid]
    comps=[];by_name={}
    for c in manifest.get('components',[]):
        v=path_to_virtual.get(c['package'])
        if v not in active or c['mesh'] not in meshes:continue
        matrix=active[v]@transform(c['transform']);c=clean(c)
        rows=c.get('instances') or [None]
        for j,inst in enumerate(rows):
            m=matrix@transform(inst['TransformData']) if inst else matrix
            record={'id':len(comps),'name':c['name'],'mesh':c['mesh'],'matrix':m.tolist(),
                    'visible':c['visible'],'package':v,'collision':c.get('collisionEnabled')}
            comps.append(record)
            if j==0:by_name[c['name']]=record
    nodes=[]
    for wall in sorted(manifest.get('walls',[]),key=lambda w:(w['package'],w['name'])):
        v=path_to_virtual.get(wall['package'])
        if v not in active:continue
        c=by_name.get(wall['component']);props=clean(wall['properties'])
        if c is None:issues.append({'wall':wall['name'],'error':'No resolved wall mesh instance'});continue
        m=np.asarray(c['matrix']);local_vertices,_=mesh(c['mesh']);lo=local_vertices.min(axis=0);hi=local_vertices.max(axis=0)
        center=points(np.array([[(hi[0]),(lo[1]+hi[1])/2,(lo[2]+hi[2])/2]]),m)[0]
        if isinstance(props.get('WallOrigin'),dict):center=points(np.array([vector(props['WallOrigin'])/100]),active[v])[0]
        normal=m[:3,0];normal=normal/np.linalg.norm(normal);right=m[:3,1];right=right/np.linalg.norm(right);up=m[:3,2];up=up/np.linalg.norm(up)
        width=float((hi[1]-lo[1])*np.linalg.norm(m[:3,1]));height=float((hi[2]-lo[2])*np.linalg.norm(m[:3,2]))
        if isinstance(props.get('WallScale'),dict):
            dims=vector(props['WallScale'])/100; width=2*abs(dims[1])*np.linalg.norm(active[v][:3,1]);height=2*abs(dims[2])*np.linalg.norm(active[v][:3,2])
        n={'id':wall['id'],'label':f'P{len(nodes)+1:02d}','name':wall['name'],'type':wall['type'],
           'position':center.tolist(),'normal':normal.tolist(),'right':right.tolist(),'up':up.tolist(),
           'width':round(width,3),'height':round(height,3),'owner':c['id'],
           'sides':[1,-1] if props.get('bIsDoubleSided',False) else [1],
           'launch':bool(props.get('bLaunchPortalWall',False)),
           'launchSpeed':props.get('LaunchSpeed'),'minLaunchSpeed':props.get('MinSpeedToLaunch'),
           'enabled':props.get('bValidForPlayer',True),'package':v,'source':wall['package'],'properties':props}
        nodes.append(n)
    if nodes:
        positions=np.array([n['position'] for n in nodes]);bounds_lo=positions.min(axis=0)-25;bounds_hi=positions.max(axis=0)+25
    else:bounds_lo=np.array([-1000]*3);bounds_hi=np.array([1000]*3)
    tri_chunks=[];owner_chunks=[];geometry=[];tri_count=0
    for c in comps:
        meta=meshes[c['mesh']];path=meta['path'];lower=path.lower()
        if any(s in lower for s in ['/crowd/','/vfx/','/lighting/','/sky/','skydome','/mainmenu/']):continue
        verts,idx=mesh(c['mesh']);m=np.asarray(c['matrix']);wv=points(verts,m)
        if np.any(wv.max(axis=0)<bounds_lo) or np.any(wv.min(axis=0)>bounds_hi):continue
        profile=(c.get('collision') or {}).get('CollisionProfileName','')
        collision_enabled=(c.get('collision') or {}).get('CollisionEnabled')
        occludes=profile not in ('NoCollision','OverlapAll','OverlapAllDynamic','Trigger') and collision_enabled not in ('Unknown::0','ECollisionEnabled::NoCollision')
        # Render meshes are an explicit geometric proxy; physics collision and
        # game-specific trace channels can differ. Never label this game-verified.
        if occludes:
            tris=wv[idx];tri_chunks.append(tris.astype(np.float32));owner_chunks.append(np.full(len(idx),c['id'],dtype=np.int32));tri_count+=len(idx)
        geometry.append({k:v for k,v in c.items() if k not in ('collision',)}|{'occludes':occludes})
    print(feature,'walls',len(nodes),'geometry instances',len(geometry),'ray triangles',tri_count,flush=True)
    triangles=np.concatenate(tri_chunks) if tri_chunks else np.empty((0,3,3),dtype=np.float32)
    owners=np.concatenate(owner_chunks) if owner_chunks else np.empty(0,dtype=np.int32)
    bvh=TriangleBVH(triangles,owners);edges=[];ground={}
    for n in nodes:
        for side in n['sides']:
            p=np.array(n['position']);normal=np.array(n['normal'])*side
            eye=p+normal*1.1
            hit=bvh.hit(eye+np.array([0,0,.3]),eye-np.array([0,0,4.]),ignore=[n['owner']])
            if hit is not None and abs(hit[2][2])>.65:ground[(n['id'],side)]=hit[1]
    def add(a,b,side_a,side_b,kind,path,seconds,difficulty,**extra):
        edges.append({'id':f'e{len(edges)}','source':a['id'],'target':b['id'],'sourceSide':side_a,'targetSide':side_b,
                      'kind':kind,'path':[np.asarray(x).round(5).tolist() for x in path],
                      'seconds':round(seconds,3),'difficulty':round(max(0,min(100,difficulty)),1),
                      'distance':round(float(np.linalg.norm(np.array(b['position'])-a['position'])),3),
                      'validation':'render-geometry checked; timing estimated',**extra})
    for i,a in enumerate(nodes):
        pa=np.array(a['position']);na=np.array(a['normal'])
        for b in nodes:
            if a['id']==b['id'] or not a['enabled'] or not b['enabled']:continue
            pb=np.array(b['position']);nb=np.array(b['normal']);distance=float(np.linalg.norm(pb-pa))
            if distance<.15:continue
            for sa in a['sides']:
                start=pa+na*sa*1.1
                for sb in b['sides']:
                    delta=pb-start;length=float(np.linalg.norm(delta));cosine=float(np.dot(nb*sb,-delta/length))
                    if cosine>.035 and b['width']>.9 and b['height']>1.8:
                        target=pb
                        if bvh.hit(start,target,ignore=[a['owner'],b['owner']]) is None:
                            incidence=math.degrees(math.acos(min(1,cosine)));apparent=math.degrees(2*math.atan(max(.01,min(b['width']-.8,b['height']-1.7))*cosine/(2*length)))
                            difficulty=18+incidence*.45+max(0,12-apparent)*3
                            yaw=math.degrees(math.atan2(delta[1],delta[0]));pitch=math.degrees(math.atan2(delta[2],np.linalg.norm(delta[:2])))
                            add(a,b,sa,sb,'portal',[pa,start,target,pb+nb*sb*1.1],.65+difficulty*.008,difficulty,
                                angle=round(incidence,1),angularSize=round(apparent,2),yaw=round(yaw,1),pitch=round(pitch,1),
                                instruction='Aim at the destination wall, replace the opposite portal, and re-enter the current portal.')
                    ga=ground.get((a['id'],sa));gb=ground.get((b['id'],sb))
                    if ga is None or gb is None:continue
                    horizontal=float(np.linalg.norm((gb-ga)[:2]));dz=float(gb[2]-ga[2])
                    if horizontal>18 or horizontal<.5:continue
                    # Conservative direct walking corridors, with floor support
                    # and three clearance rays. Corners are not inferred.
                    walk=abs(dz)<.45
                    if walk:
                        previous=ga
                        for f in np.linspace(0,1,max(3,int(horizontal/.65))):
                            point=ga*(1-f)+gb*f;h=bvh.hit(point+[0,0,.6],point-[0,0,.8],ignore=[a['owner'],b['owner']])
                            if h is None or abs(h[2][2])<.65 or abs(h[1][2]-previous[2])>.32:walk=False;break
                            previous=h[1]
                        if walk:
                            walk=all(bvh.hit(ga+[0,0,h],gb+[0,0,h],ignore=[a['owner'],b['owner']]) is None for h in (.5,1.,1.7))
                    if walk:
                        add(a,b,sa,sb,'walk',[ga+[0,0,.1],gb+[0,0,.1]],horizontal/6.,8+abs(dz)*12,
                            instruction='Follow the direct floor-supported corridor to the destination wall.')
                    elif horizontal<9 and -.9<dz<.9:
                        # Editable-model defaults: UE-like gravity and jump speed.
                        gravity=9.8;vz=4.2;disc=vz*vz-2*gravity*dz
                        if disc<0:continue
                        duration=(vz+math.sqrt(disc))/gravity
                        if horizontal/duration>7.:continue
                        arc=[ga*(1-f)+gb*f+[0,0,.9+vz*(duration*f)-.5*gravity*(duration*f)**2-dz*f] for f in np.linspace(0,1,18)]
                        if any(bvh.hit(x,y,ignore=[a['owner'],b['owner']]) is not None for x,y in zip(arc,arc[1:])):continue
                        kind='drop' if dz<-.4 else 'jump'
                        add(a,b,sa,sb,kind,arc,duration+.25,40+horizontal/duration*5+abs(dz)*8,
                            instruction='Estimated ballistic movement; verify the landing and timing in game.')
        if i%10==0:print('graph',i,'/',len(nodes),'edges',len(edges),flush=True)
    scene={'id':feature,'name':feature.removeprefix('MAP_').replace('_',' '),'rootPackage':root,
           'nodes':nodes,'edges':edges,'instances':geometry,
           'meshes':[{k:m[k] for k in ('id','path','vertices','triangles','lod','lodForCollision')} for m in manifest['meshes'] if any(c['mesh']==m['id'] for c in geometry)],
           'bounds':{'min':bounds_lo.tolist(),'max':bounds_hi.tolist()},
           'source':{'kind':'installed game assets','image':json.loads((ROOT/'tools/versions.json').read_text())['game_image'],
                     'executableSha256':json.loads((ROOT/'tools/versions.json').read_text())['game_executable_sha256'],
                     'levels':list(active),'packages':len(manifest['packages']),'geometryTriangles':tri_count},
           'model':{'walkSpeed':6.,'airSpeed':7.,'gravity':9.8,'jumpVelocity':4.2,'approachOffset':1.1,
                    'status':'Estimates; not measured in game','scope':'Direct wall-to-wall placements and direct supported movement. No live enemy state or inferred corner routes.'},
           'issues':issues,'generatedSeconds':round(time.monotonic()-started,2)}
    scene['revision']=hashlib.sha256(json.dumps(scene,sort_keys=True).encode()).hexdigest()[:16]
    output.mkdir(parents=True,exist_ok=True);temp=output/(feature+'.json.tmp');temp.write_text(json.dumps(scene,separators=(',',':'),allow_nan=False));temp.replace(output/(feature+'.json'))
    print('DONE',feature,'edges',len(edges),'seconds',scene['generatedSeconds'],flush=True)
    return scene


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('feature');args=parser.parse_args()
    compile_scene(args.feature,ROOT/'data/extracted',ROOT/'data/scenes')
