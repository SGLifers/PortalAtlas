import argparse
import json
import mimetypes
import os
import pathlib
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote, parse_qs

from .routing import route

ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/'data';WEB=ROOT/'web'
JOBS={};JOB_LOCK=threading.Lock();SCENES={}


def features():
    path=DATA/'maps-index.json'
    if not path.exists():return []
    return sorted(set(re.findall(r'/GameFeatures/Maps/(MAP_[^/]+)/',path.read_text())))


def scene(mid):
    if not re.fullmatch(r'MAP_[A-Za-z0-9_]+',mid):raise ValueError('Invalid map')
    p=DATA/'scenes'/(mid+'.json')
    if not p.exists():raise ValueError('Import this map first')
    stamp=p.stat().st_mtime_ns
    if mid not in SCENES or SCENES[mid][0]!=stamp:SCENES[mid]=(stamp,json.loads(p.read_text()))
    return SCENES[mid][1]


def map_list():
    rows=[]
    for mid in features():
        ready=(DATA/'scenes'/(mid+'.json')).exists()
        row={'id':mid,'name':mid.removeprefix('MAP_').replace('_',' '),'ready':ready}
        if ready:
            s=scene(mid);row.update(nodes=len(s['nodes']),edges=len(s['edges']),revision=s['revision'],issues=len(s['issues']),library='/Sublevels/' in s['rootPackage'],geometryUsable=s['source'].get('geometryUsable',False))
        if mid in JOBS:row['job']=dict(JOBS[mid])
        rows.append(row)
    return rows


