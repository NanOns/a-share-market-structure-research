"""Produce new scope gates; no rewrite of accepted heads or R20 receipts."""
import json,subprocess
from scripts.r20r1_io import ROOT,BASE,ref,atomic
def build():
    feasibility=json.loads((ROOT/'reports/r20r1/REAL_MATURITY_FEASIBILITY_GATE.json').read_bytes())
    if feasibility['decision']!='NO_ACCEPTED_MATURED_LINEAGE_AVAILABLE':raise ValueError('INDEPENDENT_FEASIBILITY_FIRST')
    contract=json.loads((ROOT/'config/v4_15_capability_scope_r20r1_v1.json').read_bytes())
    gate=dict(contract_id='V4_15_CAPABILITY_SCOPE_GATE_R20R1_V1',execution_baseline=BASE,R20R1_SCOPE_CLOSURE='PASS_LOCAL',**contract['capabilities'],**contract['protected_state'],bindings={n:ref(p) for n,p in {'scope_contract':'config/v4_15_capability_scope_r20r1_v1.json','feasibility':'reports/r20r1/REAL_MATURITY_FEASIBILITY_GATE.json','external_audit':'docs/evidence/r20r1/V4_R20_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md','master':'docs/evidence/r20r1/V4_NEXT_ROUND_EXECUTION_MASTER_R20R1_20261003.md','task':'docs/evidence/r20r1/V4_15_R20R1_REAL_MATURITY_SCOPE_CLOSURE_TASK_20261003.md','historical_seal':'reports/r20e/V4_15_RUNTIME_CANDIDATE_R20_SEAL.json','engineering_e2e':'reports/r20e/INDEPENDENT_E2E_GATE.json','real_settlement':'reports/r20d/SETTLEMENT_GATE.json'}.items()},supersession={'scope':'PROMOTION_SEMANTICS_ONLY','historical_files_rewritten':False,'labels_superseded':['REAL_ACCEPTED_SOURCE_SETTLEMENT','REAL_ACCEPTED_SOURCE_V4_15'],'replacement_capabilities':list(contract['capabilities']),'R20A_R20B_CURRENT_R20C_R20D_ENGINEERING_R20E_ENGINEERING':'PASS_KEEP'},OPEN_VALIDATION_DEBT='REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT')
    atomic('reports/r20r1/V4_15_CAPABILITY_SCOPE_GATE.json',gate)
    debt=dict(contract_id='R20R1_MATURITY_VALIDATION_DEBT_V1',audit_item_id='R20_AUDIT_P0_REAL_MATURED_SCOPE',scope='REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_ONLY',status='OPEN',OPEN_VALIDATION_DEBT='REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT',capability=contract['capabilities']['REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT'],policy=contract['validation_debt'],evidence=[ref('reports/r20r1/REAL_MATURITY_FEASIBILITY_GATE.json')],accepted_future_endpoint_read_count=0,matured_real_horizons=[],required_horizon_namespace=[1,3,5,10,20],append_only_revision_namespace='reports/r20r1/maturity_debt_revisions/',historical_PIT_debt_is_separate=True,HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
    atomic('reports/r20r1/OPEN_VALIDATION_DEBT.json',debt)
    protected=[]
    for prefix in ['reports/r20a','reports/r20b','reports/r20c','reports/r20d','reports/r20e','reports/v4_15_runtime_r20','data/v4/V4_14_ACCEPTED_HEAD.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json']:
        names=subprocess.check_output(['git','ls-files',prefix],cwd=ROOT,text=True,encoding='utf8').splitlines()
        protected.extend(ref(p) for p in names)
    atomic('reports/r20r1/FROZEN_BASELINE_BINDINGS.json',dict(execution_baseline=BASE,bindings=protected))
    return gate
if __name__=='__main__':print(json.dumps(build()))
