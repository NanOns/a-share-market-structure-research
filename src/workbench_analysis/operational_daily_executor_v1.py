"""Real bounded source stages; no fabricated successor Owner or publication."""
from pathlib import Path, PureWindowsPath
from datetime import datetime,timezone
import json
import os
from . import tdx_official_daily_source as tdx
from .tdx_latest_daily_source_v2 import capture_latest_tdx_package,extract_target_session_bars
from .operational_daily_storage_v1 import output_path,atomic_json
from .baostock_supplemental import package_metadata
from .baostock_dm01_sdk_schema_v2 import normalize_response
from .baostock_daily_update_source import DAILY_METHOD,FACTOR_METHOD,_canonical_rows_digest
from .source_readiness_v2 import source_readiness


def _load_daily_contract_record_from_pg(contract_id, version):
    """Load a daily runtime contract only from its approved PG registry entry."""
    namespace=os.environ.get('V4_PG_MODEL_NAMESPACE_ID','').strip()
    try:expected_identity=json.loads(os.environ.get('V4_PG_EXPECTED_DATABASE_IDENTITY_JSON','{}'))
    except ValueError as exc:raise ValueError('PG_DATABASE_IDENTITY_CONFIGURATION_INVALID') from exc
    from .contract_registry_pg_v1 import load_current_approved_contract
    from workbench_db.v4_publication_reader import readonly_connection,PgPublicationReader
    with readonly_connection() as pg:
        identity=PgPublicationReader._read_database_identity(pg)
        if expected_identity and identity!=expected_identity:raise ValueError('DAILY_CONTRACT_DATABASE_IDENTITY_MISMATCH')
        if not namespace:
            rows=pg.execute('SELECT namespace FROM v4.contract_versions WHERE contract_id=%s AND version=%s',
                            (contract_id,version)).fetchall()
            if len(rows)!=1:raise ValueError('DAILY_CONTRACT_NAMESPACE_NOT_UNIQUE')
            namespace=str(rows[0][0])
        registered=load_current_approved_contract(pg,contract_id,version,namespace,
            expected_database_identity=identity)
    return registered

def _load_daily_contract_from_pg(contract_id, version):
    return _load_daily_contract_record_from_pg(contract_id,version).parsed_json


def _daily_runtime_contract(contract_id, version, *, version_field='contract_version'):
    """Resolve an approved daily runtime contract; file fallback is forbidden."""
    if os.environ.get('V4_DAILY_CONTRACT_SOURCE','PG')!='PG':
        raise ValueError('DAILY_RUNTIME_CONTRACT_PG_ONLY')
    contract=_load_daily_contract_from_pg(contract_id,version)
    if not isinstance(contract,dict) or contract.get('contract_id')!=contract_id or contract.get(version_field)!=version:
        raise ValueError('DAILY_RUNTIME_CONTRACT_IDENTITY_INVALID')
    return contract

def readiness_binding_revision(source_revision_id,source_freeze,dependencies):
    return tdx.sha256_bytes(tdx._json_bytes(dict(
        contract_id='DYNAMIC_DAILY_READY_BINDING_IDENTITY_R3',
        source_revision_id=source_revision_id,source_freeze=source_freeze,
        dependency_bindings=dependencies)))


def _load_pg_runtime_acceptance(root, day):
    """Load manifest, receipt and exact response bytes from the dated PG fact."""
    from workbench_db.v4_baostock_runtime_acceptance_pg_r1 import load, export_native_response
    bundle = load(root, day, sdk=package_metadata())
    cache = Path(root) / 'data/v4/runtime_pg_ingress_cache/baostock' / day.replace('-', '')
    manifest_path = cache / 'accepted_runtime_manifest.json'
    atomic_json(root, manifest_path, bundle['manifest'])
    native_binding = export_native_response(root, bundle)
    return dict(manifest=bundle['manifest'], receipt=bundle['smoke_receipt'],
                raw=bundle['native_response']['payload'],
                raw_path=Path(root) / native_binding['path'],
                manifest_path=manifest_path, manifest_sha256=tdx.sha256_file(manifest_path),
                native_response_binding=native_binding, bundle=bundle)


def _runtime_acceptance_source_mode():
    mode=os.environ.get('V4_BAOSTOCK_RUNTIME_ACCEPTANCE_SOURCE','PG')
    if mode!='PG':raise ValueError('BAOSTOCK_RUNTIME_ACCEPTANCE_PG_ONLY')
    return mode


def _tdx_gbbq_source_path(project_root=None):
    """Load the configured, read-only TDX source input path."""
    repository_root = Path(__file__).resolve().parents[2]
    project_root = Path(project_root or repository_root).resolve()
    contract = _daily_runtime_contract('V4_DAILY_TDX_READONLY_SOURCE_R1','1.1.0')
    if (contract.get('contract_id') != 'V4_DAILY_TDX_READONLY_SOURCE_R1'
            or contract.get('contract_version') != '1.1.0'
            or contract.get('source_mode') != 'READ_ONLY_INPUT'):
        raise ValueError('DAILY_TDX_SOURCE_PATH_CONTRACT_INVALID')
    raw_path = contract.get('gbbq_relative_path', '')
    relative = Path(raw_path)
    if (not raw_path or relative.is_absolute() or PureWindowsPath(raw_path).is_absolute()
            or '..' in relative.parts or relative.as_posix() != 'T0002/hq_cache/gbbq'):
        raise ValueError('DAILY_TDX_RELATIVE_SOURCE_PATH_INVALID')
    from common.paths import resolve_tdx_root
    return (resolve_tdx_root(project_root) / relative).resolve()


