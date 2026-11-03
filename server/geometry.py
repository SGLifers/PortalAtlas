"""Asset-coordinate transforms and a triangle BVH. Unreal centimetres, Z up."""
import math
import numpy as np


def vector(value, default=(0., 0., 0.)):
    if not isinstance(value, dict):
        return np.array(default, dtype=float)
    return np.array([value.get(k, default[i]) for i, k in enumerate('XYZ')], dtype=float)


def transform(value):
    value = value or {}
    q = value.get('Rotation', {})
    x, y, z, w = [q.get(k, 1. if k == 'W' else 0.) for k in 'XYZW']
    norm = math.sqrt(x*x+y*y+z*z+w*w)
    if norm < 1e-8:
        raise ValueError('Invalid asset quaternion')
    x, y, z, w = [a/norm for a in (x,y,z,w)]
    r = np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                  [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                  [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
    result = np.eye(4)
    result[:3,:3] = r * vector(value.get('Scale3D'), (1.,1.,1.))[None,:]
    result[:3,3] = vector(value.get('Translation')) / 100.
    return result


def points(vertices, matrix):
    return vertices @ matrix[:3,:3].T + matrix[:3,3]


class TriangleBVH:
    def __init__(self, triangles, owners=None, leaf_size=40):
        self.triangles = np.asarray(triangles, dtype=np.float32).reshape(-1,3,3)
        self.owners = np.asarray(owners if owners is not None else np.zeros(len(self.triangles)), dtype=np.int32)
        self.nodes = []
        if len(self.triangles):
            self._lo = self.triangles.min(axis=1)
            self._hi = self.triangles.max(axis=1)
            self._centers = (self._lo+self._hi)*.5
            self._build(np.arange(len(self.triangles)),leaf_size)
            del self._lo, self._hi, self._centers

    def _build(self, ids, size):
        lo=self._lo[ids].min(axis=0).tolist(); hi=self._hi[ids].max(axis=0).tolist()
        i=len(self.nodes); self.nodes.append((lo,hi,None,None,ids))
        if len(ids)>size:
            axis=int(np.argmax(np.subtract(hi,lo))); mid=len(ids)//2
            order=np.argpartition(self._centers[ids,axis],mid)
            left=self._build(ids[order[:mid]],size);right=self._build(ids[order[mid:]],size)
            self.nodes[i]=(lo,hi,left,right,None)
        return i

    def hit(self, start, end, ignore=()):
        """Closest nonignored segment hit: distance, point, unit normal, owner."""
        if not self.nodes:
            return None
        start=np.asarray(start,dtype=float); end=np.asarray(end,dtype=float)
        delta=end-start; length=float(np.linalg.norm(delta))
        if length<1e-7:
            return None
        direction=delta/length; inv=[1./x if abs(x)>1e-12 else None for x in direction]
        near=length; best=None
        def entry(index):
            lo,hi,_,_,_=self.nodes[index];t0=0.;t1=near
            for k in range(3):
                if inv[k] is None:
                    if start[k]<lo[k] or start[k]>hi[k]:return None
                else:
                    a=(lo[k]-start[k])*inv[k];b=(hi[k]-start[k])*inv[k]
                    if a>b:a,b=b,a
                    t0=max(t0,a);t1=min(t1,b)
                    if t0>t1:return None
            return t0
        root_entry=entry(0)
        if root_entry is None:return None
        stack=[(root_entry,0)]
        while stack:
            t_enter,i=stack.pop()
            if t_enter>near:continue
            lo,hi,left,right,ids=self.nodes[i]
            if ids is None:
                children=[]
                for child in (left,right):
                    t=entry(child)
                    if t is not None:children.append((t,child))
                # Test nearer geometry first so a nearby occluder prunes distant
                # subtrees while preserving the exact closest segment hit.
                stack.extend(sorted(children,reverse=True));continue
            if ignore:
                ids=ids[~np.isin(self.owners[ids],ignore)]
            if not len(ids):continue
            tri=self.triangles[ids];e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0]
            p=np.cross(np.broadcast_to(direction,e2.shape),e2);det=np.einsum('ij,ij->i',e1,p)
            ok=np.abs(det)>1e-9
            with np.errstate(divide='ignore',invalid='ignore'):
                f=1./det;s=start-tri[:,0];u=np.einsum('ij,ij->i',s,p)*f;q=np.cross(s,e1)
                v=q@direction*f;t=np.einsum('ij,ij->i',e2,q)*f
            with np.errstate(invalid='ignore'):
                ok&=(u>=-1e-6)&(v>=-1e-6)&(u+v<=1.000001)&(t>1e-4)&(t<near-1e-4)
            matches=np.flatnonzero(ok)
            if len(matches):
                j=int(matches[np.argmin(t[matches])]);near=float(t[j]);normal=np.cross(e1[j],e2[j]);normal=normal/np.linalg.norm(normal)
                best=(near,start+direction*near,normal,int(self.owners[ids[j]]))
        return best


class InstanceBVH:
    """Two-level acceleration: shared mesh trees + transformed instance bounds.

    Keeps repeated trees/props instanced instead of expanding their triangles in
    world memory. Return values use the same world-space contract as TriangleBVH.
    """
    def __init__(self, shapes, instances):
        self.shapes={key:TriangleBVH(vertices[indices]) for key,(vertices,indices) in shapes.items()}
        self.instances=[];lo=[];hi=[];self.nodes=[]
        for row in instances:
            tree=self.shapes[row['mesh']]
            if not tree.nodes:continue
            matrix=np.asarray(row['matrix'],dtype=float);inverse=np.linalg.inv(matrix)
            a,b=tree.nodes[0][:2]
            corners=np.array([[x,y,z] for x in (a[0],b[0]) for y in (a[1],b[1]) for z in (a[2],b[2])])
            world_points=points(corners,matrix)
            lo.append(world_points.min(axis=0));hi.append(world_points.max(axis=0))
            self.instances.append((row['id'],row['mesh'],matrix,inverse))
        if not self.instances:return
        self._lo=np.asarray(lo);self._hi=np.asarray(hi);self._centers=(self._lo+self._hi)*.5
        self._build(np.arange(len(self.instances)),8)
        del self._lo,self._hi,self._centers

    _build=TriangleBVH._build

    def hit(self,start,end,ignore=()):
        if not self.nodes:return None
        start=np.asarray(start,dtype=float);end=np.asarray(end,dtype=float);delta=end-start
        length=float(np.linalg.norm(delta))
        if length<1e-7:return None
        direction=delta/length;inv=[1./v if abs(v)>1e-12 else None for v in direction]
        near=length;best=None;ignored=set(ignore)
        def entry(index):
            lo,hi,_,_,_=self.nodes[index];t0=0.;t1=near
            for k in range(3):
                if inv[k] is None:
                    if start[k]<lo[k] or start[k]>hi[k]:return None
                else:
                    a=(lo[k]-start[k])*inv[k];b=(hi[k]-start[k])*inv[k]
                    if a>b:a,b=b,a
                    t0=max(t0,a);t1=min(t1,b)
                    if t0>t1:return None
            return t0
        root=entry(0)
        if root is None:return None
        stack=[(root,0)]
        while stack:
            t_enter,i=stack.pop()
            if t_enter>near:continue
            _,_,left,right,ids=self.nodes[i]
            if ids is None:
                children=[]
                for child in (left,right):
                    t=entry(child)
                    if t is not None:children.append((t,child))
                stack.extend(sorted(children,reverse=True));continue
            for k in ids:
                owner,key,matrix,inverse=self.instances[k]
                if owner in ignored:continue
                local_start=inverse[:3,:3]@start+inverse[:3,3]
                local_end=inverse[:3,:3]@(start+direction*near)+inverse[:3,3]
                hit=self.shapes[key].hit(local_start,local_end)
                if hit is None:continue
                point=matrix[:3,:3]@hit[1]+matrix[:3,3]
                distance=float(np.dot(point-start,direction))
                if not 1e-4<distance<near-1e-4:continue
                normal=inverse[:3,:3].T@hit[2];normal/=np.linalg.norm(normal)
                near=distance;best=(distance,point,normal,owner)
        return best
