"""Real bounded source stages; no fabricated successor Owner or publication."""
from pathlib import Path
from datetime import datetime,timezone
import json
from . import tdx_official_daily_source as tdx
from .tdx_latest_daily_source_v2 import capture_latest_tdx_package,extract_target_session_bars
from .operational_daily_storage_v1 import output_path,atomic_json
from .operational_runtime_acceptance_v2 import load as load_runtime_acceptance_manifest,error as runtime_acceptance_error
from .baostock_supplemental import package_metadata
from .baostock_dm01_sdk_schema_v2 import normalize_response
from .baostock_daily_update_source import DAILY_METHOD,FACTOR_METHOD,_canonical_rows_digest
from .source_readiness_v2 import source_readiness


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


def execute_sources(root,day,mode,*,capture_only=False,cancelled=lambda:False,readback_url=None,progress=lambda *args:None):
    root=Path(root)
    if mode!='PROBE' and not capture_only:
        head=json.loads((root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
        if day<=head['accepted_trade_date']:
            return dict(status='PUBLISHED',reason='NOOP_ALREADY_CURRENT',accepted_trade_date=head['accepted_trade_date'],recovered_after_cas=True)
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
    snapshot=output_path(root,root/'data/v4/dynamic_daily_sources')
    package=capture_latest_tdx_package(snapshot_root=snapshot)
    if not package.get('download'):
        return dict(status='WAIT_TDX',reason='LATEST_OFFICIAL_PACKAGE_NOT_FROZEN')
    bars=extract_target_session_bars(package,day,snapshot_root=snapshot)
    # A pre-gate package with absent target bars receives one bounded fresh
    # post-gate capture, even if CDN validators/publication text are unchanged.
    # downloaded_at tracks the full request, independently of earliest source
    # availability, so subsequent retries reuse that verified capture.
    gate=datetime.fromisoformat(day+'T18:35:00+08:00')
    checked_at=package.get('downloaded_at') or package['observed_at']
    if (bars['status']!='TARGET_BARS_EXTRACTED' and package['provider_package_date']>=day
            and datetime.fromisoformat(checked_at)<gate<=datetime.now(timezone.utc)):
        package=capture_latest_tdx_package(snapshot_root=snapshot,force_refresh=True)
        if not package.get('download'):return dict(status='WAIT_TDX',reason='POST_GATE_OFFICIAL_CAPTURE_NOT_FROZEN')
        bars=extract_target_session_bars(package,day,snapshot_root=snapshot)
    manifest_path=root/'reports/v4_baostock/runtime_acceptance'/day.replace('-','')/'accepted_runtime_manifest.json'
    try:
        manifest=load_runtime_acceptance_manifest(manifest_path,project_root=root)
        if manifest['live_smoke']['target_date']!=day:raise ValueError('EXACT_TARGET_RUNTIME_REQUIRED')
        if runtime_acceptance_error(manifest,sdk=package_metadata(),auth_mode=manifest['auth_mode']):
            raise ValueError('SDK_RUNTIME_CHANGED')
    except (OSError,ValueError,KeyError):
        from scripts.accept_dynamic_daily_baostock_v2 import accept_runtime
        accepted=accept_runtime(day,root)
        if accepted['status']!='ACCEPTED':return accepted
        manifest=load_runtime_acceptance_manifest(manifest_path,project_root=root)
    smoke=root/manifest['smoke_receipt']['path']
    # The accepted smoke already captured both real full-market batch responses.
    # Reuse them by their live receipt rather than issuing two more full queries.
    raw_path=smoke.with_name(smoke.name.replace('_live_smoke_receipt.json','_raw_responses.json'))
    raw=json.loads(raw_path.read_bytes())
    immutable_manifest=smoke.with_name(smoke.name.replace('_live_smoke_receipt.json','_accepted_runtime_manifest.json'))
    if not immutable_manifest.is_file() or immutable_manifest.read_bytes()!=manifest_path.read_bytes():
        raise ValueError('IMMUTABLE_RUNTIME_MANIFEST_REQUIRED')
    receipt=json.loads(smoke.read_bytes())
    if raw['target_date']!=day or raw['observed_at']!=receipt['observed_at']:
        raise ValueError('NATIVE_RESPONSE_OBSERVATION_MISMATCH')
    if receipt.get('native_response') and tdx.sha256_file(raw_path)!=receipt['native_response']['sha256']:
        raise ValueError('NATIVE_RESPONSE_DIGEST_MISMATCH')
    schema=json.loads((root/'config/baostock_dm01_sdk_schema_adapter_v2.json').read_bytes())
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
    available=max(datetime.fromisoformat(raw['observed_at']),datetime.fromisoformat(bars['source_available_at'])).isoformat()
    artifact=dict(contract_id='DYNAMIC_DAILY_SOURCE_FREEZE_V1',target_session=day,
        observed_at=available,tdx_source_available_at=bars['source_available_at'],AS_RECORDED=False,PIT_ELIGIBLE=False,
        tdx=bars['artifact'],native_baostock=dict(path=raw_path.relative_to(root).as_posix(),sha256=tdx.sha256_file(raw_path)),
        runtime_manifest=dict(path=immutable_manifest.relative_to(root).as_posix(),sha256=tdx.sha256_file(immutable_manifest)),
        effective_package=package,
        normalized=normalized,canonical_qfq_authority='TDX_GBBQ_UNCHANGED',
        factor_role='AUDIT_FACT_NOT_CANONICAL_QFQ_AUTHORITY')
    if local_receipt:artifact.update(local_fallback=local_receipt,effective_package=package)
    digest=tdx.sha256_bytes(tdx._json_bytes(artifact));p=snapshot/'daily_freezes'/day/(digest+'.json')
    if not p.is_file():atomic_json(root,p,artifact)
    elif json.loads(p.read_bytes())!=artifact:raise ValueError('IMMUTABLE_SOURCE_FREEZE_COLLISION')
    result=dict(status='SOURCE_CAPTURED',
        source_freeze=dict(path=p.relative_to(root).as_posix(),sha256=tdx.sha256_file(p)),
        tdx_bar_count=bars['row_count'],baostock_row_count=len(normalized['daily']['rows']),
        source_captured=True,source_ready=False,derived_ready=False,published=False,last_good_preserved=True)
    result,readiness=verify_source_gate(root,day,artifact,result)
    progress(day,'SOURCE_READY' if readiness['source_ready'] else readiness['status'],result)
    if not readiness['source_ready']:return dict(result,status=readiness['status'],reason=readiness['reason'])
    if capture_only:return result
    progress(day,'DERIVING',result)
    from .operational_daily_ready_owner_v2 import build,seal
    produced,context=build(root,result['source_freeze'],source_readiness=result['source_readiness'])
    context['source_readiness']=result['source_readiness']
    if cancelled():return dict(result,status='CANCELLED',reason='CANCELLED_BEFORE_CAS')
    candidate,binding=seal(root,context)
    from scripts.audit_dynamic_daily_period_numbers_v1 import audit as audit_periods
    from .r43_owner_replay import ref
    period_qa=audit_periods(root,context['folder'])
    if period_qa['acceptance']!='PASS':raise ValueError('FULL_PERIOD_NUMERIC_ORACLE_FAILED')
    candidate['period_numeric_oracle']=ref(root,context['folder']/'PERIOD_NUMERIC_ORACLE.json')
    candidate_path=root/binding['path'];atomic_json(root,candidate_path,candidate);binding=ref(root,candidate_path)
    progress(day,'DERIVED_READY',dict(result,candidate=binding,derived_ready=True,source_ready=True))
    if cancelled():return dict(result,status='CANCELLED',reason='CANCELLED_BEFORE_CAS')
    if not readback_url:return dict(result,status='QA_BLOCKED',reason='LIVE_SERVICE_READBACK_ENDPOINT_REQUIRED',candidate=binding)
    from .operational_successor_release_v1 import promote
    from .operational_daily_http_readback_v1 import readback
    progress(day,'PUBLISHING',dict(result,candidate=binding,derived_ready=True,source_ready=True))
    publication=promote(root,candidate,candidate['predecessor']['sha256'],lambda c:readback(readback_url,c))
    return dict(result,**publication,source_ready=True,derived_ready=True,published=True,candidate=binding)


def verify_source_gate(root,day,artifact,result,now=None):
    """Single audited gate shared by execution and isolated receipt replay."""
    root=Path(root)
    raw_path=root/artifact['native_baostock']['path']
    if tdx.sha256_file(raw_path)!=artifact['native_baostock']['sha256']:raise ValueError('NATIVE_RESPONSE_DIGEST_MISMATCH')
    raw=json.loads(raw_path.read_bytes());normalized=artifact['normalized'];package=artifact['effective_package']
    bars=dict(artifact=artifact['tdx'],source_available_at=artifact.get('tdx_source_available_at',artifact['observed_at']))
    snapshot=root/'data/v4/dynamic_daily_sources'
    observed=raw['observed_at'];daily=normalized['daily']['rows'];factors=normalized['adjustment_factor']['rows']
    native_path=Path(bars['artifact']['path'])
    if not native_path.is_absolute():native_path=root/native_path
    if tdx.sha256_file(native_path)!=bars['artifact']['sha256']:raise ValueError('NATIVE_TARGET_DIGEST_MISMATCH')
    native_document=json.loads(native_path.read_bytes());native=native_document['target_bars']
    bycode={r['source_security_key'].upper():r for r in native}
    codes=[r['code'].upper() for r in daily]
    reconciled=bool(codes) and len(codes)==len(set(codes)) and len(bycode)==len(native)
    for row in daily:
        bar=bycode.get(row['code'].upper())
        if row['date']!=day or row['tradestatus'] not in {'0','1'}:reconciled=False
        if row['tradestatus']=='1' and (not bar or any(float(row[f])!=float(bar[f]) for f in ('open','high','low','close','volume'))):reconciled=False
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
    head_path=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    if head_path.is_file():
        from .r43_owner_replay import checked,ref
        from .r43_operational_sources import date_valid_identity
        head=json.loads(head_path.read_bytes())
        life_binding=head['owners'][head['accepted_trade_date']]['lifecycle']
        life=json.loads(checked(root,life_binding).read_bytes())
        identity=json.loads(checked(root,life['identity']).read_bytes())['rows']
        expected_codes={r['source_security_key'].upper() for r in identity if r.get('board_scope') in {'SH_MAIN','SZ_MAIN','CHINEXT','STAR'} and date_valid_identity(r,day)}
        actual_codes={code for code in codes if code.startswith(('SH.','SZ.'))}
        if actual_codes!=expected_codes:sources['baostock_daily']['status']='UNVERIFIED'
        gbbq=Path('D:/new_tdx/T0002/hq_cache/gbbq')
        before=gbbq.stat();gbbq_sha=tdx.sha256_file(gbbq);after=gbbq.stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('GBBQ_CHANGED_DURING_READINESS')
        dependencies=dict(parent_head=ref(root,head_path),lifecycle=life_binding,identity=life['identity'],
            accepted_pool_sha256=tdx.sha256_bytes(tdx._json_bytes(sorted(expected_codes))),
            accepted_pool_count=len(expected_codes),missing_codes=sorted(expected_codes-actual_codes),unknown_codes=sorted(actual_codes-expected_codes),
            gbbq=dict(path=str(gbbq),sha256=gbbq_sha,bytes=before.st_size),membership_snapshot=head['membership_snapshot'])
        # Dependency revisions belong to the source gate identity, so a changed
        # pool or action source cannot borrow a previously ready revision.
        sources['baostock_daily']['dependency_bindings']=dependencies
    readiness=source_readiness(day,now or datetime.now(timezone.utc),sources)
    readiness.update(source_freeze=result['source_freeze'],dependency_bindings=dependencies,AS_RECORDED=False,PIT_ELIGIBLE=False)
    revision=readiness.get('source_revision_id') or tdx.sha256_bytes(tdx._json_bytes(readiness))
    ready_path=snapshot/'source_readiness'/day/(revision+'.json')
    if not ready_path.is_file():atomic_json(root,ready_path,readiness)
    result.update(source_readiness=dict(path=ready_path.relative_to(root).as_posix(),sha256=tdx.sha256_file(ready_path)),
                  source_ready=readiness['source_ready'])
    return result,readiness