def _accepted_trade_date(root):
    """Resolve the last-good trade date from the accepted PG calendar Head."""
    mode=os.environ.get('V4_MARKET_CALENDAR_SOURCE','PG')
    if mode!='PG':raise ValueError('MARKET_CALENDAR_PG_ONLY')
    from workbench_db.v4_market_calendar_reader_r1 import from_environment
    calendar=from_environment().calendar()
    if calendar.get('status')!='ACCEPTED' or calendar.get('source')!='PG_ACCEPTED_PUBLICATION_HEAD':
        raise ValueError('PG_ACCEPTED_PUBLICATION_HEAD_REQUIRED')
    return calendar['accepted_trade_date']


def _capture_optional_daily_sources(root, day, freeze_binding):
    """Run the optional sidecar only with PG-validated candidate bindings."""
    from .operational_successor_v1 import accepted_api
    from .producer_bootstrap_v1 import capture_daily_sources
    return capture_daily_sources(root,day,freeze_binding,
                                 pg_head_candidate=accepted_api(root).candidate)


def _pg_source_ingest_plan_diagnostic(root, day, result):
    """Persist captured bytes as an explicit PG diagnostic candidate.

    Candidate storage does not grant source acceptance, publication, PIT, or
    Head authority. Those states still require their separate evidence.
    """
    freeze = result.get('source_freeze')
    readiness = result.get('source_readiness')
    if not isinstance(freeze, dict) or not isinstance(readiness, dict):
        return None
    try:
        from workbench_db.v4_daily_source_ingest_r6 import (
            CONTRACT_ID as SOURCE_INGEST_CONTRACT_ID,
            CONTRACT_VERSION as SOURCE_INGEST_CONTRACT_VERSION,
            build_source_ingest_plan,
            persist_diagnostic_source_candidate,
        )
        plan = build_source_ingest_plan(root, trade_date=day,
                                        source_freeze=freeze,
                                        source_readiness=readiness)
    except Exception as exc:
        # Diagnostic bridge failures must not change the existing local daily
        # executor semantics; they still fail closed and are visible to callers.
        return dict(contract_id='V4_DAILY_SOURCE_INGEST_ADAPTER_R6',
                    contract_version='1.0.0', trade_date=day,
                    status='BRIDGE_BLOCKED', acceptance_status=str(exc),
                    write_mode='PLAN_ONLY_NO_DATABASE_IO', persisted=False)
    if plan.get('status') == 'DIAGNOSTIC_ONLY':
        try:
            persisted = persist_diagnostic_source_candidate(root, plan)
        except Exception as exc:
            return dict(contract_id=plan['contract_id'], contract_version=plan['contract_version'],
                trade_date=plan['trade_date'], package_id=plan['package_id'],
                package_sha256=plan['package_sha256'], status=plan['status'],
                acceptance_status=plan['acceptance_status'],
                write_mode='PG_DIAGNOSTIC_CANDIDATE_APPEND', persisted=False,
                persistence_error=str(exc))
    else:
        persisted = dict(persisted=False, write_mode='ACCEPTED_PACKAGE_REQUIRES_PUBLICATION_TRANSACTION')
    return dict(contract_id=plan['contract_id'], contract_version=plan['contract_version'],
                trade_date=plan['trade_date'], package_id=plan['package_id'],
                package_sha256=plan['package_sha256'], status=plan['status'],
                acceptance_status=plan['acceptance_status'],
                source_fact_count=len(plan['source_facts']),
                write_mode=persisted.get('write_mode','PG_DIAGNOSTIC_CANDIDATE_APPEND'),
                persisted=persisted.get('persisted',False),pg_readback=persisted.get('readback'),
                pg_binding=persisted.get('binding'))

def probe_source_revision(day):
    """Three bounded metadata requests; never download ZIP or query full market."""
    from .tdx_latest_daily_source_v2 import _package_validator
    response=tdx._request(tdx.PAGE_URL,timeout=5)
    try:
        page=tdx._read_bounded(response,tdx.DEFAULT_MAX_PAGE_BYTES)
        url=tdx.discover_download_url(page,tdx.validate_official_url(response.geturl()))
    finally:response.close()
    response=tdx._request(tdx.discover_update_info_url(page,url),timeout=5)
    try:info=tdx._read_bounded(response,tdx.DEFAULT_MAX_INFO_BYTES)
    finally:response.close()
    provider,_=tdx.parse_update_date(info);validator=_package_validator(url,5)
    if provider<day or not validator:return dict(verified=False,status='WAIT_TDX')
    return dict(verified=True,revision=tdx.sha256_bytes(tdx._json_bytes(dict(info_sha256=tdx.sha256_bytes(info),validator=validator))),
        provider_date=provider,validator=validator,capture_method='BOUNDED_METADATA_ONLY',
        source_ready=False,reason='EXECUTOR_MUST_VERIFY_ACTUAL_TARGET_AND_THREE_SOURCES')


