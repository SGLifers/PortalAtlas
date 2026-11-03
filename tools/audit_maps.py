#!/usr/bin/env python3
"""Audit compiled real-asset graphs and their browser buffers without a game run."""
import collections
import json
import math
import pathlib
import struct
import sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.import_maps import available,EXCLUDED


def audit(path):
    scene=json.loads(path.read_text());errors=[];nodes={n['id']:n for n in scene['nodes']}
    def check(condition,message):
        if not condition:errors.append(message)
    check(scene.get('modelVersion',0)>=5,'Outdated compiled model')
    check(len(nodes)==len(scene['nodes']),'Duplicate wall IDs')
    levels=set(scene['source']['levels'])
    for level in levels:
        if '/_Generated_/' in level:check(level.split('/_Generated_/')[0] in levels,'Mixed root variants')
    coverage=scene['source'].get('coverage',{})
    if scene['source'].get('geometryUsable'):
        check(coverage.get('landscapeExpected')==coverage.get('landscapeRead'),'Missing terrain')
        for key in ('terrainErrors','missingMeshes','componentErrors','unsupportedProceduralSections'):check(not coverage.get(key),key)
    else:check(not scene['edges'],'Incomplete geometry exposes routes')
    incoming=collections.Counter();outgoing=collections.Counter();kinds=collections.Counter()
    for n in nodes.values():
        check(all(math.isfinite(x) for x in n['position']),'Nonfinite wall position')
        check(abs(sum(x*x for x in n['normal'])-1)<1e-4,'Nonunit wall normal')
        check(n['width']>0 and n['height']>0,'Invalid wall aperture')
    for edge in scene['edges']:
        a=nodes.get(edge['source']);b=nodes.get(edge['target'])
        check(a is not None and b is not None,'Missing edge endpoint')
        if a and b:
            check(edge['sourceSide'] in a['sides'] and edge['targetSide'] in b['sides'],'Invalid face state')
            check(a['enabled'] and b['enabled'],'Disabled wall used by graph')
        check(edge['seconds']>0 and 0<=edge['difficulty']<=100,'Invalid edge cost')
        check(all(math.isfinite(v) for p in edge['path'] for v in p),'Nonfinite edge path')
        if edge['kind']=='portal':check(0<=edge['angle']<90 and edge['angularSize']>0,'Invalid aim geometry')
        incoming[edge['target']]+=1;outgoing[edge['source']]+=1;kinds[edge['kind']]+=1
    for mesh in scene['meshes']:
        file=ROOT/'data/extracted'/('proxies' if mesh.get('viewProxy') else 'meshes')/(mesh['id']+'.bin')
        if not file.exists():errors.append('Missing browser buffer '+mesh['id']);continue
        with file.open('rb') as stream:header=stream.read(8)
        if len(header)!=8:errors.append('Truncated browser buffer');continue
        nv,ni=struct.unpack('<II',header);check(file.stat().st_size==8+nv*12+ni*4,'Malformed browser buffer')
    return {'map':scene['id'],'root':scene['rootPackage'],'revision':scene['revision'],'modelVersion':scene.get('modelVersion'),
        'walls':len(nodes),'edges':len(scene['edges']),'edgeKinds':dict(kinds),
        'isolatedWalls':sum(not incoming[n] and not outgoing[n] for n in nodes),
        'terrainPatches':coverage.get('landscapeRead',0),'geometryUsable':scene['source'].get('geometryUsable',False),
        'notes':len(scene['issues']),'errors':sorted(set(errors))}


def main():
    expected=[m for m in available() if m not in EXCLUDED];rows=[];missing=[]
    for mid in expected:
        path=ROOT/'data/scenes'/(mid+'.json')
        if path.exists():rows.append(audit(path))
        else:missing.append(mid)
    report={'maps':rows,'missing':missing,'passed':not missing and all(not r['errors'] for r in rows),
        'scope':'Source coverage, graph invariants and browser buffers; no measured gameplay execution'}
    (ROOT/'data/validation-report.json').write_text(json.dumps(report,indent=2))
    for row in rows:print(row['map'],row['walls'],'walls',row['edges'],'edges','geometry='+str(row['geometryUsable']),row['errors'])
    print('Missing:',', '.join(missing) or 'none')
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
