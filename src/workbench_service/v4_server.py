"""V4_DEFAULT_WORKBENCH_SERVICE_V1. Product version and permissions are separate."""
import json
import hashlib
import threading
from datetime import datetime
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .current_v4_context import CurrentAcceptedV4Reader
from .shadow_server import make_shadow_handler
from .research_bff import ResearchBFF
from .joint_release import load as joint_load,checked_path,recover


def _require_candidate_contract_proofs(context):
    """Require exact publication-bound contract approval evidence at the BFF edge."""
    from workbench_db.v4_publication_reader import PublicationReadError

    contracts=context.get('contracts') if isinstance(context,dict) else None
    if not isinstance(contracts,dict) or not contracts:
        raise PublicationReadError('PG_CANDIDATE_CONTRACT_PROOF_REQUIRED')
    publication_id=context.get('publication_id')
    trade_date=context.get('trade_date')
    namespace=context.get('model_namespace_id')
    accepted_at=context.get('accepted_at')
    for contract_id,proof in contracts.items():
        digest=proof.get('raw_sha256') if isinstance(proof,dict) else None
        if (not isinstance(contract_id,str) or not contract_id
                or not isinstance(proof,dict)
                or not isinstance(digest,str) or len(digest)!=64
                or any(ch not in '0123456789abcdef' for ch in digest)
                or proof.get('publication_id')!=publication_id
                or proof.get('trade_date')!=trade_date
                or proof.get('namespace')!=namespace
                or proof.get('accepted_at')!=accepted_at
                or proof.get('approval_source_sha256')!=digest
                or not proof.get('version') or not proof.get('schema_version')
                or not proof.get('accepted_at') or not proof.get('approved_by')
                or not proof.get('approval_ref') or not proof.get('approval_source_revision')
                or not proof.get('approval_occurred_at') or not proof.get('approval_recorded_at')):
            raise PublicationReadError('PG_CANDIDATE_CONTRACT_PROOF_INVALID')
        try:
            accepted=datetime.fromisoformat(str(proof['accepted_at']).replace('Z','+00:00'))
            occurred=datetime.fromisoformat(str(proof['approval_occurred_at']).replace('Z','+00:00'))
            recorded=datetime.fromisoformat(str(proof['approval_recorded_at']).replace('Z','+00:00'))
        except (TypeError,ValueError) as error:
            raise PublicationReadError('PG_CANDIDATE_CONTRACT_PROOF_INVALID') from error
        if (accepted.tzinfo is None or occurred.tzinfo is None or recorded.tzinfo is None
                or occurred>accepted or recorded>accepted):
            raise PublicationReadError('PG_CANDIDATE_CONTRACT_PROOF_INVALID')


