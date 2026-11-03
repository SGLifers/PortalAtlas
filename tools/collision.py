"""Recover simple collision convexes and conservative primitive bounds."""
import math
import numpy as np
from server.geometry import vector,transform,points

BOX_INDICES=np.array([[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]],dtype=np.uint32)


def box(lo,hi):return np.array([[x,y,z] for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])])


def rotation(rot):
    sp,sy,sr=[math.sin(math.radians(rot.get(k,0))/2) for k in ('Pitch','Yaw','Roll')]
    cp,cy,cr=[math.cos(math.radians(rot.get(k,0))/2) for k in ('Pitch','Yaw','Roll')]
    return {'X':cr*sp*sy-sr*cp*cy,'Y':-cr*sp*cy-sr*cp*sy,'Z':cr*cp*sy-sr*sp*cy,'W':cr*cp*cy+sr*sp*sy}


def simple_collision(meta,render_vertices,render_indices):
    body=meta.get('body') or {};props=body.get('Properties',{})
    trace=str(props.get('CollisionTraceFlag',''))
    if trace.endswith('UseComplexAsSimple') or trace.endswith('::3'):
        return render_vertices,render_indices,'render-proxy'
    agg=props.get('AggGeom') or {};vertices=[];indices=[];count=0;approximate=False
    if any(v for k,v in agg.items() if k not in ('ConvexElems','BoxElems','SphereElems','SphylElems') and isinstance(v,list)):
        return render_vertices,render_indices,'render-proxy'
    for elem in agg.get('ConvexElems',[]):
        verts=np.array([vector(v)/100 for v in elem.get('VertexData',[])])
        if len(verts)<4:continue
        idx=np.asarray(elem.get('IndexData',[]),dtype=np.uint32)
        if len(idx)<3 or len(idx)%3 or idx.max(initial=0)>=len(verts):
            verts=box(verts.min(axis=0),verts.max(axis=0));idx=BOX_INDICES;approximate=True
        else:idx=idx.reshape(-1,3)
        verts=points(verts,transform(elem.get('Transform')))
        vertices.append(verts);indices.append(idx+count);count+=len(verts)
    for kind in ('BoxElems','SphereElems','SphylElems'):
        for elem in agg.get(kind,[]):
            if kind=='BoxElems':extent=np.array([elem.get(k,0) for k in 'XYZ'])/200
            else:
                radius=elem.get('Radius',0)/100;extent=np.array([radius,radius,radius+elem.get('Length',0)/200]);approximate=True
            if np.any(extent<=0):continue
            m=transform({'Translation':elem.get('Center',{}),'Rotation':rotation(elem.get('Rotation',{}))})
            verts=points(box(-extent,extent),m);vertices.append(verts);indices.append(BOX_INDICES+count);count+=8
    if not vertices:return render_vertices,render_indices,'render-proxy'
    return np.concatenate(vertices),np.concatenate(indices),('simple-bounds-proxy' if approximate else 'simple-collision')


def collision_policy(component,meta):
    body=(meta.get('body') or {}).get('Properties',{});default=body.get('DefaultInstance') or {}
    override=component.get('collision') or {};profile=override.get('CollisionProfileName',default.get('CollisionProfileName',''))
    enabled=str(override.get('CollisionEnabled',default.get('CollisionEnabled','') if profile==default.get('CollisionProfileName','') else ''))
    if profile in ('NoCollision','OverlapAll','OverlapAllDynamic','Trigger') or enabled in ('Unknown::0','Unknown::2','ECollisionEnabled::NoCollision','ECollisionEnabled::PhysicsOnly'):
        return False
    return True
