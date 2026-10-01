"""Bounded public historical revision probes; never re-query DM01 target captures."""
import json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from workbench_analysis.baostock_supplemental import BaoStockClient,RequestBudget,package_metadata
WINDOWS=[('sh.600518','2024-07-01','2024-07-05'),('sh.600387','2024-04-19','2024-04-25'),('sz.000972','2025-03-27','2025-04-02'),('sz.300114','2025-02-14','2025-02-18'),('sz.302132','2025-02-14','2025-02-18'),('sh.600225','2025-02-05','2025-02-10'),('sh.688981','2023-07-04','2023-07-05'),('sz.301611','2026-09-24','2026-09-24')]
def now():return datetime.now(timezone.utc).isoformat()
def main():
    out=ROOT/'data/v4/source_evidence/a12_r2';receipt=out/'PROVIDER_SEMANTICS_REVISION_CAPTURE_R1.json'
    if receipt.exists():raise ValueError('IMMUTABLE_CAPTURE_ALREADY_EXISTS')
    contract=out/'PROVIDER_SEMANTICS_REVISION_CONTRACT_R1.json'
    atomic_json(contract,dict(contract_id='A12_R2_PROVIDER_SEMANTICS_REVISION_V1',reason='Existing 9/26 reconstructed cache lacks comparative revision observation and official transition cross-validation; no DM01 target re-query',windows=WINDOWS,fields=['date','code','tradestatus','isST'],adjustflag='3',frequency='d',max_rows_per_query=32,max_pages=1,max_requests=10,timeout_seconds=35,auth_mode='PUBLIC_ANONYMOUS',source_role='DIAGNOSTIC_REVISION_PROBE',formal_consumer_authorization=False,first_availability_at_target_proven=False,sdk=package_metadata()))
    budget=RequestBudget(out/'provider_request_ledger_r1.json',hard_limit=10,soft_limit=9);results=[]
    client=BaoStockClient(budget,timeout=35,auth_mode='PUBLIC_ANONYMOUS',allow_unaccepted_runtime_smoke=True)
    try:
        with client:
            for code,start,end in WINDOWS:
                observed=now()
                try:
                    rows,meta=client.query_rows('a12_r2_semantics_revision','query_history_k_data_plus',code,'date,code,tradestatus,isST',start_date=start,end_date=end,frequency='d',adjustflag='3',max_rows=32,max_pages=1)
                    results.append(dict(code=code,start=start,end=end,observed_at=observed,received_at=now(),rows=rows,metadata=meta))
                    print(code,len(rows),flush=True)
                except Exception as e:results.append(dict(code=code,start=start,end=end,observed_at=observed,error=str(e)));break
    finally:
        atomic_json(receipt,dict(contract_id='A12_R2_PROVIDER_SEMANTICS_REVISION_CAPTURE_V1',contract=bind(contract.relative_to(ROOT).as_posix()),results=results,login=client.login_result,logout=client.logout_result,endpoint=client.runtime_endpoint,ledger=bind(budget.path.relative_to(ROOT).as_posix()),sdk=package_metadata(),historical_mode='TARGET_DATE_QUERYABLE_FACT',lineage='RECONSTRUCTED_CORRECTED',formal_authorization=False))
if __name__=='__main__':main()
