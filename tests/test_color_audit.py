import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools.audit_colors import audit,ready_maps
from tools import import_colors


class ColorAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        for folder in ('meshes','proxies'):(self.root/folder).mkdir()
        (self.root/'meshes/mesh.bin').write_bytes(struct.pack('<II',3,6)+bytes(3*12+6*4))
        (self.root/'proxies/proxy.bin').write_bytes(struct.pack('<II',3,3)+bytes(3*12+3*4))
        self.scene={'id':'MAP_Test','name':'Test','revision':'rev','rootPackage':'/MAP_Test/Main',
                    'meshes':[{'id':'mesh','triangles':2,'lod':0},{'id':'proxy','triangles':10000,'lod':0,'viewProxy':True}],
                    'instances':[{'mesh':'mesh','name':'a','visible':True},{'mesh':'mesh','name':'b','visible':True},
                                 {'mesh':'proxy','name':'p','visible':True},{'mesh':'mesh','name':'hidden','visible':False}]}
        self.colors={'format':'portal-atlas-colors','version':1,'map':'MAP_Test','sceneRevision':'rev','errors':[],
                     'materials':{'red':{'colorLinear':[1,0,0],'sourceAsset':'/Test/Material','sourceParameter':'BaseColor','method':'parameter'},'plain':{'method':'unresolved'}},
                     'meshes':{'mesh':{'vertices':3,'indexCount':6,'lod':0,'slots':['red','plain'],'sections':[{'start':0,'count':3,'slot':0},{'start':3,'count':3,'slot':1}]}},
                     'components':{'b':[None,'red']}}
    def tearDown(self):self.temp.cleanup()
    def test_coverage_counts_visible_instances_overrides_and_actual_proxy_triangles(self):
        result=audit(self.scene,self.colors,self.root)
        self.assertTrue(result['passed'],result['errors']);self.assertEqual(result['visibleTriangles'],5)
        self.assertEqual(result['coloredTriangles'],3);self.assertEqual(result['triangleCoveragePercent'],60)
    def test_single_material_proxy_is_supported_but_ambiguous_assignments_fail(self):
        row={'kind':'single-material-proxy','sourceSlotCount':1,'vertices':3,'indexCount':3,'lod':0,'slots':['red'],'sections':[{'start':0,'count':3,'slot':0}]}
        self.colors['meshes']['proxy']=row
        result=audit(self.scene,self.colors,self.root)
        self.assertTrue(result['passed'],result['errors']);self.assertEqual(result['coloredTriangles'],4)
        row['slots'].append('plain');row['sourceSlotCount']=2
        self.assertFalse(audit(self.scene,self.colors,self.root)['passed'])
    def test_invalid_provenance_revision_sections_buffers_and_overrides_are_rejected(self):
        for change in ('revision','color','source','section','buffer','override','export'):
            with self.subTest(change=change):
                data=copy.deepcopy(self.colors)
                if change=='revision':data['sceneRevision']='stale'
                if change=='color':data['materials']['red']['colorLinear']=[float('nan'),0,0]
                if change=='source':data['materials']['red'].pop('sourceAsset')
                if change=='section':data['meshes']['mesh']['sections'][1]['start']=4
                if change=='buffer':data['meshes']['mesh']['vertices']=9
                if change=='override':data['components']['b']=['foreign']
                if change=='export':data['errors']=[{'mesh':'mesh','error':'Missing'}]
                self.assertFalse(audit(self.scene,data,self.root)['passed'])
    def test_bulk_selection_excludes_sublevel_libraries(self):
        directory=self.root/'data/scenes';directory.mkdir(parents=True)
        for name,root in [('MAP_Test','/MAP_Test/Main'),('MAP_Library','/MAP_Library/Sublevels/Shared')]:
            (directory/(name+'.json')).write_text(json.dumps({'rootPackage':root}))
        self.assertEqual(ready_maps(self.root),['MAP_Test'])
    def test_failed_refresh_preserves_last_good_sidecar(self):
        directory=self.root/'data';(directory/'scenes').mkdir(parents=True);(directory/'appearance').mkdir()
        # The importer expects buffers below data/extracted.
        import shutil
        shutil.copytree(self.root/'meshes',directory/'extracted/meshes')
        shutil.copytree(self.root/'proxies',directory/'extracted/proxies')
        (directory/'scenes/MAP_Test.json').write_text(json.dumps(self.scene))
        target=directory/'appearance/MAP_Test.json';original=json.dumps(self.colors);target.write_text(original)
        def export(command,**kwargs):
            bad=copy.deepcopy(self.colors);bad['sceneRevision']='wrong'
            (Path(command[-1])/'MAP_Test.json').write_text(json.dumps(bad))
        with patch.object(import_colors,'ROOT',self.root),patch('sys.argv',['import_colors','MAP_Test','--refresh']),patch.object(import_colors.subprocess,'run',side_effect=export):
            self.assertEqual(import_colors.main(),1)
        self.assertEqual(target.read_text(),original)
        self.assertTrue((self.root/'.local/MAP_Test-colors-rejected.json').is_file())
        report=json.loads((directory/'color-import-report.json').read_text())
        self.assertFalse(report['passed']);self.assertEqual(report['maps']['MAP_Test']['status'],'failed')


if __name__=='__main__':unittest.main()
