"""The preview must stay usable after the intentional legacy schema reset."""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from workbench_service.shadow_server import make_shadow_handler


def test_preview_has_no_legacy_startup_or_write_dependency(monkeypatch):
    import psycopg
    import duckdb

    def forbidden(*args, **kwargs):
        raise AssertionError('Preview attempted a database connection')

    monkeypatch.setattr(psycopg, 'connect', forbidden)
    monkeypatch.setattr(duckdb, 'connect', forbidden)
    server = ThreadingHTTPServer(('127.0.0.1', 0), make_shadow_handler(Path(__file__).resolve().parents[1]))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        with urllib.request.urlopen(base + '/v4/shadow', timeout=3) as response:
            assert b'V4 Shadow' in response.read()
        with urllib.request.urlopen(base + '/api/v4/shadow/context', timeout=3) as response:
            assert json.load(response)['status'] == 'NO_REAL_SHADOW_DATA'
        for method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            request = urllib.request.Request(base + '/api/v4/shadow/context', method=method, data=b'{}')
            try:
                urllib.request.urlopen(request, timeout=3)
            except urllib.error.HTTPError as error:
                assert error.code == 405
                assert json.load(error)['code'] == 'SHADOW_READ_ONLY'
            else:
                raise AssertionError('Write was admitted')
        for path, code in (('/api/v4/shadow/context?x=1&x=2', 409), ('/api/publications', 404)):
            try:
                urllib.request.urlopen(base + path, timeout=3)
            except urllib.error.HTTPError as error:
                assert error.code == code
            else:
                raise AssertionError('Invalid route was admitted')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
