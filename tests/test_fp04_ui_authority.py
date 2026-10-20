"""UI pointer rollback is independent from immutable research data."""
import json
import threading
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from workbench_service.v4_server import make_v4_handler
import workbench_service.v4_server as v4_server
from workbench_service.v4_daily_refresh import atomic_bytes

def test_shell_switch_rollback_and_invalid_authority(tmp_path):
    static=tmp_path/'src/workbench_service/static';(static/'research').mkdir(parents=True)
    atomic_bytes(static/'research/index.html',b'new-six-entry-shell')
    atomic_bytes(static/'v4-workbench.html',b'legacy-seven-summary')
    path=tmp_path/'config/v4_research_ui_authority_v1.json'
    server=ThreadingHTTPServer(('127.0.0.1',0),make_v4_handler(tmp_path));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    url='http://127.0.0.1:'+str(server.server_port)
    def get(route='/'):
        with urllib.request.urlopen(url+route) as response:return response.read()
    try:
        atomic_bytes(path,json.dumps({'mode':'SIX_ENTRY'}).encode())
        assert get()==b'new-six-entry-shell'
        atomic_bytes(path,json.dumps({'mode':'LEGACY_SUMMARY'}).encode())
        assert get()==b'legacy-seven-summary'
        assert get('/v4/legacy-summary')==b'legacy-seven-summary'
        atomic_bytes(path,b'{invalid')
        try:get()
        except urllib.error.HTTPError as e:assert e.code==503
        else:raise AssertionError('Malformed UI authority must fail closed')
    finally:server.shutdown();server.server_close();thread.join(timeout=2)


def test_joint_release_serves_its_bound_entrypoint_without_r43_overlay(tmp_path,monkeypatch):
    import hashlib
    import workbench_analysis.operational_successor_v1 as daily
    from http.server import BaseHTTPRequestHandler

    root=tmp_path
    (root/'config').mkdir()
    (root/'data/v4').mkdir(parents=True)
    # If the legacy overlay path is entered, it must attempt to resolve this
    # Head. A joint bundle must serve its own bound app.js without that lookup.
    (root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').write_text('{"contract_id":"test"}')
    asset=root/'bundle/app.js';asset.parent.mkdir();asset.write_bytes(b"import './rotation-auto-acceptance.js';\n")
    binding={'path':'bundle/app.js','sha256':hashlib.sha256(asset.read_bytes()).hexdigest()}
    monkeypatch.setattr(v4_server,'recover',lambda _root:None)
    monkeypatch.setattr(v4_server,'CurrentAcceptedV4Reader',lambda *_a,**_k:object())
    monkeypatch.setattr(v4_server,'ResearchBFF',lambda _root:object())
    monkeypatch.setattr(v4_server,'joint_load',lambda _root:{'ui_assets':{'app.js':binding}})
    class Base(BaseHTTPRequestHandler):
        def send(self,status,body,content_type='application/json; charset=utf-8'):
            payload=body if isinstance(body,bytes) else json.dumps(body).encode()
            self.send_response(status);self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
    monkeypatch.setattr(v4_server,'make_shadow_handler',lambda _root:Base)
    monkeypatch.setattr(daily,'accepted_api',lambda *_a,**_k:(_ for _ in ()).throw(AssertionError('R43 overlay must not run')))

    server=ThreadingHTTPServer(('127.0.0.1',0),make_v4_handler(root))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/v4/assets/app.js') as response:
            assert response.read()==asset.read_bytes()
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