def make_v4_handler(root, pg_current_adapter=None, *, allow_pg_candidate=False, pg_research_candidate_schema=None):
    """Build the V4 BFF; PG candidates require explicit injection and opt-in."""
    root=Path(root)
    recover(root)
    # A PG research candidate is an independent development surface. Do not
    # instantiate the file-backed accepted Head reader on that route: even a
    # harmless context/status request must remain bound to the PG snapshot.
    reader=(None if pg_research_candidate_schema else
            CurrentAcceptedV4Reader(root,require_runtime=True))
    base=make_shadow_handler(root)
    static=root/'src/workbench_service/static'
    bff=ResearchBFF(root)
    operational_cache={};operational_lock=threading.RLock()
    pg_research_candidate_cache={};pg_research_candidate_lock=threading.RLock()

    def operational_reader():
        from workbench_analysis.operational_successor_v1 import CONTRACT as DAILY_CONTRACT, accepted_api
        from workbench_db.v4_operational_live_head_pg_r1 import read_current
        current=read_current(root)
        candidate=current['candidate']
        # Runtime contract bytes are loaded from the approved PG Registry by
        # verify_policy; no workspace policy or Owner authority file selects it.
        signature=(current['head_sha256'],current['generation'],
                   current['database_identity']['database_oid'])
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
            if parsed.path.startswith('/api/v4/') and not parsed.path.startswith(('/api/v4/shadow/','/api/v4/current/')):
                if pg_research_candidate_schema:
                    values=parse_qs(parsed.query,keep_blank_values=True)
                    if any(len(v)!=1 for v in values.values()):return self.send(400,dict(code='DUPLICATE_PARAMETER'))
                    if len(self.path)>4096:return self.send(414,dict(code='REQUEST_TOO_LONG'))
                    if not bff.allowed(self.client_address[0]):return self.send(429,dict(code='RATE_LIMIT',retry_after_seconds=60))
                    try:
                        with pg_research_candidate_lock:
                            candidate=pg_research_candidate_cache.get('reader')
                            if candidate is None:
                                from .production_v4 import ProductionV4ResearchReader
                                candidate=ProductionV4ResearchReader(root,pg_candidate_schema=pg_research_candidate_schema)
                                pg_research_candidate_cache['reader']=candidate
                        code,payload=bff.get_with_reader(parsed.path.removeprefix('/api/v4/'),{k:v[0] for k,v in values.items()},candidate)
                        return self.send(code,payload)
                    except (ValueError,KeyError,OSError,RuntimeError) as error:
                        return self.send(503,dict(status='BLOCKED',code='PG_RESEARCH_CANDIDATE_UNAVAILABLE',reason=str(error)))
                try:
                    operational=operational_reader()
                except (ValueError,KeyError,OSError) as error:
                    return self.send(503,dict(code='OPERATIONAL_ACCEPTED_SOURCE_INVALID',reason=str(error)))
                if operational is not None:
                    from .r43_operational_bff import OperationalResearchBFF
                    from .operational_successor_bff_v1 import OperationalSuccessorBFFV1
                    from workbench_analysis.operational_successor_v1 import CONTRACT as DAILY_CONTRACT
                    try:
                        values=parse_qs(parsed.query,keep_blank_values=True)
                        if any(len(v)!=1 for v in values.values()):raise ValueError('DUPLICATE_PARAMETER')
                        projector=OperationalSuccessorBFFV1 if operational.candidate.get('contract_id')==DAILY_CONTRACT else OperationalResearchBFF
                        code,payload=projector(operational,bff).get(parsed.path,{k:v[0] for k,v in values.items()})
                        return self.send(code,payload)
                    except (ValueError,KeyError) as error:
                        return self.send(409 if str(error)=='CONTEXT_TOKEN_MISMATCH' else 400,dict(code='INVALID_OPERATIONAL_QUERY',reason=str(error)))
            if parsed.path in ('/','/v4','/v4/') or parsed.path.startswith('/v4/research/'):
                authority=root/'config/v4_research_ui_authority_v1.json'
                try:
                    mode=('SIX_ENTRY' if pg_research_candidate_schema else
                          json.loads(authority.read_bytes())['mode'] if authority.exists() else 'LEGACY_SUMMARY')
                except (ValueError,OSError,KeyError):return self.send(503,dict(code='UI_AUTHORITY_INVALID'))
                if mode not in ('SIX_ENTRY','LEGACY_SUMMARY'):return self.send(503,dict(code='UI_AUTHORITY_INVALID'))
                page=static/('research/index.html' if mode=='SIX_ENTRY' else 'v4-workbench.html')
                joint=None if pg_research_candidate_schema else joint_load(root)
                if joint:page=checked_path(root,joint['ui_assets']['index.html'])
                return self.send(200,page.read_bytes(),'text/html; charset=utf-8')
            if parsed.path=='/v4/legacy-summary':
                return self.send(200,(static/'v4-workbench.html').read_bytes(),'text/html; charset=utf-8')
            if parsed.path.startswith('/v4/assets/'):
                name=parsed.path.removeprefix('/v4/assets/')
                if name not in ('app.js','api.js','components.js','labels.js','stock.js','replay.js','style.css'):return self.send(404,dict(code='ASSET_NOT_FOUND'))
                joint=None if pg_research_candidate_schema else joint_load(root)
                asset=checked_path(root,joint['ui_assets'][name]) if joint else static/'research'/name
                if name in ('api.js','components.js','app.js') and not pg_research_candidate_schema:
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
                if pg_research_candidate_schema:
                    try:
                        with pg_research_candidate_lock:
                            candidate=pg_research_candidate_cache.get('reader')
                            if candidate is None:
                                from .production_v4 import ProductionV4ResearchReader
                                candidate=ProductionV4ResearchReader(root,pg_candidate_schema=pg_research_candidate_schema)
                                pg_research_candidate_cache['reader']=candidate
                        context=candidate.context
                        return self.send(200,dict(
                            service_state='READY',service_mode='V4_PG_RESEARCH_CANDIDATE',
                            product_version='V4',default_ui='V4',read_only_ui=True,
                            research_ui_contract='V4_SIX_ENTRY_SHELL_V1',
                            research_snapshot_state='PG_CANDIDATE_SNAPSHOT',
                            research_counts=candidate.manifest['counts'],
                            research_release_id=context['release_id'],
                            accepted_trade_date=context['accepted_trade_date'],
                            daily_worker_status='PG_SNAPSHOT_ONLY_NO_DAILY_WORKER_STATUS',
                            jobs_enabled=False,production_permission=False,
                        ))
                    except (ValueError,KeyError,OSError,RuntimeError) as error:
                        return self.send(503,dict(service_state='BLOCKED',service_mode='V4_PG_RESEARCH_CANDIDATE',
                            reason='PG_RESEARCH_CANDIDATE_UNAVAILABLE',detail=type(error).__name__))
                research={}
                if (root/'config/v4_research_snapshot_authority_v1.json').exists():
                    try:
                        current=bff.current()
                        research=dict(research_ui_contract='V4_SIX_ENTRY_SHELL_V1',research_snapshot_state='READY',research_counts=current.manifest['counts'],research_release_id=current.context['release_id'])
                    except (ValueError,OSError,KeyError) as error:
                        return self.send(503,dict(service_state='BLOCKED',service_mode='V4_DEFAULT_WORKBENCH',reason='RESEARCH_SNAPSHOT_INVALID',detail=type(error).__name__))
                if reader is None:return self.send(503,dict(service_state='BLOCKED',reason='CURRENT_ACCEPTED_READER_UNAVAILABLE'))
                code,payload=reader.read('context')
                if code!=200:return self.send(code,dict(service_state='BLOCKED',service_mode='V4_DEFAULT_WORKBENCH',reason=payload))
                try:operational=operational_reader()
                except (ValueError,KeyError,OSError) as error:
                    return self.send(503,dict(service_state='BLOCKED',service_mode='V4_DEFAULT_WORKBENCH',reason='OPERATIONAL_ACCEPTED_SOURCE_INVALID',detail=str(error)))
                legacy_context=payload['context']
                control=dict(legacy_context)
                control.update(current_operational_trade_date=None,strict_pit_legacy_trade_date=legacy_context['accepted_trade_date'],legacy_strict_pit_date=legacy_context['accepted_trade_date'],operational_accepted_trade_date=None,control_date_source='LEGACY_STRICT_PIT_HEAD',strict_pit_context_token=legacy_context.get('context_token'))
                if operational is not None:
                    context=operational.context()
                    control.update(context,current_operational_trade_date=context['accepted_trade_date'],operational_accepted_trade_date=context['accepted_trade_date'],control_date_source='USER_AUTHORIZED_OPERATIONAL_HEAD' if context.get('authorization_mode')=='DIRECT_HUMAN_USER' else 'INDEPENDENTLY_ACCEPTED_OPERATIONAL_HEAD')
                    research.update(research_snapshot_state='OPERATIONAL_SCOPED_READY',legacy_research_release_id=research.get('research_release_id'),research_release_id=context['context_token'],legacy_research_counts=research.pop('research_counts',None))
                return self.send(200,dict(service_state='READY',service_mode='V4_DEFAULT_WORKBENCH',service_control_contract='V4_DEFAULT_WORKBENCH_SERVICE_V1',product_version='V4',default_ui='V4',
                    current_accepted_reader=True,shadow_diagnostics=True,legacy_v3_default=False,read_only_ui=True,
                    production_permission=payload['production_permission'],**control,**research))
            if parsed.path.startswith('/api/v4/current/'):
                values=parse_qs(parsed.query,keep_blank_values=True)
                if any(len(v)!=1 for v in values.values()):return self.send(409,dict(status='BLOCKED',code='DUPLICATE_CONTEXT_PARAMETER'))
                allowed={'q','state','limit','offset','context_token','source','trade_date','model_namespace_id'}
                if set(values)-allowed:return self.send(400,dict(status='BLOCKED',code='UNKNOWN_CONTEXT_PARAMETER'))
                query={k:v[0] for k,v in values.items()}
                if query.get('source')=='pg_candidate':
                    if not allow_pg_candidate:
                        return self.send(404,dict(status='BLOCKED',code='PG_CANDIDATE_MODE_DISABLED'))
                    if pg_current_adapter is None:
                        return self.send(503,dict(status='BLOCKED',code='PG_CANDIDATE_READER_UNAVAILABLE'))
                    required=('trade_date','model_namespace_id','context_token')
                    if any(not query.get(key) for key in required):
                        return self.send(400,dict(status='BLOCKED',code='PG_CANDIDATE_CONTEXT_REQUIRED',required=list(required)))
                    try:
                        payload=pg_current_adapter.read_endpoint(
                            parsed.path,trade_date=query['trade_date'],
                            model_namespace_id=query['model_namespace_id'],
                            expected_context_token=query['context_token'],
                        )
                        context=payload.get('context') if isinstance(payload,dict) else None
                        if isinstance(context,dict):
                            _require_candidate_contract_proofs(context)
                            workspace_mapping=context.get('workspace_owner_mapping')
                            if not isinstance(workspace_mapping,dict):
                                raise ValueError('WORKSPACE_OWNER_MAPPING_NOT_BOUND_TO_PUBLICATION')
                            if context.get('model_namespace_id') != workspace_mapping['model_namespace_id']:
                                raise ValueError('WORKSPACE_PUBLICATION_NAMESPACE_MISMATCH')
                            if context.get('database_identity') != workspace_mapping['database_identity']:
                                raise ValueError('WORKSPACE_DATABASE_IDENTITY_MISMATCH')
                            for family,binding in context.get('module_results',{}).items():
                                if binding.get('owner_schema') != workspace_mapping['owner_schemas'].get(family):
                                    raise ValueError('WORKSPACE_OWNER_SCHEMA_MISMATCH:'+str(family))
                        from workbench_db.v4_native import workspace_namespace_identity
                        payload['workspace_identity']=workspace_namespace_identity(root,'publication')
                        payload['workspace_mapping']=workspace_mapping
                    except Exception as error:
                        # PG candidate reads are isolated from the file reader. A missing
                        # Head, Owner or read privilege is returned as a candidate error.
                        from workbench_db.v4_publication_reader import PublicationReadError
                        if isinstance(error, (PublicationReadError, ValueError)):
                            reason=str(error)
                        else:
                            reason=type(error).__name__
                        state=(
                            'NO_READER_PRIVILEGE' if ('READER' in reason or 'PERMISSION' in reason) else
                            'PENDING_PG_HEAD' if ('PUBLICATION' in reason or 'HEAD' in reason) else
                            'NOT_PIT_ELIGIBLE' if ('PIT' in reason or 'ACCEPTANCE' in reason) else
                            'DATA_MISSING'
                        )
                        return self.send(409,dict(status='BLOCKED',data_state=state,code='PG_CANDIDATE_READ_FAILED',reason=reason))
                    return self.send(200,payload)
                if query.get('source','file')!='file':
                    return self.send(400,dict(status='BLOCKED',code='CURRENT_SOURCE_UNSUPPORTED'))
                query.pop('source',None)
                if reader is None:return self.send(503,dict(status='BLOCKED',code='CURRENT_ACCEPTED_READER_UNAVAILABLE'))
                code,payload=reader.read(parsed.path.removeprefix('/api/v4/current/'),query)
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


