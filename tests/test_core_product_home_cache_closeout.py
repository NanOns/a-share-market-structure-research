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
    api=SimpleNamespace(candidate={'registry':{'path':'registry.json','sha256':hashlib.sha256(registry.read_bytes()).hexdigest()}},snapshot={},
        context=lambda:dict(context_token='placeholder'))
    state['api']=api
    monkeypatch.setattr(module,'accepted_api',lambda root:api)
    class BFF:
        def __init__(self,reader,*args,**kwargs):self.api=reader
        def get(self,path,params):
            state['calls']+=1
            if params.get('context_token')!='placeholder':raise ValueError('CONTEXT_TOKEN_MISMATCH')
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
    monkeypatch.setattr(v4_native,'configured_dsn',lambda:'<placeholder>')
    monkeypatch.setattr(v4_native,'configured_reader_dsn',lambda:'<placeholder>')
    server=ThreadingHTTPServer(('127.0.0.1',0),module.make_product_handler(tmp_path,None))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def get(token='placeholder',path='/api/v4/home'):
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

def test_cached_home_ignores_archived_source_registry_mutation(cache_server):
    state,get,registry=cache_server
    assert get()==(200,{'version':1})
    registry.write_text('{"changed":true}')
    assert get()==(200,{'version':1}) and state['calls']==1

def test_context_request_rejects_disconnected_or_other_native_owner_database(cache_server):
    state,get,registry=cache_server
    descriptor=registry.parent/'owner.pg.json'
    descriptor.write_text(json.dumps({'database_identity':{'database':'one','database_oid':1,'host':'127.0.0.1','port':55791}}))
    state['api'].pg_owner_authority={'owners':{'2026-10-09':{'core':{'descriptor':{
        'pg_descriptor':{'database_identity':{'database':'one','database_oid':1,'host':'127.0.0.1','port':55791}}
    }}}}}
    assert get(path='/api/v4/context')[0]==200
    state['database']='other'
    assert get(path='/api/v4/context')[0]==503 and state['calls']==1
    state['database']='one';state['available']=False
    assert get(path='/api/v4/context')[0]==503 and state['calls']==1


def test_three_business_requests_do_not_wait_for_shared_projection_lock(cache_server,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import workbench_service.core_product_server_r1 as module
    state,get,_=cache_server
    assert get(path='/api/v4/context')[0]==200
    barrier=threading.Barrier(3)
    original=module.CoreProductBFFR1.get
    def overlap(self,path,params):
        barrier.wait(timeout=3)
        return original(self,path,params)
    monkeypatch.setattr(module.CoreProductBFFR1,'get',overlap)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(lambda p:get(path=p),['/api/v4/stocks','/api/v4/sectors','/api/v4/context']))
    assert all(code==200 for code,_ in results)


def test_read_index_authority_change_invalidates_encoded_home(cache_server):
    state,get,registry=cache_server
    assert get()==(200,{'version':1})
    config=registry.parent/'config';config.mkdir()
    (config/'v4_read_index_authority_r1.json').write_text('{}')
    assert get()==(200,{'version':2}) and state['calls']==2
