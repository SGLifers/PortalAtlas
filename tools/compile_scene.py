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
from server.geometry import InstanceBVH, transform, vector, points
from tools.collision import simple_collision,collision_policy,box
from server.map_variants import feature_root
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


def compile_scene(feature, extracted, output, selected_root=None, scene_id=None):
    scene_id=scene_id or feature
    if not re.fullmatch(r'MAP_[A-Za-z0-9_]+',scene_id):raise ValueError('Invalid scene ID')
    if scene_id!=feature and feature_root(scene_id)!=(feature,selected_root):raise ValueError('Scene ID does not match the selected feature/root')
    started=time.monotonic();manifest=json.loads((extracted/(feature+'.json')).read_text())
    movement_path=ROOT/'data/movement-model.json'
    movement=json.loads(movement_path.read_text()) if movement_path.exists() else {}
    walk_speed=movement.get('walkSpeed',6.)
    radius=movement.get('navRadius',.45)
    step_height=movement.get('navStepHeight',.30)
    package_data={};path_to_virtual={};virtual_to_path={};issues=list(manifest['errors'])
    issues.extend({'scope':'asset reader','error':d['message'],'level':d['level']} for d in manifest.get('diagnostics',[]))
    for p in manifest['packages']:
        a=clean(json.loads((extracted/'packages'/(p['id']+'.json')).read_text()))
        virtual=source_package(a)
        if virtual:package_data[virtual]=a;path_to_virtual[p['path']]=virtual;virtual_to_path[virtual]=p['path']
    base_worlds=[v for v in package_data if '/_Generated_/' not in v and '/Sublevels/' not in v]
    own_worlds=[v for v in base_worlds if v.startswith('/'+feature+'/')]
    roots=[v for v in own_worlds if 'main' in v.rsplit('/',1)[-1].lower()]
    if not roots:
        instances=[v for v in own_worlds if v.rsplit('/',1)[-1].startswith('LI_')]
        # Separate cooked variants must never share a graph. Prefer the highest
        # explicit revision suffix, then preserve the selected root in the scene.
        roots=sorted(instances,key=lambda v:(int(re.search(r'_V(\d+)$',v).group(1)) if re.search(r'_V(\d+)$',v) else 0,v),reverse=True)[:1]
    if not roots:roots=[min(package_data,key=lambda v:(v.count('/'),len(v)))] if package_data else []
    root=min(roots,key=lambda v:(v.count('/'),len(v))) if roots else ''
    if selected_root:
        if selected_root not in base_worlds:raise ValueError('Selected root is not an extracted base world')
        root=selected_root
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
    generated=[v for v in package_data if '/_Generated_/' in v and v.split('/_Generated_/')[0] in active]
    if generated:
        for v in generated:active.setdefault(v,active[v.split('/_Generated_/')[0]])
    if len(active)==1 and len(package_data)>1 and not generated:
        issues.append({'scope':'streaming','error':'Only the root level is selected; no additional levels were silently enabled.'})
    meshes={m['id']:clean(m) for m in manifest['meshes']};mesh_cache={};shape_cache={}
    def mesh(mid):
        if mid not in mesh_cache:mesh_cache[mid]=load_mesh(extracted/'meshes'/(mid+'.bin'))
        return mesh_cache[mid]
    def shape(mid):
        if mid not in shape_cache:
            verts,idx=mesh(mid);shape_cache[mid]=simple_collision(meshes[mid],verts,idx)
        return shape_cache[mid]
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
           'launchSpeed':props.get('LaunchSpeed')/100 if isinstance(props.get('LaunchSpeed'),(int,float)) else None,
           'minLaunchSpeed':props.get('MinSpeedToLaunch'),
           'shape':'circle' if 'Circle' in meshes[c['mesh']]['path'] else 'rectangle',
           'enabled':props.get('bValidForPlayer',True),'package':v,'source':wall['package'],'properties':props}
        nodes.append(n)
    if nodes:
        positions=np.array([n['position'] for n in nodes]);bounds_lo=positions.min(axis=0)-25;bounds_hi=positions.max(axis=0)+25
    else:bounds_lo=np.array([-1000]*3);bounds_hi=np.array([1000]*3)
    geometry=[];collision_instances=[];tri_count=0;render_tri_count=0;wall_owners={n['owner'] for n in nodes}
    for c in comps:
        meta=meshes[c['mesh']];path=meta['path'];lower=path.lower()
        if any(s in lower for s in ['/crowd/','/vfx/','/lighting/','/sky/','skydome','/mainmenu/']):continue
        occludes=collision_policy(c,meta)
        if not occludes and c['id'] not in wall_owners:continue
        verts,idx,kind=shape(c['mesh']);m=np.asarray(c['matrix'])
        corners=points(box(verts.min(axis=0),verts.max(axis=0)),m)
        if np.any(corners.max(axis=0)<bounds_lo) or np.any(corners.min(axis=0)>bounds_hi):continue
        if occludes:
            collision_instances.append(c);tri_count+=len(idx)
        render_tri_count+=meta['triangles']
        geometry.append({k:v for k,v in c.items() if k not in ('collision',)}|{'occludes':occludes})
    used_ids={c['mesh'] for c in collision_instances}
    shapes={mid:shape_cache[mid][:2] for mid in used_ids}
    print(feature,'walls',len(nodes),'geometry instances',len(geometry),'instanced ray triangles',tri_count,'unique ray triangles',sum(len(v[1]) for v in shapes.values()),flush=True)
    bvh=InstanceBVH(shapes,collision_instances);edges=[];ground={};eyes={}
    critical_errors=[d for d in manifest.get('diagnostics',[]) if d['level']=='Error' and any(t in d['message'] for t in ['StaticMesh','FastGeo','PortalWall','SceneComponent','Landscape'])]
    expected_terrain=sum(o['Type']=='LandscapeComponent' for v in active for o in package_data.get(v,[]))
    read_terrain=sum(c['type']=='LandscapeHeightfield' and path_to_virtual.get(c['package']) in active for c in manifest.get('components',[]))
    terrain_errors=[e for e in manifest.get('terrainErrors',[])+manifest.get('errors',[]) if 'terrain' in e and path_to_virtual.get(e['path']) in active]
    missing_meshes=[c['name'] for c in manifest.get('components',[]) if path_to_virtual.get(c['package']) in active and c['mesh'] not in meshes]
    component_errors=[e for e in manifest.get('errors',[]) if path_to_virtual.get(e['path']) in active and any(k in e for k in ('component','fastGeo','wall'))]
    procedural_sections=[o['Name'] for v in active for o in package_data.get(v,[]) if o['Type']=='ProceduralMeshComponent' and o.get('Properties',{}).get('ProcMeshSections')]
    coverage={'landscapeExpected':expected_terrain,'landscapeRead':read_terrain,'terrainErrors':terrain_errors,'missingMeshes':missing_meshes,'componentErrors':component_errors,'unsupportedProceduralSections':procedural_sections}
    geometry_usable=tri_count>0 and not critical_errors and expected_terrain==read_terrain and not terrain_errors and not missing_meshes and not component_errors and not procedural_sections
    if not geometry_usable:issues.append({'scope':'routing','error':'Geometry extraction is incomplete; routes have been withheld.'})
    for n in nodes:
        for side in n['sides']:
            p=np.array(n['position']);normal=np.array(n['normal'])*side
            eye=p+normal*1.1
            hit=bvh.hit(eye+np.array([0,0,.3]),eye-np.array([0,0,4.]),ignore=[n['owner']])
            if hit is not None and abs(hit[2][2])>.65:
                ground[(n['id'],side)]=hit[1]
                eyes[(n['id'],side)]=hit[1]+[0,0,1.7]
            else:eyes[(n['id'],side)]=eye
    def add(a,b,side_a,side_b,kind,path,seconds,difficulty,**extra):
        edges.append({'id':f'e{len(edges)}','source':a['id'],'target':b['id'],'sourceSide':side_a,'targetSide':side_b,
                      'kind':kind,'path':[np.asarray(x).round(5).tolist() for x in path],
                      'seconds':round(seconds,3),'difficulty':round(max(0,min(100,difficulty)),1),
                      'placements':1,
                      'distance':round(float(np.linalg.norm(np.array(b['position'])-a['position'])),3),
                      'validation':'asset collision proxy checked; timing estimated',**extra})
    for i,a in enumerate(nodes):
        if not geometry_usable:break
        pa=np.array(a['position']);na=np.array(a['normal'])
        for b in nodes:
            if a['id']==b['id'] or not a['enabled'] or not b['enabled']:continue
            pb=np.array(b['position']);nb=np.array(b['normal']);distance=float(np.linalg.norm(pb-pa))
            if distance<.15:continue
            for sa in a['sides']:
                start=eyes[(a['id'],sa)]
                for sb in b['sides']:
                    delta=pb-start;length=float(np.linalg.norm(delta));cosine=float(np.dot(nb*sb,-delta/length))
                    if cosine>.035 and b['width']>.9 and b['height']>1.8:
                        target=pb
                        if bvh.hit(start,target,ignore=[a['owner'],b['owner']]) is None:
                            incidence=math.degrees(math.acos(min(1,cosine)));apparent=math.degrees(2*math.atan(max(.01,min(b['width']-.8,b['height']-1.7))*cosine/(2*length)))
                            turn=math.degrees(math.acos(float(np.clip(np.dot(na*sa,delta/length),-1,1))))
                            difficulty=18+incidence*.45+max(0,12-apparent)*3+turn*.10
                            yaw=math.degrees(math.atan2(delta[1],delta[0]));pitch=math.degrees(math.atan2(delta[2],np.linalg.norm(delta[:2])))
                            add(a,b,sa,sb,'portal',[pa,start,target,eyes[(b['id'],sb)]],.65+difficulty*.008+turn/720,difficulty,
                                angle=round(incidence,1),angularSize=round(apparent,2),yaw=round(yaw,1),pitch=round(pitch,1),
                                turn=round(turn,1),
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
                            if h is None or abs(h[2][2])<.65 or abs(h[1][2]-previous[2])>step_height+.01:walk=False;break
                            previous=h[1]
                        if walk:
                            side_offset=np.array([-(gb-ga)[1],(gb-ga)[0],0])/horizontal*radius
                            walk=all(bvh.hit(ga+offset+[0,0,h],gb+offset+[0,0,h],ignore=[a['owner'],b['owner']]) is None for h in (.5,1.,1.7) for offset in (np.zeros(3),side_offset,-side_offset))
                    if walk:
                        add(a,b,sa,sb,'walk',[ga+[0,0,.1],gb+[0,0,.1]],horizontal/walk_speed+.25,8+abs(dz)*12,
                            instruction='Follow the direct floor-supported corridor and place an entry portal on the destination wall.')
                    elif horizontal<9 and -.9<dz<.9:
                        # Editable-model defaults: UE-like gravity and jump speed.
                        gravity=9.8;vz=4.2;disc=vz*vz-2*gravity*dz
                        if disc<0:continue
                        duration=(vz+math.sqrt(disc))/gravity
                        if horizontal/duration>7.:continue
                        arc=[ga*(1-f)+gb*f+[0,0,.9+vz*(duration*f)-.5*gravity*(duration*f)**2-dz*f] for f in np.linspace(0,1,18)]
                        side_offset=np.array([-(gb-ga)[1],(gb-ga)[0],0])/horizontal*radius
                        offsets=(np.zeros(3),side_offset,-side_offset,np.array([0,0,.8]),np.array([0,0,-.5]))
                        if any(bvh.hit(x+offset,y+offset,ignore=[a['owner'],b['owner']]) is not None for x,y in zip(arc,arc[1:]) for offset in offsets):continue
                        kind='drop' if dz<-.4 else 'jump'
                        add(a,b,sa,sb,kind,arc,duration+.25,40+horizontal/duration*5+abs(dz)*8,
                            instruction='Estimated ballistic movement; place an entry portal on the destination wall after landing.')
        if i%10==0:print('graph',i,'/',len(nodes),'edges',len(edges),flush=True)
    # Use the actual simple collision hulls for the large-map overview rather
    # than forcing the browser to render every repeated high-detail tree mesh.
    overview=render_tri_count>8000000
    mesh_rows=[]
    visible_ids={c['mesh'] for c in geometry}
    proxy_dir=extracted/'proxies';proxy_dir.mkdir(exist_ok=True)
    for mid in sorted(visible_ids):
        m=meshes[mid];row={k:m[k] for k in ('id','path','vertices','triangles','lod','lodForCollision')}
        verts,idx,kind=shape(mid);row.update(collisionKind=kind,collisionTriangles=len(idx))
        if overview and kind!='render-proxy':
            with (proxy_dir/(mid+'.bin')).open('wb') as f:
                f.write(np.array([len(verts),idx.size],dtype='<u4').tobytes());f.write((verts*100).astype('<f4').tobytes());f.write(idx.astype('<u4').tobytes())
            row['viewProxy']=True
        mesh_rows.append(row)
    scene={'id':scene_id,'modelVersion':5,'name':scene_id.removeprefix('MAP_').replace('_',' '),'rootPackage':root,
           'nodes':nodes,'edges':edges,'instances':geometry,
           'meshes':mesh_rows,'overviewGeometry':'collision hulls with render fallback' if overview else 'render meshes',
           'bounds':{'min':bounds_lo.tolist(),'max':bounds_hi.tolist()},
           'source':{'kind':'installed game assets','image':json.loads((ROOT/'tools/versions.json').read_text())['game_image'],
                     'executableSha256':json.loads((ROOT/'tools/versions.json').read_text())['game_executable_sha256'],
                     'levels':list(active),'packages':len(manifest['packages']),'geometryTriangles':tri_count,'uniqueGeometryTriangles':sum(len(v[1]) for v in shapes.values()),'geometryUsable':geometry_usable,
                     'coverage':coverage,'availableRoots':base_worlds},
           'model':{'walkSpeed':walk_speed,'airSpeed':7.,'gravity':9.8,'jumpVelocity':4.2,'approachOffset':1.1,
                    'assetParameters':movement,'navRadius':radius,'navStepHeight':step_height,
                    'status':'Timing and jump physics estimated; base walking speed is asset-derived when available',
                    'scope':'Direct wall-to-wall placements and supported movement. Launch arrivals are terminal until their outgoing motion is modeled. No live enemy state or inferred corner routes.'},
           'issues':issues,'generatedSeconds':round(time.monotonic()-started,2)}
    from tools.finalize_scene import finalize
    scene=finalize(scene,manifest,extracted)
    if scene_id!=feature:scene['source']['feature']=feature
    scene['revision']=hashlib.sha256(json.dumps(scene,sort_keys=True).encode()).hexdigest()[:16]
    output.mkdir(parents=True,exist_ok=True);temp=output/(scene_id+'.json.tmp');temp.write_text(json.dumps(scene,separators=(',',':'),allow_nan=False));temp.replace(output/(scene_id+'.json'))
    print('DONE',feature,'edges',len(edges),'seconds',scene['generatedSeconds'],flush=True)
    return scene


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('feature');parser.add_argument('--root');parser.add_argument('--scene-id');args=parser.parse_args()
    compile_scene(args.feature,ROOT/'data/extracted',ROOT/'data/scenes',args.root,args.scene_id)