def import_map(mid):
    if mid not in features():raise ValueError('Unknown installed map')
    with JOB_LOCK:
        if any(j['status']=='running' for j in JOBS.values()):raise ValueError('Another map is being imported')
        import fcntl
        local=ROOT/'.local';local.mkdir(exist_ok=True)
        lock=(local/'import.lock').open('a')
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            lock.close();raise ValueError('A map import batch is already running; try again after it finishes')
        JOBS[mid]={'status':'running','phase':'Reading map packages','started':time.time()}
    def worker():
        try:
            local=ROOT/'.local';local.mkdir(exist_ok=True)
            env=os.environ.copy();env.update(ATLAS_KEY_FILE=str(DATA/'key.txt'),ATLAS_MAPPING_FILE=str(DATA/'mappings.json'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',DOTNET_PROCESSOR_COUNT='2')
            dotnet=ROOT/'.tools/dotnet/dotnet';reader=ROOT/'tools/AssetReader/bin/Release/net10.0/AssetReader.dll'
            with (local/(mid+'.log')).open('w') as log:
                subprocess.run([str(dotnet),str(reader),str(DATA/'install/Paks'),'export-feature',mid,str(DATA/'extracted')],cwd=ROOT,env=env,stdout=log,stderr=log,check=True,timeout=1800)
                JOBS[mid]['phase']='Checking angles and movement'
                subprocess.run([sys.executable,str(ROOT/'tools/compile_scene.py'),mid],cwd=ROOT,env=env,stdout=log,stderr=log,check=True,timeout=3600)
            JOBS[mid].update(status='complete',phase='Ready',finished=time.time())
        except Exception as exc:JOBS[mid].update(status='failed',phase=str(exc),finished=time.time())
        finally:lock.close()
    threading.Thread(target=worker,daemon=True).start()
    return JOBS[mid]


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def local_host(self):
        return self.headers.get('Host','') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
    def respond(self,body,status=200,kind='application/json',filename=None):
        data=json.dumps(body,allow_nan=False).encode() if kind=='application/json' else body
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)))
        if filename:self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-cache');self.end_headers();self.wfile.write(data)
    def file(self,path):
        if not path.is_file():return self.respond({'error':'File not found'},404)
        kind=mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
        if path.suffix=='.js':kind='application/javascript'
        return self.respond(path.read_bytes(),kind=kind)
    def do_GET(self):
        if not self.local_host():return self.respond({'error':'Local host required'},403)
        path=unquote(urlparse(self.path).path)
        try:
            if path in ('/api/export/graph','/api/export/route'):
                query=parse_qs(urlparse(self.path).query,keep_blank_values=True)
                def value(key,default=''):return query.get(key,[default])[0]
                current=scene(value('map'))
                if value('revision') and value('revision')!=current['revision']:raise ValueError('Map changed; reopen the arena before exporting')
                output={'format':'portal-atlas-graph','version':1,'map':current['id'],'revision':current['revision'],'rootPackage':current['rootPackage'],'source':current['source'],'model':current['model'],'nodes':current['nodes'],'edges':current['edges'],'issues':current['issues']}
                suffix='wall-graph'
                if path.endswith('/route'):
                    kinds=value('kinds','portal,walk,jump,drop').split(',') if value('kinds','portal,walk,jump,drop') else []
                    blocked=value('blocked').split(',') if value('blocked') else []
                    difficulty=float(value('maxDifficulty','100'));objective=value('objective','fastest')
                    result=route(current,value('start'),value('end'),objective,kinds,blocked,difficulty)
                    output.update(format='portal-atlas-route',start=value('start'),end=value('end'),blocked=blocked,
                        filters={'objective':objective,'kinds':kinds,'maxDifficulty':difficulty},route=result,
                        nodes=[n for n in current['nodes'] if n['id'] in result.get('walls',[])])
                    output.pop('edges');suffix='portal-route'
                return self.respond(output,filename=current['id']+'-'+suffix+'.json')
            if path=='/api/maps':return self.respond({'maps':map_list()})
            if path=='/api/status':
                report=DATA/'mappings-report.json';r=json.loads(report.read_text()) if report.exists() else {}
                return self.respond({'source':'Installed Arena Reloaded assets','archivesReady':(DATA/'key.txt').exists(),
                    'mapPackages':json.loads((DATA/'maps-index.json').read_text()).get('count',0) if (DATA/'maps-index.json').exists() else 0,
                    'schemaTypes':r.get('types',0),'mapsReady':sum(x['ready'] and not x.get('library',False) for x in map_list()),'jobs':JOBS})
            if path.startswith('/api/maps/'):return self.respond(scene(path.removeprefix('/api/maps/')))
            if re.fullmatch(r'/assets/(meshes|proxies)/[a-f0-9]{20}\.bin',path):return self.file(DATA/'extracted'/path.split('/')[2]/path.rsplit('/',1)[1])
            if path=='/':return self.file(WEB/'index.html')
            target=(WEB/path.lstrip('/')).resolve()
            if not target.is_relative_to(WEB):return self.respond({'error':'Invalid path'},400)
            return self.file(target)
        except (BrokenPipeError,ConnectionResetError):return
        except (ValueError,KeyError) as exc:return self.respond({'error':str(exc)},400)
        except Exception as exc:return self.respond({'error':type(exc).__name__},500)
    def do_POST(self):
        if not self.local_host():return self.respond({'error':'Local host required'},403)
        origin=self.headers.get('Origin')
        if origin and origin!=f'http://{self.headers.get("Host")}':return self.respond({'error':'Local origin required'},403)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<2 or size>100000:return self.respond({'error':'Invalid request size'},400)
            payload=json.loads(self.rfile.read(size));path=urlparse(self.path).path
            if path=='/api/route':
                current=scene(payload['map'])
                if payload.get('revision') and payload['revision']!=current['revision']:
                    return self.respond({'error':'Map data changed. Reopen the arena to use its refreshed graph.'},409)
                result=route(current,payload['start'],payload['end'],payload.get('objective','fastest'),payload.get('kinds'),payload.get('blocked',[]),float(payload.get('maxDifficulty',100)))
                return self.respond(result)
            if path=='/api/import':return self.respond(import_map(payload['map']),202)
            return self.respond({'error':'Unknown endpoint'},404)
        except (ValueError,KeyError,TypeError) as exc:return self.respond({'error':str(exc)},400)
        except Exception as exc:return self.respond({'error':type(exc).__name__},500)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8741);args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'Portal Atlas: http://127.0.0.1:{args.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:server.server_close()
