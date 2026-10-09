"""Genuine per-target runtime smoke for elapsed official operational sessions."""
from pathlib import Path
from datetime import datetime
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.accept_v4_dm01_baostock_runtime import _record, REQUIRED_DAILY_FIELDS, REQUIRED_FACTOR_FIELDS
from workbench_analysis.baostock_supplemental import RequestBudget, package_metadata
from workbench_analysis.operational_baostock_client_v1 import BaoStockClient
from workbench_analysis.baostock_daily_update_source import DAILY_METHOD, FACTOR_METHOD, _validate_daily_rows, _validate_factor_rows
from workbench_analysis.baostock_runtime_acceptance import build_runtime_acceptance_manifest
from workbench_analysis.daily_data_head import write_json_atomic
from workbench_analysis.dm01_runtime_r4 import calendar
from workbench_analysis.source_readiness_v2 import source_readiness
from workbench_analysis.operational_daily_calendar_v2 import SHANGHAI
from workbench_analysis.baostock_dm01_sdk_schema_v2 import normalize_response


def accept_runtime(target, root=ROOT):
    root=Path(root);now=datetime.now(SHANGHAI)
    if target not in calendar(root)['session_dates']:
        return dict(status='BLOCKED',reason='OFFICIAL_SESSION_NOT_VERIFIED')
    if not source_readiness(target,now)['time_eligible']:
        return dict(status='WAIT_BAOSTOCK_FACTOR',reason='TIME_GATE_NOT_REACHED')
    runtime=package_metadata()
    schema_contract=json.loads((root/'config/baostock_dm01_sdk_schema_adapter_v2.json').read_bytes())
    folder=root/'reports/v4_baostock/runtime_acceptance'/target.replace('-','')
    stamp=now.strftime('%Y%m%dT%H%M%S%f')
    smoke_path=folder/(stamp+'_live_smoke_receipt.json')
    receipt=dict(contract_id='BAOSTOCK_DAILY_UPDATE_LIVE_SMOKE_V1',version='1.0.0',
        target_date=target,observed_at=now.isoformat(),auth_mode='PUBLIC_ANONYMOUS',
        runtime={k:runtime[k] for k in ['package','version','installed_python_sources_sha256']},
        status='FAIL',live_smoke=None,tdx_root_write_count=0)
    try:
        with BaoStockClient(RequestBudget(root/'reports/v4_baostock/request_ledger.json'),
                auth_mode='PUBLIC_ANONYMOUS',allow_unaccepted_runtime_smoke=True) as client:
            daily,dm=client.query_rows('dynamic_daily_smoke_daily',DAILY_METHOD,date=target,max_rows=20000,max_pages=1)
            factor,fm=client.query_rows('dynamic_daily_smoke_factor',FACTOR_METHOD,date=target,max_rows=20000,max_pages=1)
            receipt['response_metadata']=dict(daily=dm,adjustment_factor=fm)
            receipt['response_row_counts']=dict(daily=len(daily),adjustment_factor=len(factor))
            raw_path=folder/(stamp+'_raw_responses.json')
            raw_sha=write_json_atomic(raw_path,
                dict(target_date=target,observed_at=now.isoformat(),daily_rows=daily,daily_metadata=dm,
                     adjustment_factor_rows=factor,adjustment_factor_metadata=fm),tdx_root=Path('D:/new_tdx'))
            receipt['native_response']=dict(path=raw_path.relative_to(root).as_posix(),sha256=raw_sha)
            daily,dm=normalize_response(daily,dm,target=target,sdk=runtime,contract=schema_contract,method=DAILY_METHOD)
            factor,fm=normalize_response(factor,fm,target=target,sdk=runtime,contract=schema_contract,method=FACTOR_METHOD)
            receipt['schema_adapter']=dict(contract_id=schema_contract['contract_id'],
                independent_external_acceptance='NOT_GRANTED',role='SPELLING_AND_RESPONSE_DATE_EVIDENCE_ONLY')
            _validate_daily_rows(daily,target);_validate_factor_rows(factor,target)
            if not daily:
                raise ValueError('BAOSTOCK_LIVE_SMOKE_NO_TARGET_DATE_DAILY_ROWS')
            if not factor:
                from workbench_analysis.operational_runtime_acceptance_v2 import prove_no_change
                from workbench_analysis.baostock_daily_update_source import _canonical_rows_digest
                proof=prove_no_change(root,target,daily,client,runtime)
                factor_record=dict(method=FACTOR_METHOD,provider_date=None,row_count=0,fields=fm['fields'],
                    response_sha256=_canonical_rows_digest(factor),no_change_target_session=target,no_change_proof=proof)
            else:factor_record=_record(FACTOR_METHOD,factor,fm,REQUIRED_FACTOR_FIELDS,target)
            smoke=dict(status='PASS',target_date=target,auth_mode=client.auth_mode,
                endpoint=dict(client.runtime_endpoint),daily=_record(DAILY_METHOD,daily,dm,REQUIRED_DAILY_FIELDS,target),
                adjustment_factor=factor_record)
            receipt.update(status='PASS',live_smoke=smoke)
    except (ValueError,OSError,RuntimeError) as exc:
        receipt['reason']=str(exc)[:160]
    digest=write_json_atomic(smoke_path,receipt,tdx_root=Path('D:/new_tdx'))
    if receipt['status']!='PASS':
        return dict(status='WAIT_BAOSTOCK_DAILY_UPDATE',reason=receipt.get('reason'),
                    smoke_receipt=smoke_path.relative_to(root).as_posix(),source_sha256=digest)
    if receipt['live_smoke']['adjustment_factor']['row_count']==0:
        from workbench_analysis.operational_runtime_acceptance_v2 import CONTRACT,canonical_sha256
        manifest=dict(contract_id=CONTRACT,version='2.0.0',status='ACCEPTED',runtime=receipt['runtime'],auth_mode=receipt['auth_mode'],
            live_smoke=receipt['live_smoke'],smoke_receipt=dict(path=smoke_path.relative_to(root).as_posix(),sha256=digest))
        manifest['manifest_sha256']=canonical_sha256(manifest)
    else:
        manifest=build_runtime_acceptance_manifest(sdk=runtime,auth_mode=receipt['auth_mode'],live_smoke=receipt['live_smoke'],
            smoke_receipt_path=smoke_path.relative_to(root).as_posix(),smoke_receipt_sha256=digest)
    write_json_atomic(folder/(stamp+'_accepted_runtime_manifest.json'),manifest,tdx_root=Path('D:/new_tdx'))
    write_json_atomic(folder/'accepted_runtime_manifest.json',manifest,tdx_root=Path('D:/new_tdx'))
    return dict(status='ACCEPTED',target_date=target,manifest= (folder/'accepted_runtime_manifest.json').relative_to(root).as_posix())


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--target-date',required=True);a=p.parse_args()
    result=accept_runtime(a.target_date);print(json.dumps(result,ensure_ascii=False))
    raise SystemExit(0 if result['status']=='ACCEPTED' else 2)