def execute_sources(root,day,mode,*,capture_only=False,cancelled=lambda:False,readback_url=None,progress=lambda *args:None,pg_publication_context=None,pg_core_result_connection=None):
    from .v4_daily_pipeline_progress_r1 import instrument_progress
    progress=instrument_progress(progress)
    root=Path(root)
    if mode!='PROBE' and not capture_only:
        accepted_trade_date=_accepted_trade_date(root)
        if day<=accepted_trade_date:
            return dict(status='PUBLISHED',reason='NOOP_ALREADY_CURRENT',accepted_trade_date=accepted_trade_date,recovered_after_cas=True)
    if mode=='PROBE':
        response=tdx._request(tdx.PAGE_URL)
        try:
            page=tdx._read_bounded(response,tdx.DEFAULT_MAX_PAGE_BYTES)
            url=tdx.discover_download_url(page,tdx.validate_official_url(response.geturl()))
        finally:response.close()
        response=tdx._request(tdx.discover_update_info_url(page,url))
        try:
            info=tdx._read_bounded(response,tdx.DEFAULT_MAX_INFO_BYTES)
            provider,_=tdx.parse_update_date(info)
        finally:response.close()
        return dict(status='PROBED',target_session=day,provider_package_date=provider,
                    metadata_sha256=tdx.sha256_bytes(info),source_ready=False,
                    observed_at=datetime.now(timezone.utc).isoformat(),head_mutated=False,
                    baostock_state='NOT_QUERIED_DATE_METADATA_IS_NOT_READINESS')
    now=datetime.now(timezone.utc)
    time_check=source_readiness(day,now)
    if not time_check['time_eligible']:return time_check
    from common.paths import resolve_tdx_root, resolve_tdx_snapshot_root
    snapshot=resolve_tdx_snapshot_root(root)
    tdx_root=resolve_tdx_root(root)
    package=capture_latest_tdx_package(snapshot_root=snapshot,tdx_root=tdx_root,
                                       pg_candidate=True,target_trade_date=day,source_role='CURRENT')
    if not package.get('download'):
        return dict(status='WAIT_TDX',reason='LATEST_OFFICIAL_PACKAGE_NOT_FROZEN')
    bars=extract_target_session_bars(package,day,snapshot_root=snapshot,tdx_root=tdx_root)
    # A pre-gate package with absent target bars receives one bounded fresh
    # post-gate capture, even if CDN validators/publication text are unchanged.
    # downloaded_at tracks the full request, independently of earliest source
    # availability, so subsequent retries reuse that verified capture.
    gate=datetime.fromisoformat(day+'T18:35:00+08:00')
    checked_at=package.get('downloaded_at') or package['observed_at']
    if (bars['status']!='TARGET_BARS_EXTRACTED' and package['provider_package_date']>=day
            and datetime.fromisoformat(checked_at)<gate<=datetime.now(timezone.utc)):
        package=capture_latest_tdx_package(snapshot_root=snapshot,tdx_root=tdx_root,force_refresh=True,
                                           pg_candidate=True,target_trade_date=day,source_role='CURRENT')
        if not package.get('download'):return dict(status='WAIT_TDX',reason='POST_GATE_OFFICIAL_CAPTURE_NOT_FROZEN')
        bars=extract_target_session_bars(package,day,snapshot_root=snapshot,tdx_root=tdx_root)
    manifest_mode=_runtime_acceptance_source_mode()
    try:
        pg_runtime=_load_pg_runtime_acceptance(root,day)
    except ValueError as exc:
        if str(exc)!='BAOSTOCK_PG_RUNTIME_ACCEPTANCE_NOT_FOUND':raise
        from scripts.accept_dynamic_daily_baostock_v2 import accept_runtime
        try:
            accepted=accept_runtime(day,root)
        except (OSError,ValueError,RuntimeError) as error:
            return dict(status='WAIT_BAOSTOCK_DAILY_UPDATE',reason=str(error)[:180],
                        pg_runtime_acceptance_required=True,source_captured=False)
        if accepted['status']!='ACCEPTED':return accepted
        pg_runtime=_load_pg_runtime_acceptance(root,day)
    manifest=pg_runtime['manifest'];receipt=pg_runtime['receipt'];raw=pg_runtime['raw']
    raw_path=pg_runtime['raw_path'];immutable_manifest=pg_runtime['manifest_path']
    native_response_binding=pg_runtime['native_response_binding']
    schema=_daily_runtime_contract('BAOSTOCK_DM01_SDK_SCHEMA_ADAPTER_V2','2.0.0',version_field='version')
    normalized={}
    for name,method in [('daily',DAILY_METHOD),('adjustment_factor',FACTOR_METHOD)]:
        rows,meta=normalize_response(raw[name+'_rows'],raw[name+'_metadata'],target=day,
                                    sdk=package_metadata(),contract=schema,method=method)
        normalized[name]=dict(rows=rows,metadata=meta)
        expected=manifest['live_smoke']['daily' if name=='daily' else 'adjustment_factor']
        if _canonical_rows_digest(rows)!=expected['response_sha256']:
            raise ValueError('SOURCE_RESPONSE_RUNTIME_DIGEST_MISMATCH')
    from .tdx_local_daily_fallback_v1 import fallback
    package,bars,local_receipt=fallback(package,bars,day,normalized['daily']['rows'],snapshot_root=snapshot)
    if bars['status']!='TARGET_BARS_EXTRACTED':
        return dict(status='WAIT_TDX',reason='ACTUAL_TARGET_SESSION_NOT_IN_VERIFIED_NATIVE_SOURCES',tdx=bars['artifact'])
    from .tdx_latest_daily_source_v2 import persist_target_candidate_pg
    tdx_pg_candidate=persist_target_candidate_pg(root,package,bars)
    # The source ZIP/local snapshot are bounded SourceIngress only. Daily
    # derivation consumes the exact rowset read back from its PG fact.
    bars=dict(bars,target_bars=tdx_pg_candidate.pop('rows'),
              row_count=tdx_pg_candidate['row_count'])
    available=max(datetime.fromisoformat(raw['observed_at']),datetime.fromisoformat(bars['source_available_at'])).isoformat()
    artifact=dict(contract_id='DYNAMIC_DAILY_SOURCE_FREEZE_V1',target_session=day,
        observed_at=available,tdx_source_available_at=bars['source_available_at'],AS_RECORDED=False,PIT_ELIGIBLE=False,
        tdx=bars['artifact'],native_baostock=dict(path=raw_path.relative_to(root).as_posix(),sha256=tdx.sha256_file(raw_path)),
        runtime_manifest=dict(path=immutable_manifest.relative_to(root).as_posix(),sha256=tdx.sha256_file(immutable_manifest)),
        effective_package=package,
        tdx_target_candidate_pg=tdx_pg_candidate,
        normalized=normalized,canonical_qfq_authority='TDX_GBBQ_UNCHANGED',
        factor_role='AUDIT_FACT_NOT_CANONICAL_QFQ_AUTHORITY')
    if manifest_mode=='PG':
        bundle=pg_runtime['bundle']
        artifact['runtime_acceptance_pg']=dict(
            contract_id='V4_BAOSTOCK_RUNTIME_ACCEPTANCE_PG_R1',contract_version='1.0.0',
            trade_date=day,database_identity=bundle['database_identity'],schema=bundle['schema'],
            payload_sha256=bundle['payload_sha256'],native_response=native_response_binding)
    if raw.get('source_transport_v2'):
        artifact['source_transport_v2']=raw['source_transport_v2']
    if local_receipt:artifact.update(local_fallback=local_receipt,effective_package=package)
    digest=tdx.sha256_bytes(tdx._json_bytes(artifact));p=snapshot/'daily_freezes'/day/(digest+'.json')
    if not p.is_file():atomic_json(root,p,artifact)
    elif json.loads(p.read_bytes())!=artifact:raise ValueError('IMMUTABLE_SOURCE_FREEZE_COLLISION')
    result=dict(status='SOURCE_CAPTURED',
        source_freeze=dict(path=p.relative_to(root).as_posix(),sha256=tdx.sha256_file(p)),
        tdx_bar_count=bars['row_count'],baostock_row_count=len(normalized['daily']['rows']),
        source_captured=True,source_ready=False,derived_ready=False,published=False,last_good_preserved=True)
    # Freeze real bytes even when the previous accepted identity pool is no
    # longer the new day's universe. The gate below still controls Owner work.
    from .producer_bootstrap_v1 import optional_step
    result=dict(result,first_capture_source_candidate=optional_step(
        _capture_optional_daily_sources,root,day,result['source_freeze']))
    result,readiness=verify_source_gate(root,day,artifact,result)
    result['pg_source_ingest_candidate'] = _pg_source_ingest_plan_diagnostic(root, day, result)
    progress(day,'SOURCE_READY' if readiness['source_ready'] else readiness['status'],result)
    if not readiness['source_ready']:return dict(result,status=readiness['status'],reason=readiness['reason'])
    if capture_only:return result
    return derive_ready_sources(root,day,result,cancelled=cancelled,readback_url=readback_url,progress=progress,
                                pg_publication_context=pg_publication_context,
                                pg_core_result_connection=pg_core_result_connection)


