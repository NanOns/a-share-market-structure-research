"""Actual bounded capability smoke and delayed target-date queries, append-only receipts."""
import argparse,json,sys,hashlib
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from workbench_analysis.baostock_supplemental import BaoStockClient,RequestBudget,package_metadata
from workbench_analysis.baostock_daily_update_source import DAILY_METHOD,FACTOR_METHOD,DAILY_REQUIRED_FIELDS,FACTOR_REQUIRED_FIELDS,_validate_daily_rows,_validate_factor_rows
from workbench_analysis.baostock_dm01_capability_v2 import build_capability,require_capability,classify_capture_response,digest

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--target-date',default='2026-09-28');parser.add_argument('--smoke-date',default='2026-09-30');args=parser.parse_args()
    sdk=package_metadata();run=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');base=ROOT/'reports/dm01/a01_r2'/run
    ledger=base/'request_ledger.json';base.mkdir(parents=True,exist_ok=True)
    observations={};capability=None;endpoint={};login_error=None
    try:
        with BaoStockClient(RequestBudget(ledger,hard_limit=12,soft_limit=10),auth_mode='PUBLIC_ANONYMOUS',timeout=30,allow_unaccepted_runtime_smoke=True) as client:
            endpoint=dict(client.runtime_endpoint)
            for purpose,target in [('CAPABILITY_SMOKE',args.smoke_date),('TARGET_DATE_CAPTURE',args.target_date)]:
                responses={}
                for method,required,validator in [(DAILY_METHOD,DAILY_REQUIRED_FIELDS,_validate_daily_rows),(FACTOR_METHOD,FACTOR_REQUIRED_FIELDS,_validate_factor_rows)]:
                    r=dict(method=method,target_trade_date=target,observed_at=datetime.now(timezone.utc).isoformat(),request_count=1,max_rows=20000,max_pages=1,auth_mode='PUBLIC_ANONYMOUS')
                    try:
                        rows,meta=client.query_rows('a01_r2_'+purpose.lower()+'_'+method,method,date=target,max_rows=20000,max_pages=1)
                        r.update(meta,received_at=datetime.now(timezone.utc).isoformat(),row_count=len(rows),response_sha256=digest(rows))
                        r['availability_state']=classify_capture_response(r,target=target,required_fields=required)
                        if r['availability_state'] in ('AVAILABLE','PROVIDER_TARGET_DATE_EMPTY'):validator(rows,target)
                        response_path=base/f'{purpose}_{method}_response.json';atomic_json(response_path,dict(rows=rows,provider_metadata=meta))
                        r['response_binding']=bind(response_path.relative_to(ROOT).as_posix())
                    except Exception as exc:
                        r.update(client.last_query_result,received_at=datetime.now(timezone.utc).isoformat(),availability_state='HISTORICAL_CATCHUP_QUERY_FAILED',error=client._safe_message(f'{type(exc).__name__}:{exc}'))
                        # Failed SDK calls have metadata receipts, never fabricated empty response bytes.
                    responses[method]=r
                receipt=dict(contract_id='BAOSTOCK_DM01_RUNTIME_SMOKE_V2' if purpose=='CAPABILITY_SMOKE' else 'BAOSTOCK_DM01_TARGET_DATE_CAPTURE_V2',
                    smoke_date=target if purpose=='CAPABILITY_SMOKE' else None,target_trade_date=target,provider_date=target,
                    auth_mode='PUBLIC_ANONYMOUS',responses=responses,endpoint=endpoint,sdk=sdk,origin='DELAYED_HISTORICAL_RETRIEVAL',lineage='RECONSTRUCTED_CORRECTED',
                    first_availability_at_target_proven=False,source_role='SUPPLEMENTAL_CROSSCHECK',canonical_qfq_authority=False,external_acceptance=None)
                if purpose=='TARGET_DATE_CAPTURE':
                    receipt['runtime_capability_id']=require_capability(capability,sdk,target) if capability else None
                    receipt['capability_verified']=capability is not None
                    receipt['source_revision_id']='BS-CAPTURE-V2:'+digest(dict(target=target,response_hashes={m:r.get('response_sha256') for m,r in responses.items()},states={m:r['availability_state'] for m,r in responses.items()}))
                receipt_path=base/f'{purpose}_receipt.json';atomic_json(receipt_path,receipt);observations[purpose]=bind(receipt_path.relative_to(ROOT).as_posix())
                if purpose=='CAPABILITY_SMOKE':
                    try:capability=build_capability(sdk,endpoint,receipt,observations[purpose]);atomic_json(base/'runtime_capability_v2.json',capability)
                    except ValueError as exc:observations['capability_failure']=str(exc)
    except Exception as exc:login_error=f'{type(exc).__name__}:{exc}'
    count=sum(v['count'] for v in json.loads(ledger.read_text(encoding='utf8'))['by_shanghai_date'].values()) if ledger.exists() else 0
    summary=dict(contract_id='DM01_A01_R2_BOUNDED_HISTORICAL_CATCHUP_R1',run_id=run,target_trade_date=args.target_date,smoke_date=args.smoke_date,
        request_count=count,requests_attempted=count>0,observations=observations,endpoint=endpoint,login_error=login_error,
        runtime_capability=bind((base/'runtime_capability_v2.json').relative_to(ROOT).as_posix()) if capability else None,
        source_role='SUPPLEMENTAL_CROSSCHECK',local_missing_does_not_prove_provider_empty=True,first_availability_at_target_proven=False,
        request_ledger=bind(ledger.relative_to(ROOT).as_posix()) if ledger.exists() else None,external_acceptance=None)
    atomic_json(ROOT/'reports/audits/A01_R2_HISTORICAL_CATCHUP_R1.json',summary)
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
