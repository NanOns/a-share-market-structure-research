"""V4_DEFAULT_WORKBENCH_SERVICE_V1. Product version and permissions are separate."""
import json
import hashlib
import os
import threading
from datetime import datetime
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .current_v4_context import CurrentAcceptedV4Reader
from .shadow_server import make_shadow_handler
from .research_bff import ResearchBFF
from .joint_release import recover


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


def _daily_source_runtime_receipts_preview(root):
    """Expose recent, digest-checked BaoStock runtime receipts in candidate UI.

    These source receipts describe available date inputs only. They do not
    authorize a publication, accepted calendar, PIT use, or operational Head.
    """
    from workbench_db.v4_baostock_runtime_acceptance_pg_r1 import FOLDER, KIND, CONTRACT
    from workbench_db.v4_forward_pg_r1 import ForwardFactStore, canonical, digest
    from workbench_db.v4_native import connection

    namespace = ForwardFactStore.namespace_for(Path(root) / FOLDER)
    with connection('v4', read_only=True) as pg:
        rows = pg.execute(
            """SELECT fact_key,payload,payload_sha256 FROM v4.forward_facts
                 WHERE workspace_namespace=%s AND kind=%s
                 ORDER BY fact_key DESC LIMIT 5""",
            (namespace, KIND),
        ).fetchall()
    receipts = []
    for day, payload, stored_digest in rows:
        raw = payload.encode('utf-8') if isinstance(payload, str) else canonical(payload)
        if digest(raw) != stored_digest:
            raise ValueError('DAILY_RUNTIME_RECEIPT_PAYLOAD_DIGEST_MISMATCH')
        record = json.loads(raw.decode('utf-8'))
        manifest = record.get('manifest') if isinstance(record, dict) else None
        smoke = manifest.get('live_smoke') if isinstance(manifest, dict) else None
        if (not isinstance(record, dict) or not isinstance(manifest, dict) or not isinstance(smoke, dict)
                or record.get('contract_id') != CONTRACT or record.get('trade_date') != day
                or manifest.get('status') != 'ACCEPTED' or smoke.get('target_date') != day):
            raise ValueError('DAILY_RUNTIME_RECEIPT_BINDING_INVALID')
        receipts.append(dict(
            trade_date=day,
            receipt_status='ACCEPTED_RUNTIME_RECEIPT',
            daily_rows=smoke.get('daily', {}).get('row_count'),
            factor_rows=smoke.get('adjustment_factor', {}).get('row_count'),
            payload_sha256=stored_digest,
        ))
    return dict(
        status='READABLE' if receipts else 'NO_RECEIPTS',
        authority='PG_ACCEPTED_DAILY_RUNTIME_FACT',
        publication_status='NOT_IMPLIED',
        receipts=receipts,
    )


