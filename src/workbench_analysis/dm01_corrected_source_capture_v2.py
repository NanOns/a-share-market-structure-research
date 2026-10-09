"""Bounded DM01 retrospective source capability, separate from same-day PIT seal."""
from datetime import datetime, timezone
from pathlib import Path
import json
from .baostock_supplemental import BaoStockClient, RequestBudget, package_metadata
from .baostock_daily_update_source import (capture_baostock_daily_update, DAILY_METHOD, FACTOR_METHOD,
    _validate_daily_rows, _validate_factor_rows, _canonical_rows_digest)
from .baostock_runtime_acceptance import build_runtime_acceptance_manifest, canonical_sha256
from .tdx_official_daily_source import _atomic_write
from .market_source_acquisition import official_sessions


def write(path, payload):
    _atomic_write(path,(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode(),tdx_root=Path('D:/new_tdx'))


def normalize_factor_schema(rows):
    result=[]
    for row in rows:
        normalized=dict(row)
        if 'adjustFactor' not in normalized and 'adjustFacto' in normalized:
            normalized['adjustFactor']=normalized.pop('adjustFacto')
        elif 'adjustFacto' in normalized:
            if normalized['adjustFactor']!=normalized['adjustFacto']:
                raise ValueError('FACTOR_ALIAS_CONFLICT')
            normalized.pop('adjustFacto')
        result.append(normalized)
    return result


class CorrectedFactorSchemaClient:
    """Versioned spelling adapter; native response retained separately."""
    def __init__(self, client, output):self.client=client;self.output=output
    def __getattr__(self,name):return getattr(self.client,name)
    def query_rows(self, operation, method, **params):
        rows,meta=self.client.query_rows(operation,method,**params)
        if method==DAILY_METHOD:
            write(self.output/'CAPTURE_NATIVE_DAILY_RESPONSE.json',dict(rows=rows,metadata=meta,params=params))
            meta=dated_daily_metadata(rows,meta,params['date'])
        if method==FACTOR_METHOD:
            write(self.output/'CAPTURE_NATIVE_FACTOR_RESPONSE.json',dict(rows=rows,metadata=meta,params=params))
            rows=normalize_factor_schema(rows)
            meta=dict(meta,fields=['adjustFactor' if f=='adjustFacto' else f for f in meta.get('fields',[])],
                schema_adapter='DM01_CORRECTED_FACTOR_FIELD_ALIAS_V2',native_factor_response='CAPTURE_NATIVE_FACTOR_RESPONSE.json')
        return rows,meta


def dated_daily_metadata(rows, meta, target):
    dates={r.get('date') for r in rows}
    if dates!={target}:raise ValueError('DAILY_RESPONSE_DATE_MISMATCH')
    if meta.get('provider_date') not in (None,target):raise ValueError('DAILY_METADATA_DATE_CONFLICT')
    return dict(meta,provider_date=target,provider_date_evidence='ALL_RESPONSE_ROW_DATES_VERIFIED',
                sdk_result_date=meta.get('provider_date'))


def corrected_baostock_capture(root, target_date, output):
    root=Path(root).resolve();output=Path(output).resolve()
    if target_date not in official_sessions(root):raise ValueError('OFFICIAL_SESSION_NOT_VERIFIED')
    from zoneinfo import ZoneInfo
    local=datetime.now(ZoneInfo('Asia/Shanghai'))
    if target_date>local.date().isoformat() or (target_date==local.date().isoformat() and local.hour<15):
        raise ValueError('WAIT_MARKET_CLOSE')
    ledger=root/'reports/v4_baostock/request_ledger.json'
    budget=RequestBudget(ledger)
    def count():
        return sum(r['count'] for r in json.loads(ledger.read_bytes()).get('by_shanghai_date',{}).values()) if ledger.exists() else 0
    before=count(); observed=datetime.now(timezone.utc).isoformat()
    receipt=dict(contract_id='DM01_CORRECTED_BAOSTOCK_SOURCE_CAPABILITY_V2',target_date=target_date,
        observed_at=observed,AS_RECORDED=False,knowledge_lineage='RECONSTRUCTED_CORRECTED',
        production_permission=False,requests=[],status='IN_PROGRESS')
    try:
        with BaoStockClient(budget,auth_mode='PUBLIC_ANONYMOUS',allow_unaccepted_runtime_smoke=True) as client:
            receipt['endpoint']=client.runtime_endpoint
            daily,dm=client.query_rows('dm01_corrected_runtime_daily',DAILY_METHOD,date=target_date,max_rows=20000,max_pages=1)
            receipt['requests'].append(dict(method=DAILY_METHOD,params=dict(date=target_date),metadata=dm,rows=daily))
            write(output/'CORRECTED_BAOSTOCK_CAPABILITY_RECEIPT.json',receipt)
            factors,fm=client.query_rows('dm01_corrected_runtime_factors',FACTOR_METHOD,date=target_date,max_rows=20000,max_pages=1)
            receipt['requests'].append(dict(method=FACTOR_METHOD,params=dict(date=target_date),metadata=fm,rows=factors))
            _validate_daily_rows(daily,target_date);_validate_factor_rows(normalize_factor_schema(factors),target_date)
            if not daily:raise ValueError('PROVIDER_EMPTY_DAILY_CONFIRMED')
            def record(method,rows,meta):
                if meta.get('provider_date')!=target_date:raise ValueError('PROVIDER_DATE_MISMATCH')
                return dict(method=method,provider_date=target_date,row_count=len(rows),fields=meta.get('fields'),
                    response_sha256=_canonical_rows_digest(rows),page_count=meta.get('page_count'),error_code=meta.get('error_code'))
            smoke=dict(status='PASS',target_date=target_date,auth_mode=client.auth_mode,endpoint=client.runtime_endpoint,
                daily=record(DAILY_METHOD,daily,dated_daily_metadata(daily,dm,target_date)),adjustment_factor=record(FACTOR_METHOD,factors,fm))
            receipt.update(status='PASS_CORRECTED_READ_CAPABILITY',live_smoke=smoke)
        write(output/'CORRECTED_BAOSTOCK_CAPABILITY_RECEIPT.json',receipt)
        import hashlib
        smoke_path=output/'LIVE_READ_CAPABILITY_SMOKE_V1.json'
        runtime=package_metadata()
        write(smoke_path,dict(contract_id='BAOSTOCK_DAILY_UPDATE_LIVE_SMOKE_V1',status='PASS',
            runtime={k:runtime[k] for k in ('package','version','installed_python_sources_sha256')},
            auth_mode='PUBLIC_ANONYMOUS',live_smoke=smoke,AS_RECORDED=False,
            consumer_scope='CORRECTED_SOURCE_STAGING_ONLY'))
        manifest=build_runtime_acceptance_manifest(sdk=package_metadata(),auth_mode='PUBLIC_ANONYMOUS',live_smoke=smoke,
            smoke_receipt_path=smoke_path.relative_to(root).as_posix(),smoke_receipt_sha256=hashlib.sha256(smoke_path.read_bytes()).hexdigest())
        manifest.update(consumer_scope='CORRECTED_SOURCE_STAGING_ONLY',production_permission=False,AS_RECORDED=False)
        manifest['manifest_sha256']=canonical_sha256({k:v for k,v in manifest.items() if k!='manifest_sha256'})
        write(output/'CORRECTED_RUNTIME_CAPABILITY_MANIFEST.json',manifest)
        with BaoStockClient(budget,auth_mode='PUBLIC_ANONYMOUS',runtime_acceptance_manifest=manifest) as client:
            source=capture_baostock_daily_update(trade_date=target_date,client=CorrectedFactorSchemaClient(client,output),
                snapshot_root=root/'data/v4/source_snapshots',tdx_root=Path('D:/new_tdx'),runtime_acceptance_manifest=manifest)
        receipt.update(status=source['status'],snapshot_id=source['snapshot_id'],source_status=source['status'])
        write(output/'CORRECTED_BAOSTOCK_CAPTURE_RESULT.json',dict(source,AS_RECORDED=False,production_permission=False))
        return source,manifest,None
    except Exception as error:
        # Source errors are concrete and bounded. No fallback to fictitious empty rows.
        receipt.update(status='BLOCKED_CORRECTED_BAOSTOCK_CAPTURE',reason=str(error)[:1000],error_type=type(error).__name__)
        return None,None,receipt['reason']
    finally:
        receipt['request_count_this_run']=count()-before
        write(output/'CORRECTED_BAOSTOCK_FULL_TRACE.json',receipt)
