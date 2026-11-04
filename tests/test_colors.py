import importlib
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

api=importlib.import_module('server.__main__')
ROOT=Path(__file__).resolve().parents[1]


class ColorApiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.data=Path(self.temp.name)
        (self.data/'appearance').mkdir()
        self.patch=patch.object(api,'DATA',self.data);self.patch.start()
        self.scene=patch.object(api,'scene',return_value={'revision':'current'});self.scene.start()
    def tearDown(self):self.scene.stop();self.patch.stop();self.temp.cleanup()
    def write(self,**changes):
        data={'format':'portal-atlas-colors','version':1,'map':'MAP_Test','sceneRevision':'current','materials':{},'meshes':{}}
        data.update(changes);(self.data/'appearance/MAP_Test.json').write_text(json.dumps(data));return data
    def test_missing_colors_do_not_block_neutral_map(self):
        self.assertFalse(api.appearance('MAP_Test')['available'])
    def test_matching_revision_exposes_appearance_without_mutating_scene(self):
        self.write();self.assertTrue(api.appearance('MAP_Test')['available'])
        self.assertEqual(api.scene('MAP_Test'),{'revision':'current'})
    def test_stale_colors_are_withheld(self):
        self.write(sceneRevision='old');self.assertFalse(api.appearance('MAP_Test')['available'])
    def test_wrong_map_or_format_rejected(self):
        for value in [{'map':'MAP_Other'},{'format':'other'},{'version':2}]:
            self.write(**value)
            with self.assertRaises(ValueError):api.appearance('MAP_Test')


@unittest.skipUnless((ROOT/'data/appearance/MAP_Academy.json').is_file(),'Private Academy colors not imported')
class RealColorTests(unittest.TestCase):
    def setUp(self):
        self.colors=json.loads((ROOT/'data/appearance/MAP_Academy.json').read_text())
        self.scene=json.loads((ROOT/'data/scenes/MAP_Academy.json').read_text())
    def test_colors_have_asset_parameter_provenance_and_linear_values(self):
        colored=[m for m in self.colors['materials'].values() if 'colorLinear' in m]
        self.assertGreater(len(colored),0)
        for m in colored:
            self.assertTrue(m['sourceAsset'].startswith('/'));self.assertTrue(m['sourceParameter'])
            self.assertIn(m['method'],('parameter','layer-parameter'))
            self.assertEqual(len(m['colorLinear']),3)
            self.assertTrue(all(math.isfinite(v) and 0<=v<=1 for v in m['colorLinear']))
    def test_sections_cover_the_existing_geometry_exactly(self):
        self.assertEqual(self.colors['sceneRevision'],self.scene['revision'])
        ids={m['id'] for m in self.scene['meshes']}
        for mid,row in self.colors['meshes'].items():
            self.assertIn(mid,ids)
            with (ROOT/'data/extracted/meshes'/f'{mid}.bin').open('rb') as f:vertices,indices=struct.unpack('<II',f.read(8))
            self.assertEqual((row['vertices'],row['indexCount']),(vertices,indices))
            end=0
            for section in row['sections']:
                self.assertEqual(section['start'],end);self.assertEqual(section['count']%3,0)
                self.assertGreaterEqual(section['slot'],0);end+=section['count']
            self.assertEqual(end,indices)
    def test_component_override_materials_are_preserved(self):
        self.assertTrue(self.colors['components'])
        self.assertTrue(all(mid is None or mid in self.colors['materials'] for slots in self.colors['components'].values() for mid in slots))
        self.assertEqual(self.colors['errors'],[])


@unittest.skipUnless((ROOT/'data/color-import-report.json').is_file(),'Private color rollout not imported')
class RolloutColorTests(unittest.TestCase):
    def test_every_standalone_map_has_valid_current_appearance(self):
        from tools.audit_colors import audit,ready_maps
        for mid in ready_maps(ROOT):
            with self.subTest(map=mid):
                scene=json.loads((ROOT/'data/scenes'/f'{mid}.json').read_text())
                colors=json.loads((ROOT/'data/appearance'/f'{mid}.json').read_text())
                result=audit(scene,colors,ROOT/'data/extracted')
                self.assertTrue(result['passed'],result['errors'])
                self.assertGreater(result['resolvedMaterials'],0)
                self.assertEqual(colors['coverage']['coloredTriangles'],result['coloredTriangles'])
                self.assertEqual(colors['coverage']['visibleTriangles'],result['visibleTriangles'])


if __name__=='__main__':unittest.main()
