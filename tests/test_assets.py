"""Optional integration checks on real local assets, never demonstration maps."""
import json
import math
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SCENES=list((ROOT/'data/scenes').glob('MAP_*.json'))


@unittest.skipUnless(SCENES,'Local extracted game data is not in Git')
class AssetIntegrationTests(unittest.TestCase):
    def test_wall_and_graph_invariants(self):
        for path in SCENES:
            with self.subTest(map=path.stem):
                scene=json.loads(path.read_text());nodes={n['id']:n for n in scene['nodes']}
                self.assertEqual(len(nodes),len(scene['nodes']))
                for n in nodes.values():
                    self.assertTrue(all(math.isfinite(x) for x in n['position']))
                    self.assertGreater(n['width'],0);self.assertGreater(n['height'],0)
                    self.assertAlmostEqual(sum(x*x for x in n['normal']),1,places=4)
                for e in scene['edges']:
                    self.assertIn(e['source'],nodes);self.assertIn(e['target'],nodes)
                    self.assertIn(e['sourceSide'],nodes[e['source']]['sides']);self.assertIn(e['targetSide'],nodes[e['target']]['sides'])
                    self.assertGreater(e['seconds'],0);self.assertTrue(0<=e['difficulty']<=100)
                    if e['kind']=='portal':
                        self.assertTrue(0<=e['angle']<90)
                        self.assertGreater(e['angularSize'],0)
    def test_wall_positions_match_serialized_source(self):
        path=ROOT/'data/scenes/MAP_Academy.json'
        if not path.exists():self.skipTest('Academy not imported')
        scene=json.loads(path.read_text());source=json.loads((ROOT/'data/extracted/MAP_Academy.json').read_text());walls={w['id']:w for w in source['walls']}
        for n in scene['nodes']:
            wall=walls[n['id']];origin=wall['properties'].get('WallOrigin')
            if origin:
                for i,axis in enumerate('XYZ'):self.assertAlmostEqual(n['position'][i],origin[axis]/100,places=4)
    def test_required_native_schemas(self):
        mapping=json.loads((ROOT/'data/mappings.json').read_text());schemas={s['name']:s for s in mapping}
        for name in ['Actor','SceneComponent','StaticMeshComponent','PrimitiveComponent','Vector','GF1047PortalWall']:
            self.assertIn(name,schemas)
        self.assertEqual([p['name'] for p in schemas['Vector']['properties']],['X','Y','Z'])
    def test_selected_variant_does_not_mix_generated_worlds(self):
        for path in SCENES:
            scene=json.loads(path.read_text())
            if scene.get('modelVersion',0)<5:continue
            levels=set(scene['source']['levels'])
            for level in levels:
                if '/_Generated_/' in level:self.assertIn(level.split('/_Generated_/')[0],levels,path.stem)
    def test_terrain_coverage_gates_routes(self):
        for path in SCENES:
            scene=json.loads(path.read_text());coverage=scene['source'].get('coverage')
            if not coverage:continue
            if scene['source']['geometryUsable']:
                self.assertEqual(coverage['landscapeExpected'],coverage['landscapeRead'],path.stem)
                self.assertFalse(coverage['terrainErrors']);self.assertFalse(coverage['missingMeshes'])
            else:self.assertEqual(scene['edges'],[],path.stem)


if __name__=='__main__':unittest.main()