def derive_ready_sources(root,day,result,*,cancelled=lambda:False,readback_url=None,progress=lambda *args:None,engineering_replay_current=False,candidate_only_exact=False,pg_publication_context=None,pg_core_result_connection=None):
    """Revalidate frozen bytes at the final boundary before any Owner work."""
    from .v4_daily_pipeline_progress_r1 import instrument_progress
    progress=instrument_progress(progress)
    from .r43_owner_replay import source_ingress
    root=Path(root)
    if candidate_only_exact and readback_url is not None:
        raise ValueError('EXACT_CANDIDATE_ONLY_CANNOT_PROMOTE')
    if engineering_replay_current:
        import os
        isolation_root = os.environ.get('V4_R4_ISOLATION_ROOT')
        if (readback_url is not None or os.environ.get('R4_NATIVE_ISOLATION') != '1'
                or not isolation_root
                or not root.resolve().is_relative_to(Path(isolation_root).resolve())):
            raise ValueError('ENGINEERING_REPLAY_CANNOT_PROMOTE')
    artifact=json.loads(source_ingress(root,result['source_freeze']).read_bytes())
    from .producer_bootstrap_v1 import optional_step
    if not result.get('first_capture_source_candidate',{}).get('candidate'):
        result=dict(result,first_capture_source_candidate=optional_step(
            _capture_optional_daily_sources,root,day,result['source_freeze']))
    result,readiness=verify_source_gate(root,day,artifact,result)
    result['pg_source_ingest_candidate'] = _pg_source_ingest_plan_diagnostic(root, day, result)
    if not readiness['source_ready']:
        return dict(result,status=readiness['status'],reason=readiness['reason'])
    progress(day,'DERIVING',result)
    from .operational_daily_ready_owner_v2 import build,seal
    produced,context=build(root,result['source_freeze'],source_readiness=result['source_readiness'],engineering_replay_current=engineering_replay_current,candidate_only_exact=candidate_only_exact,progress=progress)
    context['source_readiness']=result['source_readiness']
    if cancelled():return dict(result,status='CANCELLED',reason='CANCELLED_BEFORE_CAS')
    candidate,binding=seal(root,context)
    # The real sealed daily Owners feed the V4 Core result planner when an
    # independently issued PG publication/source receipt is provided. Normal
    # daily local builds remain non-persistent and report the missing authority.
    core_candidate=build_daily_core_result_candidate(root,candidate,day,pg_publication_context)
    if pg_core_result_connection is not None:
        core_candidate=persist_daily_core_result_candidate(pg_core_result_connection,core_candidate)
    result=dict(result,pg_daily_core_result_candidate=core_candidate)
    from scripts.audit_dynamic_daily_period_numbers_v1 import audit as audit_periods
    from .r43_owner_replay import ref
    period_qa=audit_periods(root,context['folder'])
    if period_qa['acceptance']!='PASS':raise ValueError('FULL_PERIOD_NUMERIC_ORACLE_FAILED')
    candidate['period_numeric_oracle']=ref(root,context['folder']/'PERIOD_NUMERIC_ORACLE.json')
    if context.get('exact_daily_policy'):
        from .operational_product_pack_v3 import prepare as prepare_product_pack
        core_replay=json.loads((context['folder']/'owner_v3/CORE_REPLAY.json').read_bytes())
        owner=next(row for row in core_replay['owners'] if row['trade_date']==day)
        pack_receipt=prepare_product_pack(root,candidate,owner)
        atomic_json(root,context['folder']/'NATIVE_PRODUCT_PACK_PREPARATION_V3.json',pack_receipt)
    candidate_path=root/binding['path'];atomic_json(root,candidate_path,candidate);binding=ref(root,candidate_path)
    from .producer_bootstrap_v1 import produce_daily_state, produce_daily_sector, optional_step
    result=dict(result,full_state_signal_candidate=optional_step(produce_daily_state,root,day,candidate),
                sector_operational_candidate=optional_step(produce_daily_sector,root,day,candidate))
    if context.get('exact_daily_policy'):
        from .producer_candidate_index_pg_v1 import build_review_and_display_candidates
    else:
        from .producer_bootstrap_v1 import build_review_and_display_candidates
    result=dict(result,producer_review_candidates=optional_step(build_review_and_display_candidates,root,day,candidate,
            result.get('first_capture_source_candidate',{}),candidate_binding=binding))
    if context.get('exact_daily_policy'):
        from workbench_db.v4_membership_reference_pg_v1 import prepare_research
        review=result.get('producer_review_candidates',{})
        index=(review.get('candidate') or {}).get('index_document')
        if not isinstance(index,dict) or index.get('contract_id')!='PRODUCER_CANDIDATE_INDEX_V2' or day not in index.get('sessions',{}):
            raise ValueError('NATIVE_RESEARCH_INDEX_PRODUCER_PG_INPUT_REQUIRED')
        reference_receipt=prepare_research(root,candidate,binding,index)
        atomic_json(root,context['folder']/'NATIVE_RESEARCH_REFERENCE_PREPARATION_V1.json',reference_receipt)
        candidate_path=context['folder']/'NATIVE_RESEARCH_SUCCESSOR_CANDIDATE.json'
        atomic_json(root,candidate_path,candidate);binding=ref(root,candidate_path)
    # Observe the exact sealed daily candidate. This never grants authority,
    # enrolls corrected events or blocks publication of otherwise usable domains.
    from .cohort_capture_readiness_r1 import inspect_daily_candidate
    capture_readiness=inspect_daily_candidate(root,candidate_binding=binding,candidate=candidate,
        trade_date=day,cutoff=datetime.now(timezone.utc).isoformat())
    result=dict(result,cohort_capture_readiness=capture_readiness)
    from workbench_db.v4_read_index_r1 import prepare_bff as prepare_read_index_r1
    from workbench_db.v4_read_index_r2 import prepare_bff as prepare_read_index_r2
    progress(day,'READ_INDEX',dict(result,processed=0,total=2,unit='versions'))
    read_index=prepare_read_index_r1(root,candidate)
    result=dict(result,read_index=read_index)
    progress(day,'READ_INDEX',dict(result,processed=1,total=2,unit='versions'))
    read_index_r2=prepare_read_index_r2(root,candidate)
    result=dict(result,read_index_r2=read_index_r2)
    # The exact PG index version bindings are part of the successor candidate;
    # persist the updated transport before the accepted-Head CAS can reference it.
    candidate_path=root/binding['path'];atomic_json(root,candidate_path,candidate);binding=ref(root,candidate_path)
    progress(day,'READ_INDEX',dict(result,processed=2,total=2,unit='versions'))
    progress(day,'DERIVED_READY',dict(result,candidate=binding,derived_ready=True,source_ready=True))
    if cancelled():return dict(result,status='CANCELLED',reason='CANCELLED_BEFORE_CAS')
    if not readback_url:return dict(result,status='QA_BLOCKED',reason='LIVE_SERVICE_READBACK_ENDPOINT_REQUIRED',candidate=binding)
    from .operational_successor_release_v1 import promote
    from .operational_daily_http_readback_v1 import readback
    progress(day,'PUBLISHING',dict(result,candidate=binding,derived_ready=True,source_ready=True))
    if cancelled():return dict(result,status='CANCELLED',reason='CANCELLED_BEFORE_CAS')
    publication=promote(root,candidate,candidate['predecessor']['sha256'],lambda c:readback(readback_url,c))
    return dict(result,**publication,source_ready=True,derived_ready=True,published=True,candidate=binding)


