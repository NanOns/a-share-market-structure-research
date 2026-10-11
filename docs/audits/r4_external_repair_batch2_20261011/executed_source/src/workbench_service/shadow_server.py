"""V4_SHADOW_PREVIEW_SERVICE_V1: read-only, no legacy recovery or writers."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .shadow_context import PREFIX, ShadowContextReader


def make_shadow_handler(root):
    root = Path(root)
    static = root / 'src/workbench_service/static'
    # Invalid contracts prevent startup; never inject simulated data.
    reader = ShadowContextReader(root)

    class Handler(BaseHTTPRequestHandler):
        def send(self, status, body, content_type='application/json; charset=utf-8'):
            raw = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False, allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path in ('/', '/v4', '/v4/', '/v4/shadow', '/v4/shadow/'):
                return self.send(200, (static / 'shadow-v4.html').read_bytes(), 'text/html; charset=utf-8')
            if parsed.path == '/v4/shadow.js':
                return self.send(200, (static / 'shadow-v4.js').read_bytes(), 'application/javascript; charset=utf-8')
            if parsed.path == '/api/operations/status':
                return self.send(200, {'service_state': 'READY', 'service_mode': 'V4_SHADOW_ONLY',
                    'service_control_contract': 'V4_SHADOW_PREVIEW_SERVICE_V1', 'read_only': True,
                    'legacy_workbench_available': False})
            if parsed.path.startswith(PREFIX):
                values = parse_qs(parsed.query, keep_blank_values=True)
                if any(len(value) != 1 for value in values.values()):
                    return self.send(409, {'status': 'BLOCKED', 'code': 'DUPLICATE_CONTEXT_PARAMETER', 'items': []})
                status, body = reader.handle(parsed.path, {key: value[0] for key, value in values.items()})
                return self.send(status, body)
            return self.send(404, {'status': 'BLOCKED', 'code': 'ROUTE_UNAVAILABLE_IN_V4_SHADOW_ONLY'})

        def reject_write(self):
            return self.send(405, {'status': 'BLOCKED', 'code': 'SHADOW_READ_ONLY', 'items': []})

        do_POST = do_PUT = do_PATCH = do_DELETE = reject_write

        def log_message(self, *_):
            pass

    return Handler


def serve_shadow(root, host='127.0.0.1', port=28765):
    ThreadingHTTPServer((host, port), make_shadow_handler(root)).serve_forever()