def make_v4_handler(root, pg_current_adapter=None, *, allow_pg_candidate=False, pg_candidate_release_id=None, static_root=None):
    """Build the V4 BFF; PG candidates require explicit injection and opt-in."""
    root=Path(root)
    candidate_target=pg_candidate_release_id
    candidate_enabled=bool(candidate_target)
    if not candidate_enabled:
        recover(root)
    # The six-entry workbench reads the approved current contract, whose
    # bindings are resolved from the fixed V4 schema. Research-release and
    # publication candidates remain separate, explicit request modes.
    reader=CurrentAcceptedV4Reader(root,require_runtime=True)
    base=make_shadow_handler(root)
    static=Path(static_root) if static_root is not None else root/'src/workbench_service/static'
    bff=ResearchBFF(root)
    operational_cache={};operational_lock=threading.RLock()
    pg_research_candidate_cache={};pg_research_candidate_lock=threading.RLock()
    def candidate_reader():
        with pg_research_candidate_lock:
            current=pg_research_candidate_cache.get('reader')
            if current is None:
                from .production_v4 import ProductionV4ResearchReader
                current=ProductionV4ResearchReader(root,candidate_release_id=candidate_target)
                pg_research_candidate_cache['reader']=current
            return current

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
            if candidate_enabled and parsed.path=='/v4/research/data-update':
                return self.send(200,(static/'daily-update/index.html').read_bytes(),'text/html; charset=utf-8')
            if candidate_enabled and parsed.path=='/v4/daily-update.js':
                return self.send(200,(static/'daily-update/app.js').read_bytes(),'application/javascript; charset=utf-8')
            if candidate_enabled and parsed.path.startswith('/api/v4/operations/daily-update/'):
                values=parse_qs(parsed.query,keep_blank_values=True)
                if any(len(v)!=1 for v in values.values()):return self.send(400,dict(code='DUPLICATE_PARAMETER'))
                tail=parsed.path.removeprefix('/api/v4/operations/daily-update/').strip('/').split('/')
                try:
                    if tail==['status']:
                        context=candidate_reader().context
                        source_receipts=_daily_source_runtime_receipts_preview(root)
                        return self.send(200,dict(contract_id='V4_DAILY_STATUS_CANDIDATE_PREVIEW_R1',
                            status='PREVIEW_ONLY',last_good_trade_date=context['accepted_trade_date'],
                            missing_sessions=None,calendar_status='NO_ACCEPTED_MARKET_CALENDAR_HEAD',
                            context_token=context.get('context_token'),publication_id=context.get('publication_id'),
                            database_identity=context.get('database_identity'),source_mode='PG_CANDIDATE_SNAPSHOT',
                            jobs_enabled=False,worker_status='NOT_STARTED',
                            settings=dict(auto_enabled=False,service_alive=False,
                                operational_mode='CANDIDATE_PREVIEW_NO_WORKER',publication_ready=False),
                            daily_source_runtime_receipts=source_receipts,
                            last_job=None,active_job=None,last_catch_up_job=None,worker_error=None))
                    if tail==['settings']:
                        return self.send(200,dict(auto_enabled=False,service_alive=False,
                            operational_mode='CANDIDATE_PREVIEW_NO_WORKER',permission_scope='READ_ONLY_PG_SNAPSHOT'))
                    if tail==['progress']:
                        # Candidate preview has deliberately disabled the daily
                        # scheduler and does not provision its job schema. Keep
                        # polling truthful and deterministic without probing a
                        # missing table or presenting a transient PG error as
                        # a broken preview.
                        return self.send(200,dict(contract_id='V4_DAILY_PROGRESS_R1',
                            stage_state='PREVIEW_ONLY',mode=None,job_mode=None,
                            target_trade_date=None,started_at=None,finished_at=None,
                            error_code=None,stage=None,processed=None,total=None,
                            unit=None,recent_message='Daily worker is disabled in candidate preview',
                            eta_seconds=None,error_detail=None,head_unchanged=True,
                            worker_error=None,last_published_trade_date=None,
                            jobs_enabled=False,worker_status='NOT_STARTED'))
                    if len(tail)==2 and tail[0]=='jobs':
                        from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobsReadOnly
                        return self.send(200,DailyJobsReadOnly(root).job(tail[1]))
                    if len(tail)==3 and tail[0]=='jobs' and tail[2]=='events':
                        from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobsReadOnly
                        after=int(values.get('after',['0'])[0])
                        return self.send(200,dict(events=DailyJobsReadOnly(root).events(tail[1],after)))
                    if tail==['releases']:
                        return self.send(200,dict(current=None,predecessors=[],
                            status='NO_OPERATIONAL_HEAD_IN_CANDIDATE_PREVIEW'))
                    return self.send(404,dict(code='DAILY_ROUTE_NOT_FOUND'))
                except (ValueError,KeyError,OSError,RuntimeError) as error:
                    return self.send(503,dict(code='DAILY_PG_STATUS_UNAVAILABLE',fallback=False,reason=str(error)[:160]))
                except Exception as error:
                    import psycopg
                    if isinstance(error,psycopg.Error):
                        return self.send(503,dict(code='DAILY_PG_STATUS_UNAVAILABLE',fallback=False))
                    raise
            if parsed.path=='/v4/operational-preview':
                return self.send(200,(static/'r43-operational-preview.html').read_bytes(),'text/html; charset=utf-8')
            if parsed.path.startswith('/api/v4/original-0930/'):
                values=parse_qs(parsed.query,keep_blank_values=True)
                if any(len(v)!=1 for v in values.values()):return self.send(400,dict(code='DUPLICATE_PARAMETER'))
                code,payload=bff.get('/api/v4/'+parsed.path.removeprefix('/api/v4/original-0930/'),{k:v[0] for k,v in values.items()})
                return self.send(code,payload)
            if parsed.path.startswith('/api/v4/') and not parsed.path.startswith(('/api/v4/shadow/','/api/v4/current/')):
                if candidate_enabled:
                    values=parse_qs(parsed.query,keep_blank_values=True)
                    if any(len(v)!=1 for v in values.values()):return self.send(400,dict(code='DUPLICATE_PARAMETER'))
                    if len(self.path)>4096:return self.send(414,dict(code='REQUEST_TOO_LONG'))
                    if not bff.allowed(self.client_address[0]):return self.send(429,dict(code='RATE_LIMIT',retry_after_seconds=60))
                    try:
                        with pg_research_candidate_lock:
                            candidate=pg_research_candidate_cache.get('reader')
                            if candidate is None:
                                from .production_v4 import ProductionV4ResearchReader
                                candidate=ProductionV4ResearchReader(root,candidate_release_id=candidate_target)
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
                # V4's default product page is a shipped frontend asset. Do
                # not let a workspace JSON pointer choose the live UI shell.
                page=static/'research/index.html'
                return self.send(200,page.read_bytes(),'text/html; charset=utf-8')
            if parsed.path=='/v4/legacy-summary':
                return self.send(200,(static/'v4-workbench.html').read_bytes(),'text/html; charset=utf-8')
            if parsed.path.startswith('/v4/assets/'):
                name=parsed.path.removeprefix('/v4/assets/')
                if name not in ('app.js','api.js','components.js','labels.js','stock.js','replay.js','style.css'):return self.send(404,dict(code='ASSET_NOT_FOUND'))
                # Frontend source assets are ordinary code resources. An
                # operational compatibility asset, when present, is instead
                # selected by the PG Head-bound registry below.
                asset=static/'research'/name
                if name in ('api.js','components.js','app.js') and not candidate_enabled:
                    try:operational=operational_reader()
                    except (ValueError,KeyError,OSError) as error:return self.send(503,dict(code='OPERATIONAL_ACCEPTED_SOURCE_INVALID',reason=str(error)))
                    if operational is not None:
                        relative='src/workbench_service/static/r43-compat/'+name
                        from workbench_db.v4_operational_registry_pg_r1 import read_registry
                        registry=read_registry(root,operational.candidate)
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
                if candidate_enabled:
                    try:
                        with pg_research_candidate_lock:
                            candidate=pg_research_candidate_cache.get('reader')
                            if candidate is None:
                                from .production_v4 import ProductionV4ResearchReader
                                candidate=ProductionV4ResearchReader(root,candidate_release_id=candidate_target)
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
                try:
                    current=bff.current()
                    research=dict(research_ui_contract='V4_SIX_ENTRY_SHELL_V1',research_snapshot_state='READY',research_counts=current.manifest['counts'],research_release_id=current.context['release_id'])
                except (ValueError,OSError,KeyError):
                    research=dict(research_ui_contract='V4_SIX_ENTRY_SHELL_V1',research_snapshot_state='UNAVAILABLE_FROM_PG')
                if pg_current_adapter is not None:
                    try:
                        payload=pg_current_adapter.read_current_endpoint('/api/v4/current/summary')
                    except Exception as error:
                        return self.send(503,dict(service_state='BLOCKED',service_mode='V4_DEFAULT_WORKBENCH',
                            reason='PG_CURRENT_PUBLICATION_UNAVAILABLE',detail=type(error).__name__))
                    legacy_context=payload.get('context',{})
                    production_permission=legacy_context.get('production_permission',{})
                else:
                    if reader is None:return self.send(503,dict(service_state='BLOCKED',reason='CURRENT_ACCEPTED_READER_UNAVAILABLE'))
                    code,payload=reader.read('context')
                    if code!=200:return self.send(code,dict(service_state='BLOCKED',service_mode='V4_DEFAULT_WORKBENCH',reason=payload))
                    legacy_context=payload['context'];production_permission=payload['production_permission']
                try:operational=operational_reader()
                except (ValueError,KeyError,OSError) as error:
                    return self.send(503,dict(service_state='BLOCKED',service_mode='V4_DEFAULT_WORKBENCH',reason='OPERATIONAL_ACCEPTED_SOURCE_INVALID',detail=str(error)))
                control=dict(legacy_context)
                control.update(current_operational_trade_date=None,strict_pit_legacy_trade_date=legacy_context['accepted_trade_date'],legacy_strict_pit_date=legacy_context['accepted_trade_date'],operational_accepted_trade_date=None,control_date_source='LEGACY_STRICT_PIT_HEAD',strict_pit_context_token=legacy_context.get('context_token'))
                if operational is not None:
                    context=operational.context()
                    control.update(context,current_operational_trade_date=context['accepted_trade_date'],operational_accepted_trade_date=context['accepted_trade_date'],control_date_source='USER_AUTHORIZED_OPERATIONAL_HEAD' if context.get('authorization_mode')=='DIRECT_HUMAN_USER' else 'INDEPENDENTLY_ACCEPTED_OPERATIONAL_HEAD')
                    research.update(research_snapshot_state='OPERATIONAL_SCOPED_READY',legacy_research_release_id=research.get('research_release_id'),research_release_id=context['context_token'],legacy_research_counts=research.pop('research_counts',None))
                return self.send(200,dict(service_state='READY',service_mode='V4_DEFAULT_WORKBENCH',service_control_contract='V4_DEFAULT_WORKBENCH_SERVICE_V1',product_version='V4',default_ui='V4',
                    current_accepted_reader=True,shadow_diagnostics=True,legacy_v3_default=False,read_only_ui=True,
                    production_permission=production_permission,**control,**research))
            if parsed.path.startswith('/api/v4/current/'):
                values=parse_qs(parsed.query,keep_blank_values=True)
                if any(len(v)!=1 for v in values.values()):return self.send(409,dict(status='BLOCKED',code='DUPLICATE_CONTEXT_PARAMETER'))
                allowed={'q','state','limit','offset','context_token','source','trade_date','model_namespace_id'}
                if set(values)-allowed:return self.send(400,dict(status='BLOCKED',code='UNKNOWN_CONTEXT_PARAMETER'))
                query={k:v[0] for k,v in values.items()}
                if pg_current_adapter is not None and query.get('source')=='pg_publication':
                    try:
                        payload=pg_current_adapter.read_current_endpoint(parsed.path,
                            expected_context_token=query.get('context_token'),
                            trade_date=query.get('trade_date'),
                            model_namespace_id=query.get('model_namespace_id'))
                        context=payload.get('context') if isinstance(payload,dict) else None
                        if isinstance(context,dict):
                            _require_candidate_contract_proofs(context)
                            mapping=context.get('workspace_owner_mapping')
                            if mapping is not None:
                                if context.get('model_namespace_id')!=mapping.get('model_namespace_id'):
                                    raise ValueError('WORKSPACE_PUBLICATION_NAMESPACE_MISMATCH')
                                if context.get('database_identity')!=mapping.get('database_identity'):
                                    raise ValueError('WORKSPACE_DATABASE_IDENTITY_MISMATCH')
                                for family,binding in context.get('module_results',{}).items():
                                    if binding.get('owner_schema')!=mapping.get('owner_schemas',{}).get(family):
                                        raise ValueError('WORKSPACE_OWNER_SCHEMA_MISMATCH:'+str(family))
                        return self.send(200,payload)
                    except Exception as error:
                        from workbench_db.v4_publication_reader import PublicationReadError
                        reason=str(error) if isinstance(error,(PublicationReadError,ValueError)) else type(error).__name__
                        return self.send(409,dict(status='BLOCKED',code='PG_CURRENT_READ_FAILED',reason=reason))
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

        def do_POST(self):
            if candidate_enabled and self.path.startswith('/api/v4/operations/daily-update/'):
                return self.send(403,dict(code='CANDIDATE_PREVIEW_WRITE_DISABLED',jobs_started=False))
            return self.send(501,dict(code='METHOD_NOT_SUPPORTED'))

        def do_PUT(self):
            if candidate_enabled and self.path.startswith('/api/v4/operations/daily-update/'):
                return self.send(403,dict(code='CANDIDATE_PREVIEW_WRITE_DISABLED',jobs_started=False))
            return self.send(501,dict(code='METHOD_NOT_SUPPORTED'))

    return Handler


def serve_v4(root,host='127.0.0.1',port=28765):
    adapter=pg_candidate_adapter_from_environment(workspace_root=root)
    candidate_release_id=os.environ.get('V4_PG_RESEARCH_CANDIDATE_RELEASE_ID')
    ThreadingHTTPServer((host,port),make_v4_handler(root,adapter,allow_pg_candidate=True,
        pg_candidate_release_id=candidate_release_id)).serve_forever()


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


def serve_v4_candidate(root, pg_current_adapter=None, *, candidate_release_id=None):
    """Explicit candidate-only BFF on the one development port; never production."""
    if pg_current_adapter is None:
        pg_current_adapter = pg_candidate_adapter_from_environment(workspace_root=root)
    candidate_release_id=(candidate_release_id or os.environ.get('V4_PG_RESEARCH_CANDIDATE_RELEASE_ID'))
    if not candidate_release_id:
        raise RuntimeError('V4_PG_RESEARCH_CANDIDATE_RELEASE_ID_REQUIRED')
    ThreadingHTTPServer(
        ('127.0.0.1',28766),
        make_v4_handler(root,pg_current_adapter,allow_pg_candidate=True,
                        pg_candidate_release_id=candidate_release_id),
    ).serve_forever()
