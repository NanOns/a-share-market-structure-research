import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from workbench_service.v4_server import make_v4_handler

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def service(monkeypatch):
    import psycopg,duckdb
    def forbidden(*args,**kwargs):raise AssertionError('legacy database dependency')
    monkeypatch.setattr(psycopg,'connect',forbidden);monkeypatch.setattr(duckdb,'connect',forbidden)
    server=ThreadingHTTPServer(('127.0.0.1',0),make_v4_handler(ROOT))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{server.server_port}'
    finally:server.shutdown();server.server_close();thread.join(timeout=3)


def get(base,path):
    with urllib.request.urlopen(base+path,timeout=10) as response:
        raw=response.read();return response.status,json.loads(raw) if path.startswith('/api/') else raw


def test_service_starts_without_legacy_and_root_is_v4(service):
    from workbench_service.joint_release import load,checked_path
    authority=load(ROOT)
    assert authority is not None
    approved_html=checked_path(ROOT,authority['ui_assets']['index.html']).read_bytes()
    for path in ['/','/v4','/v4/']:
        assert get(service,path)[1]==approved_html
    status=get(service,'/api/operations/status')[1]
    assert status['service_mode']=='V4_DEFAULT_WORKBENCH'
    assert status['read_only_ui'] and not status['legacy_v3_default']
    assert not any(status['production_permission'].values())


def test_current_routes_without_real_shadow(service):
    token=get(service,'/api/v4/current/context')[1]['context_token']
    for module in ['summary','radar','entity','sector','cohort','settlement','health']:
        status,payload=get(service,'/api/v4/current/'+module+'?context_token='+token)
        assert status==200 and payload['context_token']==token
        assert payload['items']
    assert get(service,'/api/v4/shadow/context')[1]['status']=='NO_REAL_SHADOW_DATA'
    assert get(service,'/v4/shadow')[0]==200


def test_ui_writes_forbidden(service):
    for route in ['/api/v4/current/entity','/api/v4/shadow/context','/api/operations/restart']:
        request=urllib.request.Request(service+route,method='POST',data=b'{}')
        with pytest.raises(urllib.error.HTTPError) as error:urllib.request.urlopen(request,timeout=3)
        assert error.value.code==405


def test_entity_search_and_context_stability(service):
    token=get(service,'/api/v4/current/context')[1]['context_token']
    p=get(service,'/api/v4/current/entity?q=688349&context_token='+token)[1]
    assert p['total']==1 and p['context_token']==token
    assert get(service,'/api/v4/current/context')[1]['context_token']==token


def test_service_restart_same_context():
    from workbench_service.current_v4_context import CurrentAcceptedV4Reader
    assert CurrentAcceptedV4Reader(ROOT).load_context()==CurrentAcceptedV4Reader(ROOT).load_context()
