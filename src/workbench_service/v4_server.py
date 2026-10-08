"""V4_DEFAULT_WORKBENCH_SERVICE_V1. Product version and permissions are separate."""
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .current_v4_context import CurrentAcceptedV4Reader
from .shadow_server import make_shadow_handler
from .research_bff import ResearchBFF


def make_v4_handler(root):
    root=Path(root)
    reader=CurrentAcceptedV4Reader(root,require_runtime=True)
    base=make_shadow_handler(root)
    static=root/'src/workbench_service/static'
    bff=ResearchBFF(root)

    class Handler(base):
        def do_GET(self):
            parsed=urlparse(self.path)
            if parsed.path in ('/','/v4','/v4/') or parsed.path.startswith('/v4/research/'):
                authority=root/'config/v4_research_ui_authority_v1.json'
                try:mode=json.loads(authority.read_bytes())['mode'] if authority.exists() else 'LEGACY_SUMMARY'
                except (ValueError,OSError,KeyError):return self.send(503,dict(code='UI_AUTHORITY_INVALID'))
                if mode not in ('SIX_ENTRY','LEGACY_SUMMARY'):return self.send(503,dict(code='UI_AUTHORITY_INVALID'))
                page=static/('research/index.html' if mode=='SIX_ENTRY' else 'v4-workbench.html')
                return self.send(200,page.read_bytes(),'text/html; charset=utf-8')
            if parsed.path=='/v4/legacy-summary':
                return self.send(200,(static/'v4-workbench.html').read_bytes(),'text/html; charset=utf-8')
            if parsed.path.startswith('/v4/assets/'):
                name=parsed.path.removeprefix('/v4/assets/')
                if name not in ('app.js','api.js','components.js','labels.js','stock.js','replay.js','style.css'):return self.send(404,dict(code='ASSET_NOT_FOUND'))
                return self.send(200,(static/'research'/name).read_bytes(),'text/css; charset=utf-8' if name.endswith('.css') else 'application/javascript; charset=utf-8')
            if parsed.path=='/v4/workbench.js':
                return self.send(200,(static/'v4-workbench.js').read_bytes(),'application/javascript; charset=utf-8')
            if parsed.path=='/v3':
                return self.send(200,b'<!doctype html><meta charset="utf-8"><title>V3 historical diagnostics</title><h1>V3 historical diagnostics</h1><p>The legacy database was intentionally retired. V4 current accepted research is available at <a href="/v4">V4</a>.</p>','text/html; charset=utf-8')
            if parsed.path=='/api/operations/status':
                research={}
                if (root/'config/v4_research_snapshot_authority_v1.json').exists():
                    try:
                        current=bff.current()
                        research=dict(research_ui_contract='V4_SIX_ENTRY_SHELL_V1',research_snapshot_state='READY',research_counts=current.manifest['counts'],research_release_id=current.context['release_id'])
                    except (ValueError,OSError,KeyError) as error:
                        return self.send(503,dict(service_state='BLOCKED',service_mode='V4_DEFAULT_WORKBENCH',reason='RESEARCH_SNAPSHOT_INVALID',detail=type(error).__name__))
                code,payload=reader.read('context')
                if code!=200:return self.send(code,dict(service_state='BLOCKED',service_mode='V4_DEFAULT_WORKBENCH',reason=payload))
                return self.send(200,dict(service_state='READY',service_mode='V4_DEFAULT_WORKBENCH',service_control_contract='V4_DEFAULT_WORKBENCH_SERVICE_V1',product_version='V4',default_ui='V4',
                    current_accepted_reader=True,shadow_diagnostics=True,legacy_v3_default=False,read_only_ui=True,
                    production_permission=payload['production_permission'],**payload['context'],**research))
            if parsed.path.startswith('/api/v4/current/'):
                values=parse_qs(parsed.query,keep_blank_values=True)
                if any(len(v)!=1 for v in values.values()):return self.send(409,dict(status='BLOCKED',code='DUPLICATE_CONTEXT_PARAMETER'))
                allowed={'q','state','limit','offset','context_token'}
                if set(values)-allowed:return self.send(400,dict(status='BLOCKED',code='UNKNOWN_CONTEXT_PARAMETER'))
                code,payload=reader.read(parsed.path.removeprefix('/api/v4/current/'),{k:v[0] for k,v in values.items()})
                return self.send(code,payload)
            if parsed.path.startswith('/api/v4/') and not parsed.path.startswith('/api/v4/shadow/'):
                if len(self.path)>4096:return self.send(414,dict(code='REQUEST_TOO_LONG'))
                if not bff.allowed(self.client_address[0]):return self.send(429,dict(code='RATE_LIMIT',retry_after_seconds=60))
                values=parse_qs(parsed.query,keep_blank_values=True)
                if any(len(v)!=1 for v in values.values()):return self.send(400,dict(code='DUPLICATE_PARAMETER'))
                code,payload=bff.get(parsed.path,{k:v[0] for k,v in values.items()})
                return self.send(code,payload)
            return super().do_GET()

    return Handler


def serve_v4(root,host='127.0.0.1',port=28765):
    ThreadingHTTPServer((host,port),make_v4_handler(root)).serve_forever()
