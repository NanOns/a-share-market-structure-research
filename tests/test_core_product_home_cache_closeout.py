"""Cache transport checks; mocked facts do not certify real PG publication."""
import json
import hashlib
import threading
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from types import SimpleNamespace

import pytest

@pytest.fixture
def cache_server(tmp_path,monkeypatch):
    import workbench_service.core_product_server_r1 as module
    monkeypatch.setattr(module,'make_daily_handler',lambda *args:BaseHTTPRequestHandler)
    folder=tmp_path/'data/v4';folder.mkdir(parents=True)
    (folder/'V4_OPERATIONAL_RESEARCH_HEAD.json').write_text('{}')
    (folder/'V4_DATA_ACCEPTED_HEAD.json').write_text('{"identity":{}}')
    registry=tmp_path/'registry.json';registry.write_text('{}')
    state=dict(database='one',available=True,calls=0)
    api=SimpleNamespace(candidate={'registry':{'path':'registry.json','sha256':hashlib.sha256(registry.read_bytes()).hexdigest()}},snapshot={})
    state['api']=api
    monkeypatch.setattr(module,'accepted_api',lambda root:api)
    class BFF:
        def __init__(self,reader,*args,**kwargs):self.api=reader
        def get(self,path,params):
            state['calls']+=1
            if params.get('context_token')!='valid':raise ValueError('CONTEXT_TOKEN_MISMATCH')
            return 200,{'version':state['calls']}
    monkeypatch.setattr(module,'CoreProductBFFR1',BFF)
    class PG:
        def __enter__(self):
            if not state['available']:raise RuntimeError('OFFLINE')
            return self
        def __exit__(self,*args):pass
        def execute(self,sql,*args):
            return SimpleNamespace(fetchone=lambda:(state['database'],1,'127.0.0.1',55791))
    monkeypatch.setattr(module.psycopg,'connect',lambda *args,**kwargs:PG())
    from workbench_db import v4_native
    monkeypatch.setattr(v4_native,'configured_dsn',lambda:'mocked transport fixture')
    server=ThreadingHTTPServer(('127.0.0.1',0),module.make_product_handler(tmp_path,None))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def get(token='valid',path='/api/v4/home'):
        try:
            response=urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}{path}?context_token={token}')
        except urllib.error.HTTPError as error:response=error
        with response:return response.status,json.loads(response.read())
    yield state,get,registry
    server.shutdown();server.server_close();thread.join()

def test_cached_home_checks_database_identity_and_availability(cache_server):
    state,get,_=cache_server
    assert get()==(200,{'version':1})
    assert get()==(200,{'version':1}) and state['calls']==1
    state['database']='other'
    assert get()[0]==503
    state['database']='one';state['available']=False
    assert get()[0]==503

def test_cached_home_rejects_wrong_token(cache_server):
    _,get,_=cache_server
    assert get()[0]==200
    assert get('wrong')[0]==409

def test_cached_home_invalidates_changed_source(cache_server):
    state,get,registry=cache_server
    assert get()==(200,{'version':1})
    registry.write_text('{"changed":true}')
    assert get()==(200,{'version':2}) and state['calls']==2

def test_context_request_rejects_disconnected_or_other_native_owner_database(cache_server):
    state,get,registry=cache_server
    descriptor=registry.parent/'owner.pg.json'
    descriptor.write_text(json.dumps({'database_identity':{'database':'one','database_oid':1,'host':'127.0.0.1','port':55791}}))
    state['api'].pg_owner_authority={'owners':{'2026-10-09':{'core':{'path':descriptor.name}}}}
    assert get(path='/api/v4/context')[0]==200
    state['database']='other'
    assert get(path='/api/v4/context')[0]==503 and state['calls']==1
    state['database']='one';state['available']=False
    assert get(path='/api/v4/context')[0]==503 and state['calls']==1
