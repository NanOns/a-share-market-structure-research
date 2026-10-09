"""Real bounded source stages; no fabricated successor Owner or publication."""
from pathlib import Path
from datetime import datetime,timezone
import json
from . import tdx_official_daily_source as tdx
from .tdx_latest_daily_source_v2 import capture_latest_tdx_package,extract_target_session_bars
from .operational_daily_storage_v1 import output_path,atomic_json
from .baostock_runtime_acceptance import load_runtime_acceptance_manifest,runtime_acceptance_error
from .baostock_supplemental import package_metadata
from .baostock_dm01_sdk_schema_v2 import normalize_response
from .baostock_daily_update_source import DAILY_METHOD,FACTOR_METHOD,_canonical_rows_digest


def execute_sources(root,day,mode):
    root=Path(root)
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
    snapshot=output_path(root,root/'data/v4/dynamic_daily_sources')
    package=capture_latest_tdx_package(snapshot_root=snapshot)
    if not package.get('download'):
        return dict(status='WAIT_TDX',reason='LATEST_OFFICIAL_PACKAGE_NOT_FROZEN')
    bars=extract_target_session_bars(package,day,snapshot_root=snapshot)
    if bars['status']!='TARGET_BARS_EXTRACTED':
        return dict(status='WAIT_TDX',reason='ACTUAL_TARGET_SESSION_NOT_IN_LATEST_PACKAGE',tdx=bars['artifact'])
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
    artifact=dict(contract_id='DYNAMIC_DAILY_SOURCE_FREEZE_V1',target_session=day,
        observed_at=raw['observed_at'],AS_RECORDED=False,PIT_ELIGIBLE=False,
        tdx=bars['artifact'],native_baostock=dict(path=raw_path.relative_to(root).as_posix(),sha256=tdx.sha256_file(raw_path)),
        runtime_manifest=dict(path=manifest_path.relative_to(root).as_posix(),sha256=tdx.sha256_file(manifest_path)),
        normalized=normalized,canonical_qfq_authority='TDX_GBBQ_UNCHANGED',
        factor_role='AUDIT_FACT_NOT_CANONICAL_QFQ_AUTHORITY')
    digest=tdx.sha256_bytes(tdx._json_bytes(artifact));p=snapshot/'daily_freezes'/day/(digest+'.json')
    if not p.is_file():atomic_json(root,p,artifact)
    return dict(status='QA_BLOCKED',reason='DATED_IDENTITY_LIFECYCLE_GBBQ_AND_SUCCESSOR_OWNER_CHAIN_NOT_ADMITTED',
        source_freeze=dict(path=p.relative_to(root).as_posix(),sha256=tdx.sha256_file(p)),
        tdx_bar_count=bars['row_count'],baostock_row_count=len(normalized['daily']['rows']),
        source_captured=True,source_ready=False,derived_ready=False,published=False,last_good_preserved=True)
