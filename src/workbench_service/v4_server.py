"""V4_DEFAULT_WORKBENCH_SERVICE_V1. Product version and permissions are separate."""
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .current_v4_context import CurrentAcceptedV4Reader
from .shadow_server import make_shadow_handler


def make_v4_handler(root):
    root=Path(root)
    reader=CurrentAcceptedV4Reader(root,require_runtime=True)
    base=make_shadow_handler(root)
    static=root/'src/workbench_service/static'

    class Handler(base):
        def do_GET(self):
            parsed=urlparse(self.path)
            if parsed.path in ('/','/v4','/v4/'):
                return self.send(200,(static/'v4-workbench.html').read_bytes(),'text/html; charset=utf-8')
            if parsed.path=='/v4/workbench.js':
                return self.send(200,(static/'v4-workbench.js').read_bytes(),'application/javascript; charset=utf-8')
            if parsed.path=='/v3':
                return self.send(200,b'<!doctype html><meta charset="utf-8"><title>V3 historical diagnostics</title><h1>V3 historical diagnostics</h1><p>The legacy database was intentionally retired. V4 current accepted research is available at <a href="/v4">V4</a>.</p>','text/html; charset=utf-8')
            if parsed.path=='/api/operations/status':
                code,payload=reader.read('context')
                if code!=200:return self.send(code,dict(service_state='BLOCKED',service_mode='V4_DEFAULT_WORKBENCH',reason=payload))
                return self.send(200,dict(service_state='READY',service_mode='V4_DEFAULT_WORKBENCH',service_control_contract='V4_DEFAULT_WORKBENCH_SERVICE_V1',product_version='V4',default_ui='V4',
                    current_accepted_reader=True,shadow_diagnostics=True,legacy_v3_default=False,read_only_ui=True,
                    production_permission=payload['production_permission'],**payload['context']))
            if parsed.path.startswith('/api/v4/current/'):
                values=parse_qs(parsed.query,keep_blank_values=True)
                if any(len(v)!=1 for v in values.values()):return self.send(409,dict(status='BLOCKED',code='DUPLICATE_CONTEXT_PARAMETER'))
                allowed={'q','state','limit','offset','context_token'}
                if set(values)-allowed:return self.send(400,dict(status='BLOCKED',code='UNKNOWN_CONTEXT_PARAMETER'))
                code,payload=reader.read(parsed.path.removeprefix('/api/v4/current/'),{k:v[0] for k,v in values.items()})
                return self.send(code,payload)
            return super().do_GET()

    return Handler


def serve_v4(root,host='127.0.0.1',port=28765):
    ThreadingHTTPServer((host,port),make_v4_handler(root)).serve_forever()
