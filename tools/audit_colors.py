#!/usr/bin/env python3
"""Validate asset-color sidecars against real scene buffers and measure coverage."""
import argparse
import json
import math
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parents[1]


def ready_maps(root=ROOT):
    return [path.stem for path in sorted((root/'data/scenes').glob('MAP_*.json'))
            if '/Sublevels/' not in json.loads(path.read_text()).get('rootPackage','')]


def audit(scene,colors,buffer_root):
    errors=[]
    def check(condition,message):
        if not condition:errors.append(message)
    check(colors.get('format')=='portal-atlas-colors' and colors.get('version')==1,'Invalid color format/version')
    check(colors.get('map')==scene['id'],'Wrong map')
    check(colors.get('sceneRevision')==scene['revision'],'Stale scene revision')
    materials=colors.get('materials',{});meshes=colors.get('meshes',{});components=colors.get('components',{})
    if not all(isinstance(value,dict) for value in (materials,meshes,components)):
        return {'passed':False,'errors':errors+['Invalid material/mesh/component tables']}
    resolved=set()
    for mid,material in materials.items():
        if not isinstance(material,dict):errors.append('Invalid material '+mid);continue
        check(not material.get('error'),'Material export error: '+mid)
        if 'colorLinear' not in material:continue
        rgb=material['colorLinear']
        valid=isinstance(rgb,list) and len(rgb)==3 and all(type(v) in (float,int) and math.isfinite(v) and 0<=v<=1 for v in rgb)
        check(valid,'Invalid linear color: '+mid)
        check(isinstance(material.get('sourceAsset'),str) and material['sourceAsset'].startswith('/'),'Missing color asset provenance: '+mid)
        check(bool(material.get('sourceParameter')) and material.get('method') in ('parameter','layer-parameter'),'Missing parameter provenance: '+mid)
        if valid:resolved.add(mid)
    source_meshes={row['id']:row for row in scene['meshes']}
    expected={mid for mid,row in source_meshes.items() if not row.get('viewProxy')}
    triangle_counts={row['id']:row['triangles'] for row in scene['meshes']}
    for row in scene['meshes']:
        if not row.get('viewProxy'):continue
        try:
            path=Path(buffer_root)/'proxies'/f"{row['id']}.bin"
            with path.open('rb') as stream:vertices,indices=struct.unpack('<II',stream.read(8))
            check(path.stat().st_size==8+vertices*12+indices*4 and indices%3==0,'Malformed proxy buffer: '+row['id'])
            triangle_counts[row['id']]=indices//3
        except (OSError,struct.error):errors.append('Unreadable proxy buffer: '+row['id'])
    check(expected<=set(meshes) and set(meshes)<=set(source_meshes),'Appearance meshes differ from scene meshes')
    for mid,row in meshes.items():
        if mid not in source_meshes:continue
        try:
            source=source_meshes[mid];proxy=source.get('viewProxy',False)
            path=Path(buffer_root)/('proxies' if proxy else 'meshes')/f'{mid}.bin'
            with path.open('rb') as stream:vertices,indices=struct.unpack('<II',stream.read(8))
            check(path.stat().st_size==8+vertices*12+indices*4,'Malformed mesh buffer: '+mid)
            check(row['vertices']==vertices and row['indexCount']==indices,'Buffer dimensions differ: '+mid)
            check((proxy or indices==source['triangles']*3) and row.get('lod')==source['lod'],'Scene LOD differs: '+mid)
            slots=row['slots'];sections=row['sections'];end=0
            if proxy:check(row.get('kind')=='single-material-proxy' and row.get('sourceSlotCount')==1 and len(slots)==1 and all(s['slot']==0 for s in sections),'Ambiguous proxy material assignment: '+mid)
            check(isinstance(slots,list) and len(slots)<=256,'Invalid material slots: '+mid)
            check(all(slot is None or slot in materials for slot in slots),'Unknown mesh material: '+mid)
            for section in sections:
                start,count,slot=section['start'],section['count'],section['slot']
                check(all(type(v) is int for v in (start,count,slot)) and start==end and count>=0 and count%3==0 and 0<=slot<=255,'Invalid triangle section: '+mid)
                end=start+count
            check(end==indices,'Incomplete triangle sections: '+mid)
        except (OSError,KeyError,TypeError,ValueError,struct.error):errors.append('Unreadable appearance/buffer: '+mid)
    for name,slots in components.items():
        check(isinstance(slots,list) and all(slot is None or slot in materials for slot in slots),'Invalid component override: '+name)
    check(not colors.get('errors'),'Reader mesh/level export errors')
    total=colored=0
    for instance in scene['instances']:
        if not instance.get('visible'):continue
        mid=instance['mesh'];total+=triangle_counts[mid]
        row=meshes.get(mid)
        if not row:continue  # Multi-material proxies deliberately stay neutral.
        overrides=components.get(instance['name'],[])
        try:
            for section in row['sections']:
                slot=section['slot'];base=row['slots'][slot] if slot<len(row['slots']) else None
                material=overrides[slot] if slot<len(overrides) and overrides[slot] is not None else base
                if material in resolved:colored+=section['count']//3
        except (KeyError,IndexError,TypeError):errors.append('Invalid instance appearance: '+instance['name'])
    check(colored<=total,'Colored triangle count exceeds scene geometry')
    return {'map':scene['id'],'name':scene['name'],'sceneRevision':scene['revision'],
            'meshes':len(meshes),'proxyMeshes':sum(bool(m.get('viewProxy')) for m in scene['meshes']),
            'materials':len(materials),'resolvedMaterials':len(resolved),'unresolvedMaterials':len(materials)-len(resolved),
            'componentOverrides':len(components),'visibleTriangles':total,'coloredTriangles':colored,
            'triangleCoveragePercent':round(100*colored/total,1) if total else 0,
            'errors':sorted(set(errors)),'passed':not errors}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('maps',nargs='*');args=parser.parse_args()
    rows=[]
    for mid in args.maps or ready_maps():
        try:
            scene=json.loads((ROOT/'data/scenes'/f'{mid}.json').read_text())
            colors=json.loads((ROOT/'data/appearance'/f'{mid}.json').read_text())
            result=audit(scene,colors,ROOT/'data/extracted')
        except (OSError,ValueError) as error:result={'map':mid,'passed':False,'errors':[str(error)]}
        rows.append(result)
        print(mid,f"{result.get('triangleCoveragePercent',0)}% colored triangles",result['errors'],flush=True)
    report={'passed':all(row['passed'] for row in rows),'maps':rows,
            'scope':'Representative asset parameter colors; triangle counts include neutral proxies, exclude terrain/grid/portal overlays. Not texture or gameplay fidelity.'}
    (ROOT/'data/color-validation-report.json').write_text(json.dumps(report,indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
