"""UI pointer rollback is independent from immutable research data."""
import json
import threading
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from workbench_service.v4_server import make_v4_handler
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
