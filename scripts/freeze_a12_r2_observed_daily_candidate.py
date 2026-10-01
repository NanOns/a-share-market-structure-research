"""Separate observed daily owner proposal, limited to actual immutable captures."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
P='reports/audits/A12_R2_'
def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def main():
    base='reports/dm01/a01_r2/20261001T033251758661Z/normalized_schema_v2_1/'
    receipts=[read(base+n+'_normalized_receipt.json') for n in ['TARGET_DATE_CAPTURE','CAPABILITY_SMOKE']]
    captures=[]
    for receipt in receipts:
        r=receipt['responses']['query_daily_history_k_AStock'];raw=r['raw_response_binding'];assert bind(raw['path'])['sha256']==raw['sha256']
        captures.append(dict(target_trade_date=receipt['target_trade_date'],response=raw,observed_at=r['observed_at'],received_at=r['received_at'],historical_mode='TARGET_DATE_QUERYABLE_FACT',first_availability_at_target_proven=False))
    owners={}
    for field in ['TRADING_STATUS','ISST']:
        o=read(P+'OWNER_'+field+'_CANDIDATE_R1.json');o['contract_id']=o['contract_id'].replace('RECONSTRUCTED','OBSERVED_DAILY');o['effective_scope']=dict(start_date='2026-09-28',end_date='2026-09-30')
        o['source_bindings']=[x['response'] for x in captures];o['captured_dates_only']=[x['target_trade_date'] for x in captures];o['captured_observations']=captures;o['source_observed_at']=min(x['observed_at'] for x in captures)
        o['role_binding'].update(owner_contract_id=o['contract_id'],role_binding_id='A12_R2_OBSERVED_CANDIDATE_ROLE:'+field);o['role_binding_id']=o['role_binding']['role_binding_id']
        o['uncaptured_date_behavior']='BLOCKED_NO_FROZEN_DATED_RESPONSE; FUTURE_DAILY_REFRESH_REQUIRES_NEW_IMMUTABLE_REVISION'
        o['future_flow']='Capture raw source with actual receive time on every target date; accepted owner and scoped registration required before formal consumption'
        path=P+'OBSERVED_DAILY_OWNER_'+field+'_CANDIDATE_R1.json';atomic_json(ROOT/path,o);owners[field]=bind(path)
    atomic_json(ROOT/(P+'OBSERVED_DAILY_AUTHORITY_PROPOSAL_R1.json'),dict(status='PENDING_EXTERNAL_ACCEPTANCE',owner_bindings=owners,captures=captures,no_new_requests=True,formal_consumer_authorization=False,actual_registry_written=False,first_availability_at_target_proven=False,dm01_final_all_nine='BLOCKED',scope='Only 9/28 and 9/30 already captured on 10/1; no automatic authorization of 9/29 or future dates'))
    print('OBSERVED_DAILY_CANDIDATE_ONLY',len(captures))
if __name__=='__main__':main()