def build_daily_core_result_candidate(root,candidate,trade_date,publication_context=None):
    """Bind sealed V4 daily producer bytes to the Core PG result planner.

    The executor supplies no fabricated publication or source identities. A
    missing context is an explicit blocked diagnostic; with a context, the
    exact `raw`, `core`, `profile`, and `lifecycle` producer artifacts are
    digest-checked and joined by `(security_id, trade_date)` before planning.
    This function performs no database I/O.
    """
    if not isinstance(publication_context,dict):
        return {"status":"BLOCKED_PG_PUBLICATION_CONTEXT_MISSING",
                "trade_date":trade_date,"write_mode":"PLAN_ONLY_NO_DATABASE_IO",
                "persisted":False}


    try:
        from gzip import open as gzip_open
        from .r43_owner_replay import checked
        from workbench_db.v4_daily_core_result_r6 import build_daily_core_result_plan

        owner=(candidate.get("owners") or {}).get(trade_date)
        if not isinstance(owner,dict):raise ValueError("SEALED_DAILY_OWNER_MISSING")
        def rows(name):
            binding=owner.get(name)
            if not isinstance(binding,dict):raise ValueError("SEALED_OWNER_BINDING_MISSING:"+name)
            path=checked(root,binding)
            if path.name.endswith(".gz"):
                with gzip_open(path,"rt",encoding="utf-8") as stream:return [json.loads(line) for line in stream]
            value=json.loads(path.read_bytes())
            return value.get("rows",value if isinstance(value,list) else [value])
        raw_rows=rows("raw");core_rows=rows("core");profile_rows=rows("profile");lifecycle_rows=rows("lifecycle")
        maps={name:{str(row.get("security_id")):row for row in values
                    if row.get("trade_date",trade_date)==trade_date}
               for name,values in (("raw",raw_rows),("core",core_rows),
                                   ("profile",profile_rows),("lifecycle",lifecycle_rows))}
        if any(len(maps[name])!=len(values) for name,values in (("raw",raw_rows),("core",core_rows),
                                                                 ("profile",profile_rows),("lifecycle",lifecycle_rows))):
            raise ValueError("SEALED_DAILY_OWNER_DUPLICATE_OR_T0_MISMATCH")
        if set(maps["core"]) != set(maps["lifecycle"]) or set(maps["profile"]) != set(maps["lifecycle"]):
            raise ValueError("SEALED_DAILY_OWNER_SECURITY_ID_SET_MISMATCH")
        receipt=publication_context.get("producer_receipt")
        bindings=(receipt or {}).get("source_artifact_bindings") if isinstance(receipt,dict) else None
        tdx_ids=sorted({item.get("source_revision_id") for item in bindings or []
                        if item.get("source_key")=="tdx" and item.get("target_trade_date")==trade_date})
        by_security=publication_context.get("source_revision_by_security") or {}
        if not tdx_ids and not by_security:raise ValueError("ACCEPTED_TDX_SOURCE_REVISION_REQUIRED")
        security_types=publication_context.get("security_type_by_security") or {}
        projected=[]
        for security_id in sorted(maps["core"]):
            core=maps["core"][security_id];life=maps["lifecycle"][security_id]
            raw=maps["raw"].get(security_id);profile=maps["profile"][security_id]
            if core.get("trade_date")!=trade_date or life.get("trade_date",trade_date)!=trade_date:
                raise ValueError("SEALED_DAILY_OWNER_T0_MISMATCH")
            status=life.get("status")
            trade_status={"ACTUAL_TRADED":"TRADING","TRADING":"TRADING",
                          "SUSPENDED":"SUSPENDED","DELISTED":"DELISTED"}.get(status,"UNKNOWN")
            fields=core.get("fields") if isinstance(core.get("fields"),dict) else {}
            def observed(name):
                item=fields.get(name)
                if not isinstance(item,dict) or item.get("quality_state")!="OBSERVED":return None
                return item.get("value")
            ma60=fields.get("ma60") if isinstance(fields.get("ma60"),dict) else None
            history_status=("SUFFICIENT" if ma60 and ma60.get("quality_state")=="OBSERVED"
                            and int(ma60.get("actual_count") or 0)>=60 else
                            "INSUFFICIENT_NEW_LISTING_HISTORY" if ma60 else "HISTORY_UNKNOWN")
            source_revision=by_security.get(security_id)
            if source_revision is None and len(tdx_ids)==1:source_revision=tdx_ids[0]
            if not source_revision:raise ValueError("CORE_ROW_SOURCE_REVISION_UNBOUND:"+security_id)
            projected.append({
                "trade_date":trade_date,"security_id":security_id,
                "security_type":security_types.get(security_id,"UNKNOWN"),
                "trade_status":trade_status,
                **({key:raw.get(key) for key in ("open","high","low","close","volume","amount")} if raw else
                   {key:None for key in ("open","high","low","close","volume","amount")}),
                "turnover_rate":None,"turnover_status":"TURNOVER_UNAVAILABLE",
                "ma5":observed("ma5"),"ma20":observed("ma20"),"ma60":observed("ma60"),
                "history_status":history_status,"price_basis":"TDX_GBBQ_UNCHANGED",
                "source_revision_id":source_revision,
                "profile_payload":{"core_fields":fields,"profile_owner":profile},
                "quality_status":"ACTUAL_OPERATIONAL_DAILY_OWNER_V1",
            })
        plan=build_daily_core_result_plan(
            publication_id=publication_context.get("publication_id"),
            publication_revision=publication_context.get("publication_revision"),
            trade_date=trade_date,
            source_manifest_sha256=publication_context.get("source_manifest_sha256"),
            producer_contract_id=publication_context.get("producer_contract_id"),
            producer_sha256=publication_context.get("producer_sha256"),
            producer_receipt=receipt,rows=projected,
            completeness_contract=publication_context.get("completeness_contract"),
        )
        return {"status":"PLAN_READY_NOT_PERSISTED","trade_date":trade_date,
                "result_identity":plan["result_identity"],"result_sha256":plan["result_sha256"],
                "row_count":plan["row_count"],"write_mode":plan["write_mode"],
                "persisted":False,"plan":plan}
    except Exception as exc:
        return {"status":"BLOCKED_PRODUCER_OR_SOURCE_BINDING",
                "trade_date":trade_date,"reason":str(exc),
                "write_mode":"PLAN_ONLY_NO_DATABASE_IO","persisted":False}