def pg_candidate_adapter_from_environment(environ=None, *, workspace_root=None):
    """Build the read-only candidate adapter from explicit, non-secret DB identity config."""
    import os
    env = os.environ if environ is None else environ
    raw = env.get('V4_PG_EXPECTED_DATABASE_IDENTITY_JSON')
    if not raw:
        raise RuntimeError('V4_PG_EXPECTED_DATABASE_IDENTITY_REQUIRED')
    try:
        identity = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as error:
        raise RuntimeError('V4_PG_EXPECTED_DATABASE_IDENTITY_INVALID') from error
    if (not isinstance(identity, dict)
            or set(identity) != {'database', 'database_oid', 'host', 'port'}
            or not isinstance(identity.get('database'), str)
            or isinstance(identity.get('database_oid'), bool)
            or not isinstance(identity.get('database_oid'), int)
            or not isinstance(identity.get('host'), str)
            or isinstance(identity.get('port'), bool)
            or not isinstance(identity.get('port'), int)):
        raise RuntimeError('V4_PG_EXPECTED_DATABASE_IDENTITY_INVALID')
    from workbench_db.v4_publication_reader import PgPublicationReader
    from .v4_pg_current_adapter import PgV4CurrentAdapter
    return PgV4CurrentAdapter(PgPublicationReader(
        expected_database_identity=identity,
        workspace_root=str(Path(workspace_root).resolve()) if workspace_root is not None else None,
    ))


def serve_v4_candidate(root, pg_current_adapter=None, *, pg_research_candidate_schema=None):
    """Explicit candidate-only BFF on the one development port; never production."""
    if pg_current_adapter is None:
        pg_current_adapter = pg_candidate_adapter_from_environment(workspace_root=root)
    ThreadingHTTPServer(
        ('127.0.0.1',28766),
        make_v4_handler(root,pg_current_adapter,allow_pg_candidate=True,
                        pg_research_candidate_schema=pg_research_candidate_schema),
    ).serve_forever()
