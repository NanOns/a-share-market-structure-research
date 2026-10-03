"""Independently reconstruct scope expectations from immutable disk authority.

Does not import the gate writer, capability admission function, or runtime evaluators.
"""
import json,subprocess
from pathlib import Path
from scripts.validate_r20r1_feasibility import inspect,exact,descriptor,require
ROOT=Path(__file__).resolve().parents[1]
def validate(root=ROOT,gate=None,debt=None):
    root=Path(root)
    load=lambda p:json.loads((root/p).read_bytes())
    expected=inspect(root);recorded=load('reports/r20r1/REAL_MATURITY_FEASIBILITY_GATE.json')
    require(expected==recorded,'INDEPENDENT_FEASIBILITY_RECOMPUTE')
    g=gate if gate is not None else load('reports/r20r1/V4_15_CAPABILITY_SCOPE_GATE.json')
    d=debt if debt is not None else load('reports/r20r1/OPEN_VALIDATION_DEBT.json')
    required={'V4_15_RUNTIME_ENGINEERING':'PASS','REAL_ACCEPTED_SOURCE_T0_INTEGRATION':'PASS_CAPABILITY_SCOPED','REAL_ACCEPTED_SOURCE_PENDING_DUE_READBACK':'PASS_CAPABILITY_SCOPED','REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT':'NOT_GRANTED_PENDING_MATURITY_EVIDENCE','HISTORICAL_PIT_EFFECTIVENESS':'NOT_GRANTED'}
    require(all(g.get(k)==v for k,v in required.items()),'NO_CAPABILITY_WIDENING')
    require(not any(k in g for k in ['REAL_ACCEPTED_SOURCE_V4_15','REAL_ACCEPTED_SOURCE_SETTLEMENT']),'AMBIGUOUS_LABEL_SUPERSEDED')
    require(g['R20R1_SCOPE_CLOSURE']=='PASS_LOCAL','SCOPE_CLOSURE_REQUIRED')
    require(g['supersession']=={'scope':'PROMOTION_SEMANTICS_ONLY','historical_files_rewritten':False,'labels_superseded':['REAL_ACCEPTED_SOURCE_SETTLEMENT','REAL_ACCEPTED_SOURCE_V4_15'],'replacement_capabilities':list(load('config/v4_15_capability_scope_r20r1_v1.json')['capabilities']),'R20A_R20B_CURRENT_R20C_R20D_ENGINEERING_R20E_ENGINEERING':'PASS_KEEP'},'EXPLICIT_NARROW_SUPERSESSION')
    expected_paths={'scope_contract':'config/v4_15_capability_scope_r20r1_v1.json','feasibility':'reports/r20r1/REAL_MATURITY_FEASIBILITY_GATE.json','external_audit':'docs/evidence/r20r1/V4_R20_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md','master':'docs/evidence/r20r1/V4_NEXT_ROUND_EXECUTION_MASTER_R20R1_20261003.md','task':'docs/evidence/r20r1/V4_15_R20R1_REAL_MATURITY_SCOPE_CLOSURE_TASK_20261003.md','historical_seal':'reports/r20e/V4_15_RUNTIME_CANDIDATE_R20_SEAL.json','engineering_e2e':'reports/r20e/INDEPENDENT_E2E_GATE.json','real_settlement':'reports/r20d/SETTLEMENT_GATE.json'}
    require(g['bindings']=={n:descriptor(p,root) for n,p in expected_paths.items()},'EXACT_REQUIRED_EVIDENCE_BINDING')
    for b in g['bindings'].values():exact(b,root)
    contract=exact(g['bindings']['scope_contract'],root);require(contract['capabilities']==required,'CONTRACT_CANNOT_REDEFINE_EXPECTED')
    protected={'V4_15_ACCEPTED_HEAD':'NOT_CREATED','V4_STAGE_ACCEPTED_HEAD':'V4_00_TO_V4_14_ACCEPTED','V4_DATA_ACCEPTED_HEAD':'2026-09-30','NEXT':'STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT'}
    require(all(g.get(k)==v for k,v in protected.items()) and all(g.get(k) is False for k in ['Production','Shadow','Focus','V4_16']),'PROTECTED_STATE')
    require(d['status']=='OPEN' and d['OPEN_VALIDATION_DEBT']==g['OPEN_VALIDATION_DEBT']=='REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT','OPEN_REAL_MATURITY_DEBT')
    require(d['capability']==required['REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT'] and not d['matured_real_horizons'] and d['accepted_future_endpoint_read_count']==0,'NO_DEBT_FABRICATION')
    require(d['policy']==contract['validation_debt'] and d['policy']['blocks_unrelated_development'] is False and d['policy']['blocks_dependent_claims'] is True and d['policy']['does_not_authorize_next_stage'] is True,'NONBLOCKING_SCOPED_DEBT')
    require(d['evidence']==[descriptor('reports/r20r1/REAL_MATURITY_FEASIBILITY_GATE.json',root)],'DEBT_EXACT_EVIDENCE')
    if (root/'reports/r20r1/MATURITY_DEBT_READBACK.json').exists():
        view=load('reports/r20r1/MATURITY_DEBT_READBACK.json');revision=exact(view['LATEST_VALIDATED'],root)
        require(view['status']==revision['status']=='OPEN' and not revision['verified_maturity_receipts'] and not view['matured_real_horizons'],'CURRENT_INCREMENT_CANNOT_CLOSE_REAL_DEBT')
        require(revision['initial_debt']==descriptor('reports/r20r1/OPEN_VALIDATION_DEBT.json',root),'INITIAL_DEBT_BINDING')
    for b in load('reports/r20r1/FROZEN_BASELINE_BINDINGS.json')['bindings']:exact(b,root)
    require(subprocess.check_output(['git','diff','7f97f4487e2c8aaccb7e7701af4ccfddfa7ddec9','--name-only','--','src','data','reports/r20a','reports/r20b','reports/r20c','reports/r20d','reports/r20e','reports/v4_15_runtime_r20'],cwd=root)==b'','R20_IMPLEMENTATION_AND_EVIDENCE_KEEP')
    return dict(R20R1_INDEPENDENT_ORACLE='PASS_LOCAL',R20R1_SCOPE_CLOSURE='PASS_LOCAL',capabilities=required,feasibility=expected['decision'],future_read_count=0,all_real_outcomes_pending=True,historical_evidence_unchanged=True,OPEN_VALIDATION_DEBT='REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT',NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
if __name__=='__main__':print(json.dumps(validate(),indent=2))
