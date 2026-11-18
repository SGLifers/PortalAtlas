import unittest
import json
from pathlib import Path

from server.map_variants import MAP_VARIANTS,expanded_features,feature_root


class MapVariantTests(unittest.TestCase):
    def test_simulation_bundle_exposes_six_separate_maps_only_when_installed(self):
        self.assertEqual(expanded_features({'MAP_Academy'}),['MAP_Academy'])
        maps=expanded_features({'MAP_Academy','MAP_Simulation'})
        self.assertEqual(len(maps),7);self.assertNotIn('MAP_Simulation',maps)
        self.assertEqual(len({root for feature,root in MAP_VARIANTS.values()}),6)
        for mid,(feature,root) in MAP_VARIANTS.items():
            self.assertIn(mid,maps);self.assertEqual(feature_root(mid),(feature,root))
            self.assertTrue(root.startswith('/MAP_Simulation/'))
            self.assertTrue(root.endswith('_Main'))
        self.assertEqual(feature_root('MAP_Academy'),('MAP_Academy',None))

    def test_variant_id_cannot_overwrite_an_unrelated_map(self):
        from tools.compile_scene import compile_scene
        with self.assertRaisesRegex(ValueError,'does not match'):
            compile_scene('MAP_Simulation',Path('/not-read'),Path('/not-written'),'/MAP_Simulation/SimulationCharlie/SimulationCharlie_Main','MAP_Academy')

    def test_imported_variants_keep_portals_and_streamed_levels_in_their_selected_root(self):
        directory=Path(__file__).resolve().parents[1]/'data/scenes'
        if not all((directory/(mid+'.json')).exists() for mid in MAP_VARIANTS):self.skipTest('Simulation roots not imported locally')
        for mid,(feature,root) in MAP_VARIANTS.items():
            scene=json.loads((directory/(mid+'.json')).read_text())
            self.assertEqual(scene['id'],mid);self.assertEqual(scene['rootPackage'],root)
            self.assertEqual(scene['source']['feature'],feature);self.assertTrue(scene['nodes'])
            prefix=root.rsplit('/',1)[0]+'/'
            self.assertTrue(all(level.startswith(prefix) for level in scene['source']['levels']))
            self.assertTrue(all(node['package'] in scene['source']['levels'] for node in scene['nodes']))
