import math
import unittest
import warnings
import numpy as np
from server.geometry import TriangleBVH, transform, points


class GeometryTests(unittest.TestCase):
    def test_unreal_quaternion_and_centimetres(self):
        m=transform({'Translation':{'X':100,'Y':200,'Z':300},'Rotation':{'Z':math.sqrt(.5),'W':math.sqrt(.5)},'Scale3D':{'X':2,'Y':-1,'Z':1}})
        np.testing.assert_allclose(points(np.array([[1,0,0],[0,1,0]]),m),[[1,4,3],[2,2,3]],atol=1e-6)
    def test_invalid_quaternion_rejected(self):
        with self.assertRaises(ValueError):transform({'Rotation':{'W':0}})
    def test_nearest_hit_and_ignored_instance(self):
        tri=np.array([[[0,0,0],[2,0,0],[0,2,0]],[[0,0,1],[2,0,1],[0,2,1]]])
        bvh=TriangleBVH(tri,[10,20],leaf_size=1)
        h=bvh.hit([.2,.2,2],[.2,.2,-2]);self.assertEqual(h[3],20);self.assertAlmostEqual(h[0],1)
        h=bvh.hit([.2,.2,2],[.2,.2,-2],ignore=[20]);self.assertEqual(h[3],10);self.assertAlmostEqual(h[0],2)
    def test_back_faces_occlude_and_segment_has_finite_extent(self):
        bvh=TriangleBVH([[[0,0,0],[2,0,0],[0,2,0]]])
        self.assertIsNotNone(bvh.hit([.2,.2,-1],[.2,.2,1]))
        self.assertIsNone(bvh.hit([.2,.2,2],[.2,.2,1]))
        self.assertIsNone(bvh.hit([3,3,-1],[3,3,1]))
    def test_parallel_and_degenerate_triangles_do_not_warn_or_hit(self):
        bvh=TriangleBVH([[[0,0,0],[0,0,0],[0,0,0]],[[0,0,0],[2,0,0],[0,2,0]]])
        with warnings.catch_warnings():
            warnings.simplefilter('error');self.assertIsNone(bvh.hit([0,0,1],[1,0,1]))
    def test_empty_geometry_is_explicit(self):self.assertIsNone(TriangleBVH([]).hit([0,0,0],[1,1,1]))


if __name__=='__main__':unittest.main()
