"""V4_DEFAULT_WORKBENCH_SERVICE_V1. Product version and permissions are separate."""
import json
import hashlib
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .current_v4_context import CurrentAcceptedV4Reader
from .shadow_server import make_shadow_handler
from .research_bff import ResearchBFF
from .joint_release import load as joint_load,checked_path,recover


def make_v4_handler(root):
    root=Path(root)
    recover(root)
    reader=CurrentAcceptedV4Reader(root,require_runtime=True)
    base=make_shadow_handler(root)
    static=root/'src/workbench_service/static'
    bff=ResearchBFF(root)
    operational_cache={};operational_lock=threading.RLock()

    def operational_reader():
        from workbench_analysis.r43_operational_publication import accepted_api
        head=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
        authority=root/'data/v4/R43_OPERATIONAL_EXTERNAL_ACCEPTANCE.json'
        if not head.exists():
            operational_cache.clear();return None
        signature=hashlib.sha256(head.read_bytes()+(authority.read_bytes() if authority.exists() else b'')).hexdigest()
        with operational_lock:
            cached=operational_cache.get('reader')
            signatures=operational_cache.get('sources',{})
            changed=any(not p.is_file() or (p.stat().st_size,p.stat().st_mtime_ns)!=stat for p,stat in signatures.items())
            if cached is None or signature!=operational_cache.get('signature') or changed:
                operational_cache.clear()
                cached=accepted_api(root)
                registry=json.loads((root/cached.candidate['registry']['path']).read_bytes())
                bindings=[]
                def collect(value):
                    if isinstance(value,dict):
                        if value.get('path') and value.get('sha256'):bindings.append(value)
                        for child in value.values():collect(child)
                    elif isinstance(value,list):
                        for child in value:collect(child)
                collect(registry);collect(cached.candidate);collect(cached.snapshot)
                paths={root/b['path'] for b in bindings}
                operational_cache.update(reader=cached,signature=signature,sources={p:(p.stat().st_size,p.stat().st_mtime_ns) for p in paths})
            return cached

    class Handler(base):
        def do_GET(self):
            parsed=urlparse(self.path)
            if parsed.path=='/v4/operational-preview':
                return self.send(200,(static/'r43-operational-preview.html').read_bytes(),'text/html; charset=utf-8')
            if parsed.path.startswith('/api/v4/original-0930/'):
                values=parse_qs(parsed.query,keep_blank_values=True)
                if any(len(v)!=1 for v in values.values()):return self.send(400,dict(code='DUPLICATE_PARAMETER'))
                code,payload=bff.get('/api/v4/'+parsed.path.removeprefix('/api/v4/original-0930/'),{k:v[0] for k,v in values.items()})
                return self.send(code,payload)
            if parsed.path.startswith('/api/v4/') and not parsed.path.startswith('/api/v4/shadow/'):
                from workbench_analysis.r43_operational_publication import accepted_api
                try:
                    operational=operational_reader()
                except (ValueError,KeyError,OSError) as error:
                    return self.send(503,dict(code='OPERATIONAL_ACCEPTED_SOURCE_INVALID',reason=str(error)))
                if operational is not None:
                    from .r43_operational_bff import OperationalResearchBFF
                    try:
                        values=parse_qs(parsed.query,keep_blank_values=True)
                        if any(len(v)!=1 for v in values.values()):raise ValueError('DUPLICATE_PARAMETER')
                        code,payload=OperationalResearchBFF(operational,bff).get(parsed.path,{k:v[0] for k,v in values.items()})
                        return self.send(code,payload)
                    except (ValueError,KeyError) as error:
                        return self.send(409 if str(error)=='CONTEXT_TOKEN_MISMATCH' else 400,dict(code='INVALID_OPERATIONAL_QUERY',reason=str(error)))
            if parsed.path in ('/','/v4','/v4/') or parsed.path.startswith('/v4/research/'):
                authority=root/'config/v4_research_ui_authority_v1.json'
                try:mode=json.loads(authority.read_bytes())['mode'] if authority.exists() else 'LEGACY_SUMMARY'
                except (ValueError,OSError,KeyError):return self.send(503,dict(code='UI_AUTHORITY_INVALID'))
                if mode not in ('SIX_ENTRY','LEGACY_SUMMARY'):return self.send(503,dict(code='UI_AUTHORITY_INVALID'))
                page=static/('research/index.html' if mode=='SIX_ENTRY' else 'v4-workbench.html')
                joint=joint_load(root)
                if joint:page=checked_path(root,joint['ui_assets']['index.html'])
                return self.send(200,page.read_bytes(),'text/html; charset=utf-8')
            if parsed.path=='/v4/legacy-summary':
                return self.send(200,(static/'v4-workbench.html').read_bytes(),'text/html; charset=utf-8')
            if parsed.path.startswith('/v4/assets/'):
                name=parsed.path.removeprefix('/v4/assets/')
                if name not in ('app.js','api.js','components.js','labels.js','stock.js','replay.js','style.css'):return self.send(404,dict(code='ASSET_NOT_FOUND'))
                joint=joint_load(root)
                asset=checked_path(root,joint['ui_assets'][name]) if joint else static/'research'/name
                if name in ('api.js','components.js','app.js'):
                    try:operational=operational_reader()
                    except (ValueError,KeyError,OSError) as error:return self.send(503,dict(code='OPERATIONAL_ACCEPTED_SOURCE_INVALID',reason=str(error)))
                    if operational is not None:
                        relative='src/workbench_service/static/r43-compat/'+name
                        registry=json.loads((root/operational.candidate['registry']['path']).read_bytes())
                        binding=next((b for b in registry['bindings'] if b['path']==relative),None)
                        if binding is None:return self.send(503,dict(code='OPERATIONAL_UI_COMPATIBILITY_ASSET_NOT_BOUND'))
                        from workbench_analysis.r43_operational_sources import checked
                        asset=checked(root,binding)
                return self.send(200,asset.read_bytes(),'text/css; charset=utf-8' if name.endswith('.css') else 'application/javascript; charset=utf-8')
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
                if parsed.path=='/api/v4/stocks.csv':
                    from .csv_export import stock_csv
                    from .current_v4_context import SourceInvalid
                    try:raw,count=stock_csv(bff.current(),{k:v[0] for k,v in values.items()})
                    except SourceInvalid:return self.send(409,dict(code='CONTEXT_CONFLICT'))
                    except (ValueError,TypeError):return self.send(400,dict(code='INVALID_EXPORT_QUERY'))
                    self.send_response(200);self.send_header('Content-Type','text/csv; charset=utf-8')
                    self.send_header('Content-Disposition','attachment; filename="V4_stocks.csv"')
                    self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store')
                    self.send_header('X-Row-Count',str(count));self.end_headers();self.wfile.write(raw);return
                code,payload=bff.get(parsed.path,{k:v[0] for k,v in values.items()})
                return self.send(code,payload)
            return super().do_GET()

    return Handler


def serve_v4(root,host='127.0.0.1',port=28765):
    ThreadingHTTPServer((host,port),make_v4_handler(root)).serve_forever()
