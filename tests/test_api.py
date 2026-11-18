import importlib
import json
from io import BytesIO
from pathlib import Path
import tempfile
import zipfile
import threading
import unittest
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from unittest.mock import patch

api=importlib.import_module('server.__main__')


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http=ThreadingHTTPServer(('127.0.0.1',0),api.Handler)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.http.server_port)
    @classmethod
    def tearDownClass(cls):cls.http.shutdown();cls.http.server_close();cls.thread.join()
    def request(self,path,payload=None,origin=None):
        headers={}
        if origin:headers['Origin']=origin
        if payload is not None:headers['Content-Type']='application/json'
        req=urllib.request.Request(self.base+path,data=None if payload is None else json.dumps(payload).encode(),headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=5) as res:return res.status,res.read(),res.headers
        except urllib.error.HTTPError as e:return e.code,e.read(),e.headers
    def test_static_app_and_content_types(self):
        code,body,headers=self.request('/');self.assertEqual(code,200);self.assertIn(b'Portal Atlas',body)
        self.assertIn('text/html',headers['Content-Type'])
        self.assertEqual(self.request('/app.js')[2]['Content-Type'],'application/javascript')
    def test_private_game_data_is_not_served(self):
        for path in ['/data/key.txt','/../data/key.txt','/%2e%2e/data/key.txt','/.tools/dotnet/dotnet']:
            with self.subTest(path=path):self.assertIn(self.request(path)[0],(400,404))
    def test_cross_origin_writes_are_rejected(self):
        code,body,_=self.request('/api/import',{'map':'MAP_Academy'},'https://example.com');self.assertEqual(code,403)
    def test_capture_save_requires_same_origin_zip_and_uses_private_export_directory(self):
        content=BytesIO()
        with zipfile.ZipFile(content,'w') as archive:
            archive.writestr('manifest.json',json.dumps({'format':'portal-atlas-clue-batch','version':1}))
        raw=content.getvalue()
        with tempfile.TemporaryDirectory() as directory,patch.object(api,'ROOT',Path(directory)):
            for origin in [None,'https://example.com',self.base]:
                headers={'Content-Type':'application/zip'}
                if origin:headers['Origin']=origin
                request=urllib.request.Request(self.base+'/api/captures',data=raw,headers=headers)
                if origin==self.base:
                    with urllib.request.urlopen(request,timeout=5) as response:
                        self.assertEqual(response.status,201);path=Path(json.loads(response.read())['path'])
                        self.assertEqual(path.parent,Path(directory)/'.local/captures');self.assertEqual(path.read_bytes(),raw)
                else:
                    with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(request,timeout=5)
                    self.assertEqual(error.exception.code,403)
    def test_dns_rebinding_host_is_rejected(self):
        request=urllib.request.Request(self.base+'/api/maps',headers={'Host':'foreign.example'})
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(request,timeout=5)
        self.assertEqual(error.exception.code,403)
    def test_invalid_route_input_has_structured_error(self):
        code,body,_=self.request('/api/route',{'map':'../../secret','start':'x','end':'y'});self.assertEqual(code,400);self.assertIn('error',json.loads(body))
    def test_optional_color_endpoint_and_invalid_id(self):
        with patch.object(api,'appearance',return_value={'available':False,'reason':'Not imported'}):
            code,body,_=self.request('/api/colors/MAP_Test');self.assertEqual(code,200);self.assertFalse(json.loads(body)['available'])
        self.assertEqual(self.request('/api/colors/../../secret')[0],400)
    def test_exports_are_json_attachments_with_source_and_revision(self):
        s={'id':'MAP_Test','revision':'r1','rootPackage':'/MAP_Test/Main','source':{'kind':'assets'},'model':{},'nodes':[{'id':'A'},{'id':'B'}],'edges':[{'source':'A','target':'B','kind':'walk','seconds':1,'difficulty':10}],'issues':[]}
        with patch.object(api,'scene',return_value=s):
            code,body,headers=self.request('/api/export/graph?map=MAP_Test&revision=r1')
            self.assertEqual(code,200);self.assertIn('attachment;',headers['Content-Disposition']);self.assertEqual(json.loads(body)['revision'],'r1')
            code,body,headers=self.request('/api/export/route?map=MAP_Test&start=A&end=B&kinds=walk')
            self.assertEqual(code,200);self.assertTrue(json.loads(body)['route']['found'])
            self.assertEqual(self.request('/api/export/graph?map=MAP_Test&revision=old')[0],400)
    def test_changed_revision_is_rejected_before_route_search(self):
        with patch.object(api,'scene',return_value={'revision':'new'}):
            self.assertEqual(self.request('/api/route',{'map':'MAP_Test','revision':'old','start':'A','end':'B'})[0],409)
    def test_route_request_uses_directed_search(self):
        s={'nodes':[{'id':'A'},{'id':'B'}],'edges':[{'id':'AB','source':'A','target':'B','kind':'portal','seconds':1,'difficulty':20}]}
        with patch.object(api,'scene',return_value=s):
            code,body,_=self.request('/api/route',{'map':'MAP_Test','start':'A','end':'B'});self.assertEqual(code,200);self.assertTrue(json.loads(body)['found'])
            code,body,_=self.request('/api/route',{'map':'MAP_Test','start':'B','end':'A'});self.assertEqual(code,200);self.assertFalse(json.loads(body)['found'])


if __name__=='__main__':unittest.main()
