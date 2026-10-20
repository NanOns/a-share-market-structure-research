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
from .joint_release import recover


def make_v4_handler(root, *, static_root=None):
    root=Path(root)
    static=Path(static_root) if static_root is not None else root/'src/workbench_service/static'
    source_override=static_root is not None
    recover(root)
    reader=CurrentAcceptedV4Reader(root,require_runtime=True)
    base=make_shadow_handler(root)
    bff=ResearchBFF(root)
    operational_cache={};operational_lock=threading.RLock()

    def operational_reader():
        from workbench_analysis.operational_successor_v1 import accepted_api
        from workbench_db.v4_operational_live_head_pg_r1 import read_current
        current=read_current(root)
        signature=(current['head_sha256'],current['generation'],current['database_identity']['database_oid'])
        with operational_lock:
            cached=operational_cache.get('reader')
            if cached is None or signature!=operational_cache.get('signature'):
                operational_cache.clear()
                cached=accepted_api(root,head_snapshot=current)
                from workbench_db.v4_operational_registry_pg_v1 import read_registry
                registry=read_registry(root,cached.candidate)
                operational_cache.update(reader=cached,signature=signature,registry=registry)
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
                try:
                    operational=operational_reader()
                except (ValueError,KeyError,OSError) as error:
                    return self.send(503,dict(code='OPERATIONAL_ACCEPTED_SOURCE_INVALID',reason=str(error)))
                if operational is not None:
                    from .operational_successor_bff_v1 import OperationalSuccessorBFFV1 as OperationalResearchBFF
                    try:
                        values=parse_qs(parsed.query,keep_blank_values=True)
                        if any(len(v)!=1 for v in values.values()):raise ValueError('DUPLICATE_PARAMETER')
                        code,payload=OperationalResearchBFF(operational,bff).get(parsed.path,{k:v[0] for k,v in values.items()})
                        return self.send(code,payload)
                    except (ValueError,KeyError) as error:
                        return self.send(409 if str(error)=='CONTEXT_TOKEN_MISMATCH' else 400,dict(code='INVALID_OPERATIONAL_QUERY',reason=str(error)))
            if parsed.path in ('/','/v4','/v4/') or parsed.path.startswith('/v4/research/'):
                # The V4 product shell is code, not mutable business state.
                # Runtime configuration JSON must not select a page on behalf
                # of an accepted Owner or Publication.
                page=static/'research/index.html'
                return self.send(200,page.read_bytes(),'text/html; charset=utf-8')
            if parsed.path=='/v4/legacy-summary':
                return self.send(200,(static/'v4-workbench.html').read_bytes(),'text/html; charset=utf-8')
            if parsed.path.startswith('/v4/assets/'):
                name=parsed.path.removeprefix('/v4/assets/')
                if name not in ('app.js','api.js','components.js','labels.js','stock.js','replay.js','style.css'):return self.send(404,dict(code='ASSET_NOT_FOUND'))
                if name=='app.js':
                    if source_override:
                        asset=static/'research'/name
                    else:
                        try:
                            operational=operational_reader()
                            if operational is None:raise ValueError('OPERATIONAL_PG_UI_ASSET_BINDING_REQUIRED')
                            relative='src/workbench_service/static/r43-compat/app.js'
                            binding=next((b for b in operational_cache['registry']['bindings']
                                          if b.get('path')==relative),None)
                            if binding is None:raise ValueError('OPERATIONAL_UI_COMPATIBILITY_ASSET_NOT_BOUND')
                            from workbench_analysis.r43_operational_sources import checked
                            asset=checked(root,binding)
                        except (ValueError,KeyError,OSError) as error:
                            return self.send(503,dict(code='OPERATIONAL_UI_ASSET_UNAVAILABLE',reason=str(error)))
                    return self.send(200,asset.read_bytes(),'application/javascript; charset=utf-8')
                asset=static/'research'/name
                if not source_override and name in ('api.js','components.js'):
                    try:operational=operational_reader()
                    except (ValueError,KeyError,OSError):operational=None
                    if operational is not None:
                        relative='src/workbench_service/static/r43-compat/'+name
                        from workbench_db.v4_operational_registry_pg_v1 import read_registry
                        registry=read_registry(root,operational.candidate)
                        binding=next((b for b in registry['bindings'] if b['path']==relative),None)
                        if binding is not None:
                            from workbench_analysis.r43_operational_sources import checked
                            asset=checked(root,binding)
                return self.send(200,asset.read_bytes(),'text/css; charset=utf-8' if name.endswith('.css') else 'application/javascript; charset=utf-8')
            if parsed.path=='/v4/workbench.js':
                return self.send(200,(static/'v4-workbench.js').read_bytes(),'application/javascript; charset=utf-8')
            if parsed.path=='/v3':
                return self.send(200,b'<!doctype html><meta charset="utf-8"><title>V3 historical diagnostics</title><h1>V3 historical diagnostics</h1><p>The legacy database was intentionally retired. V4 current accepted research is available at <a href="/v4">V4</a>.</p>','text/html; charset=utf-8')
            if parsed.path=='/api/operations/status':
                research={}
                try:
                    current=bff.current()
                    research=dict(research_ui_contract='V4_SIX_ENTRY_SHELL_V1',research_snapshot_state='READY',research_counts=current.manifest['counts'],research_release_id=current.context['release_id'])
                except (ValueError,OSError,KeyError):
                    research=dict(research_ui_contract='V4_SIX_ENTRY_SHELL_V1',research_snapshot_state='UNAVAILABLE_FROM_PG')
                code,payload=reader.read('context')
                if code!=200:return self.send(code,dict(service_state='BLOCKED',service_mode='V4_DEFAULT_WORKBENCH',reason=payload))
                try:operational=operational_reader()
                except (ValueError,KeyError,OSError) as error:
                    return self.send(503,dict(service_state='BLOCKED',service_mode='V4_DEFAULT_WORKBENCH',reason='OPERATIONAL_ACCEPTED_SOURCE_INVALID',detail=str(error)))
                from .operational_control_status import control_status, CONTRACT
                control=control_status(payload)
                if operational is not None:
                    context=operational.context()
                    control=control_status(payload,context,operational.context_digest)
                    research.update(research_snapshot_state='OPERATIONAL_SCOPED_READY',legacy_research_release_id=research.get('research_release_id'),research_release_id=context['context_token'],legacy_research_counts=research.pop('research_counts',None))
                return self.send(200,dict(service_state='READY',service_mode='V4_DEFAULT_WORKBENCH',service_control_contract=CONTRACT,product_version='V4',default_ui='V4',
                    current_accepted_reader=True,shadow_diagnostics=True,legacy_v3_default=False,read_only_ui=True,
                    **control,**research))
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
