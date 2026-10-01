"""Three bounded real empty-return cases, distinct from frozen historical replay scope."""
import sys,json
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from workbench_analysis.baostock_supplemental import BaoStockClient,RequestBudget,package_metadata
def main():
    p=ROOT/'data/v4/source_evidence/a12_r2';target=p/'PROVIDER_EMPTY_RETURN_CAPTURE_R1.json'
    if target.exists():raise ValueError('IMMUTABLE_CAPTURE_ALREADY_EXISTS')
    windows=json.loads((p/'PROVIDER_EMPTY_RETURN_CONTRACT_R1.json').read_text(encoding='utf8'))['windows']
    contract=p/'PROVIDER_EMPTY_RETURN_CONTRACT_R1.json';atomic_json(contract,dict(contract_id='A12_R2_EMPTY_RETURN_SEMANTICS_V1',windows=windows,fields=['date','code','tradestatus','isST'],max_requests=5,max_rows_each=8,max_pages=1,timeout=35,auth_mode='PUBLIC_ANONYMOUS',purpose='Real empty return semantics validation after archaeology; no repeated DM01 target capture',sdk=package_metadata(),formal_authorization=False))
    budget=RequestBudget(p/'provider_empty_request_ledger_r1.json',hard_limit=5,soft_limit=4);results=[]
    with BaoStockClient(budget,timeout=35,auth_mode='PUBLIC_ANONYMOUS',allow_unaccepted_runtime_smoke=True) as client:
        for w in windows:
            t=datetime.now(timezone.utc).isoformat();rows,meta=client.query_rows('a12_r2_empty_semantics','query_history_k_data_plus',w['code'],'date,code,tradestatus,isST',start_date=w['start'],end_date=w['end'],frequency='d',adjustflag='3',max_rows=8,max_pages=1)
            results.append({**w,'rows':rows,'metadata':meta,'observed_at':t,'received_at':datetime.now(timezone.utc).isoformat(),'no_row_interpretation':'UNKNOWN_FIELD; NOT_NORMAL_OR_SUSPENDED'})
    atomic_json(target,dict(contract_id='A12_R2_REAL_EMPTY_RETURN_CAPTURE_V1',contract=bind(contract.relative_to(ROOT).as_posix()),results=results,endpoint=client.runtime_endpoint,login=client.login_result,logout=client.logout_result,ledger=bind(budget.path.relative_to(ROOT).as_posix()),sdk=package_metadata(),formal_authorization=False))
    print([(x['category'],len(x['rows'])) for x in results])
if __name__=='__main__':main()