def persist_daily_core_result_candidate(pg, candidate):
    """Opt-in bridge from sealed producer plan to the controlled caller transaction.

    No connection is opened and no commit is issued here. Supplying ``pg`` is
    an explicit write-path selection; the writer still validates the configured
    V4 writer role, candidate publication, source package proofs, and PIT clocks.
    """
    if not isinstance(candidate,dict) or candidate.get("status")!="PLAN_READY_NOT_PERSISTED":
        raise ValueError("PG_CORE_RESULT_PLAN_NOT_READY")
    plan=candidate.get("plan")
    if not isinstance(plan,dict):raise ValueError("PG_CORE_RESULT_PLAN_MISSING")
    from workbench_db.v4_daily_core_result_r6 import persist_daily_core_result
    receipt=persist_daily_core_result(pg,plan)
    return {**candidate,"status":"PG_CANDIDATE_RESULT_INSERTED_NOT_ACCEPTED",
            "write_mode":"CALLER_TRANSACTION_NO_COMMIT","persisted":True,
            "pg_write_receipt":receipt}


def verify_source_gate(root,day,artifact,result,now=None):
    """Single audited gate shared by execution and isolated receipt replay."""
    root=Path(root)
    from .r43_owner_replay import source_ingress
    def pg_source(binding):
        relative=Path(binding['path'])
        if relative.is_absolute():relative=relative.resolve().relative_to(root.resolve())
        return source_ingress(root,dict(binding,path=relative.as_posix()))
    freeze_binding=result.get('source_freeze')
    if isinstance(freeze_binding,dict):
        frozen=json.loads(pg_source(freeze_binding).read_bytes())
        if frozen!=artifact:raise ValueError('SOURCE_FREEZE_PG_READBACK_MISMATCH')
    raw_path=pg_source(artifact['native_baostock'])
    if tdx.sha256_file(raw_path)!=artifact['native_baostock']['sha256']:raise ValueError('NATIVE_RESPONSE_DIGEST_MISMATCH')
    raw=json.loads(raw_path.read_bytes());normalized=artifact['normalized'];package=artifact['effective_package']
    bars=dict(artifact=artifact['tdx'],source_available_at=artifact.get('tdx_source_available_at',artifact['observed_at']))
    snapshot=root/'data/v4/dynamic_daily_sources'
    observed=raw['observed_at'];daily=normalized['daily']['rows'];factors=normalized['adjustment_factor']['rows']
    native_path=pg_source(bars['artifact'])
    if tdx.sha256_file(native_path)!=bars['artifact']['sha256']:raise ValueError('NATIVE_TARGET_DIGEST_MISMATCH')
    native_document=json.loads(native_path.read_bytes());native=native_document['target_bars']
    bycode={r['source_security_key'].upper():r for r in native}
    codes=[r['code'].upper() for r in daily]
    scoped_reconciliation=None
    reconciled=bool(codes) and len(codes)==len(set(codes)) and len(bycode)==len(native)
    active_codes={r['code'].upper() for r in daily if r.get('tradestatus')=='1'}
    if set(bycode)!=active_codes:reconciled=False
    for row in daily:
        bar=bycode.get(row['code'].upper())
        if row['date']!=day or row['tradestatus'] not in {'0','1'}:reconciled=False
        try:
            if row['tradestatus']=='1' and (not bar or any(float(row[f])!=float(bar[f]) for f in ('open','high','low','close','volume'))):reconciled=False
        except (KeyError,TypeError,ValueError,OverflowError):
            # The versioned per-code gate below records and quarantines this
            # object; malformed numeric input must not bypass that diagnostic.
            reconciled=False
        if row['tradestatus']=='0' and bar:reconciled=False
    sources={}
    for name,rows in [('baostock_daily',daily),('baostock_factor',factors)]:
        sources[name]=dict(status='VERIFIED',target_session=day,provider_date=day,
            source_sha256=_canonical_rows_digest(rows),observed_at=observed,
            row_count=len(rows),identity_reconciliation_passed=reconciled,
            provider='BaoStock',artifact_family=name,capture_method='ACCEPTED_NATIVE_RESPONSE',
            evidence_path=raw_path.relative_to(root).as_posix(),captured_at=observed,
            verified_at=datetime.now(timezone.utc).isoformat())
        sources[name]['provider_observed_at']=observed
    factor_proved=(raw.get('target_date')==day and 'adjustment_factor_rows' in raw
        and raw.get('adjustment_factor_metadata',{}).get('error_code')=='0'
        and all(r.get('dividOperateDate')==day for r in factors)
        and bool(raw['adjustment_factor_rows'])==bool(factors))
    if not factor_proved:sources['baostock_factor']['status']='UNVERIFIED'
    if not factors:
        sources['baostock_factor'].update(verified_no_change=factor_proved,proof_target_session=day,
            no_change_proof_sha256=tdx.sha256_file(raw_path))
    sources['tdx']=dict(status='VERIFIED',target_session=day,
        source_sha256=bars['artifact']['sha256'],observed_at=bars['source_available_at'],
        bars_date_coverage=sorted({r.get('trade_date') for r in native if r.get('trade_date')}),row_count=len(native),provider='TDX',
        artifact_family='NATIVE_DAILY',capture_method='VERIFIED_TARGET_EXTRACTION',
        provider_package_date=package['provider_package_date'],package=package.get('download'),
        evidence_path=bars['artifact']['path'],captured_at=bars['source_available_at'],
        verified_at=datetime.now(timezone.utc).isoformat())
    sources['tdx']['provider_observed_at']=package.get('observed_at',bars['source_available_at'])
    if any(r.get('trade_date')!=day for r in native):sources['tdx']['status']='UNVERIFIED'
    dependencies={}
    identity_preflight=None
    from workbench_db.v4_operational_live_head_pg_r1 import read_current
    head=read_current(root)['candidate']
    from .r43_owner_replay import ref
    from .r43_operational_sources import date_valid_identity
    from workbench_db.v4_operational_owner_authority_v2 import load as load_owner,read as read_owner
    from workbench_db.v4_membership_reference_pg_v1 import identity_source,read_identity
    owner_authority=load_owner(root,head)
    life_binding=head['owners'][head['accepted_trade_date']]['lifecycle']
    life=read_owner(root,owner_authority,head['accepted_trade_date'],'lifecycle',life_binding)
    identity_binding=identity_source(root,head)
    identity=read_identity(root,head)
    expected_codes={r['source_security_key'].upper() for r in identity if r.get('board_scope') in {'SH_MAIN','SZ_MAIN','CHINEXT','STAR'} and date_valid_identity(r,day)}
    actual_codes={code for code in codes if code.startswith(('SH.','SZ.'))}
    from .operational_new_listing_r1 import classify_codes
    code_changes=classify_codes(expected_codes,daily,native,day)
    from .native_source_reconciliation_r3 import reconcile
    policy_path=root/'config/tdx_a_stock_delta_scope_policy_v2.json'
    scoped_reconciliation=reconcile(native,daily,expected_codes,json.loads(policy_path.read_bytes()),day)
    scoped_reconciliation['scope_policy']=ref(root,policy_path)
    scoped_reconciliation['dated_identity']=life['identity']
    # Provider arithmetic agreement and canonical identity admission are
    # distinct gates. A correctly reconciled new/delisted roster still waits
    # for dated identity authority below; it is not a bad price source.
    provider_reconciliation=reconcile(native,daily,actual_codes,json.loads(policy_path.read_bytes()),day)
    reconciled=provider_reconciliation['status']=='SCOPED_REQUIRED_PROVIDER_FACTS_RECONCILED'
    scoped_reconciliation['provider_facts']=provider_reconciliation
    for family in ('baostock_daily','baostock_factor'):
        sources[family]['identity_reconciliation_passed']=reconciled
        sources[family]['scope_reconciliation']=scoped_reconciliation
    # Provider validation and the protected old identity gate are separate.
    # A new roster never obtains authority merely by matching native bars.
    scope_matches=actual_codes==expected_codes
    sources['dated_identity_authority']=dict(
        contract_id='DATED_IDENTITY_GATE_REASON_R2',target_session=day,
        status='PREVIOUS_HEAD_IDENTITY_SCOPE_MATCH' if scope_matches else 'WAIT_DATED_IDENTITY_AUTHORITY',
        scope_matches=scope_matches,expected_codes=sorted(expected_codes),actual_codes=sorted(actual_codes),
        new_identity_admitted=False,provider_status='NATIVE_PROVIDERS_RECONCILED' if reconciled else 'NATIVE_PROVIDER_RECONCILIATION_FAILED')
    gbbq=_tdx_gbbq_source_path(root)
    before=gbbq.stat();gbbq_sha=tdx.sha256_file(gbbq);after=gbbq.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('GBBQ_CHANGED_DURING_READINESS')
    parent_binding='pg://v4/operational_research_heads/current'
    dependencies=dict(parent_head=parent_binding,lifecycle=life_binding,identity=identity_binding,
        accepted_pool_sha256=tdx.sha256_bytes(tdx._json_bytes(sorted(expected_codes))),
        accepted_pool_count=len(expected_codes),missing_codes=sorted(expected_codes-actual_codes),unknown_codes=sorted(actual_codes-expected_codes),
        code_changes=code_changes,new_codes=code_changes['new_codes'],absent_codes=code_changes['absent_codes'],invalid_codes=code_changes['invalid_codes'],active_universe=code_changes['valid_codes'],
        gbbq=dict(path=str(gbbq),sha256=gbbq_sha,bytes=before.st_size),membership_snapshot=head['membership_snapshot'])
    from .next_t0_identity_preflight_v1 import diagnose
    transport=raw.get('source_transport_v2',{})
    identity_preflight=diagnose(trade_date=day,previous_date=head['accepted_trade_date'],
        expected_codes=expected_codes,actual_codes=actual_codes,
        source_binding=artifact['native_baostock'],parent_head=parent_binding,
        identity_binding=identity_binding,membership_binding=head['membership_snapshot'],
        native_reconciled=reconciled,
        requested_at=raw.get('requested_at') or transport.get('requested_at') or transport.get('daily',{}).get('requested_at'),
        received_at=raw.get('received_at') or transport.get('daily',{}).get('received_at') or observed,
        first_available_at=observed)
    # Dependency revisions belong to the source gate identity, so a changed
    # pool or action source cannot borrow a previously ready revision.
    sources['baostock_daily']['dependency_bindings']=dependencies
    readiness=source_readiness(day,now or datetime.now(timezone.utc),sources)
    readiness.update(source_freeze=result['source_freeze'],dependency_bindings=dependencies,AS_RECORDED=False,PIT_ELIGIBLE=False)
    readiness['native_provider_facts']=dict(
        status='NATIVE_PROVIDERS_RECONCILED' if reconciled else 'NATIVE_PROVIDER_RECONCILIATION_FAILED',
        original_baostock=artifact['native_baostock'],original_tdx=bars['artifact'],
        target_session=day,native_codes=sorted(bycode),baostock_codes=sorted(set(codes)))
    if scoped_reconciliation is not None:
        readiness['native_provider_facts'].update(
            reconciliation_scope=scoped_reconciliation,
            full_market_coverage_pass=False,
            current_contract_scope_pass=scoped_reconciliation['status']=='SCOPED_REQUIRED_PROVIDER_FACTS_RECONCILED')
    if identity_preflight:readiness['old_head_identity_preflight']=identity_preflight
    # Equal payloads at distinct immutable locations must not borrow a gate
    # whose exact source binding names another artifact.
    revision=readiness_binding_revision(readiness.get('source_revision_id'),result['source_freeze'],dependencies)
    ready_path=snapshot/'source_readiness'/day/(revision+'.json')
    if not ready_path.is_file():atomic_json(root,ready_path,readiness)
    result.update(source_readiness=dict(path=ready_path.relative_to(root).as_posix(),sha256=tdx.sha256_file(ready_path)),
                  source_ready=readiness['source_ready'])
    return result,readiness
