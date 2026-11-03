import unittest
import numpy as np
from server.geometry import InstanceBVH,TriangleBVH,points,transform
from tools.collision import BOX_INDICES,box,simple_collision,collision_policy


class InstancedGeometryTests(unittest.TestCase):
    def test_shared_mesh_matches_expanded_world_geometry(self):
        vertices=box([-1,-1,-1],[1,1,1]);indices=BOX_INDICES
        a=transform({'Translation':{'X':100,'Y':200,'Z':300},'Rotation':{'Z':.3826834324,'W':.9238795325},'Scale3D':{'X':2,'Y':.5,'Z':1}})
        b=transform({'Translation':{'X':100,'Y':200,'Z':600},'Scale3D':{'X':-1,'Y':1,'Z':.5}})
        rows=[{'id':10,'mesh':'cube','matrix':a.tolist()},{'id':20,'mesh':'cube','matrix':b.tolist()}]
        instanced=InstanceBVH({'cube':(vertices,indices)},rows)
        expanded=TriangleBVH(np.concatenate([points(vertices,a)[indices],points(vertices,b)[indices]]),[10]*12+[20]*12)
        for start,end in [([1,2,10],[1,2,-1]),([-10,2,3],[10,2,3]),([1,10,6],[1,-10,6]),([20,20,20],[30,30,30])]:
            for ignore in [(),(20,)]:
                h=instanced.hit(start,end,ignore);expected=expanded.hit(start,end,ignore)
                self.assertEqual(h is None,expected is None)
                if h:
                    self.assertAlmostEqual(h[0],expected[0],places=4);np.testing.assert_allclose(h[1],expected[1],atol=1e-5);self.assertEqual(h[3],expected[3])
    def test_empty_instance_scene(self):self.assertIsNone(InstanceBVH({},[]).hit([0,0,0],[1,1,1]))
    def test_zero_scale_preserves_flattened_collision_plane(self):
        vertices=box([-1,-1,-1],[1,1,1]);matrix=np.eye(4);matrix[2,2]=0;matrix[2,3]=3
        bvh=InstanceBVH({'cube':(vertices,BOX_INDICES)},[{'id':7,'mesh':'cube','matrix':matrix.tolist()}])
        hit=bvh.hit([0,0,6],[0,0,0]);self.assertIsNotNone(hit)
        self.assertAlmostEqual(hit[0],3);self.assertEqual(hit[3],7)
    def test_serialized_simple_box_dimensions_and_center(self):
        meta={'body':{'Properties':{'AggGeom':{'BoxElems':[{'X':200,'Y':400,'Z':100,'Center':{'X':100}}]}}}}
        vertices,indices,kind=simple_collision(meta,np.zeros((0,3)),np.zeros((0,3),dtype=np.uint32))
        self.assertEqual(kind,'simple-collision');np.testing.assert_allclose(vertices.min(axis=0),[0,-2,-.5]);np.testing.assert_allclose(vertices.max(axis=0),[2,2,.5]);self.assertEqual(len(indices),12)
    def test_complex_collision_setting_keeps_render_mesh(self):
        v=np.array([[0,0,0],[1,0,0],[0,1,0]]);idx=np.array([[0,1,2]])
        out=simple_collision({'body':{'Properties':{'CollisionTraceFlag':'CTF_UseComplexAsSimple'}}},v,idx)
        self.assertEqual(out[2],'render-proxy');self.assertIs(out[0],v)
    def test_no_collision_default_and_profile_override(self):
        meta={'body':{'Properties':{'DefaultInstance':{'CollisionProfileName':'NoCollision','CollisionEnabled':'Unknown::0'}}}}
        self.assertFalse(collision_policy({},meta));self.assertTrue(collision_policy({'collision':{'CollisionProfileName':'BlockAll'}},meta))
    def test_missing_convex_topology_uses_conservative_bounds(self):
        vertices=[{'X':0,'Y':0,'Z':0},{'X':100,'Y':0,'Z':0},{'X':0,'Y':100,'Z':0},{'X':0,'Y':0,'Z':100}]
        out=simple_collision({'body':{'Properties':{'AggGeom':{'ConvexElems':[{'VertexData':vertices}]}}}},None,None)
        self.assertEqual(out[2],'simple-bounds-proxy');self.assertEqual(len(out[0]),8)


if __name__=='__main__':unittest.main()
