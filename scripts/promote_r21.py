"""Create capability-scoped artifacts, committing visibility with one Stage replace."""
import json,subprocess
from scripts.r21_io import ROOT,BASE,TESTED,TAG,AUDIT,STAGE,HEAD,ref,atomic
def promote(root=ROOT):
    parent=(root/'reports/r21/PARENT_STAGE_HEAD.json').read_bytes()
    assert (root/STAGE).read_bytes()==parent,'EXACT_PARENT_REQUIRED'
    assert subprocess.check_output(['git','rev-parse',TAG+'^{commit}'],cwd=root).decode().strip()==TESTED
    audit=(root/AUDIT).read_text(encoding='utf8')
    assert ref(AUDIT,root)['sha256']=='daadcfe74ecb5a23aa9aaca09d0168e72b0e19e1d304a26e35ec5bde49826f71','EXACT_AUTHORIZING_AUDIT_REQUIRED'
    assert 'PASS_FINAL_V4_15_RUNTIME_CANDIDATE_CAPABILITY_SCOPED' in audit and 'V4_15_PROMOTION = AUTHORIZED' in audit and BASE in audit
    c=json.loads((root/'reports/r21/PARENT_CURRENT_STAGE_AUTHORITY.json').read_bytes())
    paths=dict(predecessor_v4_14='data/v4/V4_14_ACCEPTED_HEAD.json',contract_package='config/v4_15_contract_package_v1.json',runtime_seal='reports/r20e/V4_15_RUNTIME_CANDIDATE_R20_SEAL.json',scope_seal='reports/r20r1/V4_15_R20R1_CANDIDATE_SEAL.json',debt_seal='reports/r20r1r1/V4_15_R20R1R1_CANDIDATE_SEAL.json',dm01_seal='reports/r20r1r2/V4_15_R20R1R2_CANDIDATE_SEAL.json',external_audit=AUDIT,data_head='data/v4/V4_DATA_ACCEPTED_HEAD.json',maturity_readback='reports/r20r1r2/MATURITY_DEBT_READBACK.json',forward_projection='config/v4_15_forward_projection_r20r1r2_v1.json',open_validation_debt='reports/r20r1/OPEN_VALIDATION_DEBT.json')
    bindings={k:ref(p,root) for k,p in paths.items()}
    bindings.update({k:c[k] for k in ['calendar','identity','membership']})
    capabilities={k:'ENGINEERING_ACCEPTED' for k in ['V4_15_RUNTIME_ENGINEERING','RADAR_COHORT_RUNTIME','SETTLEMENT_RUNTIME','PERSISTED_E2E','INDEPENDENT_ORACLE','REAL_DM01_DATA_HEAD_REACHABILITY','REAL_DM01_ROW_SCHEMA_ADMISSION','FORWARD_EVALUATION_PROJECTION','HORIZON_SCOPED_VALIDATION_DEBT']}
    capabilities.update({k:'PASS_CAPABILITY_SCOPED' for k in ['REAL_ACCEPTED_SOURCE_T0_INTEGRATION','REAL_ACCEPTED_SOURCE_PENDING_DUE_READBACK']})
    boundary=dict(CURRENT_REAL_MATURITY_EVIDENCE='NONE',REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME='NOT_GRANTED_PENDING_MATURITY_EVIDENCE',REALTIME_ACCEPTED_COHORT_MATURITY='NOT_GRANTED',HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',PROVED_HORIZONS=[],UNPROVED_HORIZONS=[1,3,5,10,20],V4_15_FWD_ADJ_VECTOR_01='OPEN_NONBLOCKING_TEST_ENHANCEMENT',production=False,shadow=False,focus=False,V4_16=False)
    entry=dict(contract_id='V4_15_ACCEPTED_ENTRY_CONTRACT_V1',version='1.0.0',accepted_head_namespace=HEAD,bindings=bindings,capabilities=capabilities,tested_source=TESTED,immutable_tested_tag=TAG,execution_baseline=BASE,**boundary)
    er=atomic('config/v4_15_accepted_entry_contract_v1.json',entry,root)
    head=dict(contract_id='V4_15_ACCEPTED_HEAD_V1',version='1.0.0',stage='V4-15',status='RUNTIME_ENGINEERING_PASS_CAPABILITY_SCOPED',external_acceptance='EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED',external_audit_decision='PASS_FINAL_V4_15_RUNTIME_CANDIDATE_CAPABILITY_SCOPED',accepted_trade_date='2026-09-30',entry_contract=er,bindings=bindings,capabilities=capabilities,tested_source=TESTED,immutable_tested_tag=TAG,**boundary)
    hr=atomic(HEAD,head,root)
    c.update(contract_id='V4_CURRENT_STAGE_AUTHORITY_V2',version='2.0.0',input_commit=BASE,accepted_stage_range='V4_00_TO_V4_15_ACCEPTED',current_head=hr,predecessor_v4_14=bindings['predecessor_v4_14'],external_audit=bindings['external_audit'],V4_15_accepted=True,parent_stage=ref('reports/r21/PARENT_STAGE_HEAD.json',root),reader='CURRENT_V4_15_WITH_EXPLICIT_V4_14_PUBLICATION_AND_REPLAY_PREDECESSOR')
    atomic('config/v4_current_stage_authority_v2.json',c,root)
    # Reader code must be version-safe before visibility changes.
    assert 'v4_current_stage_authority_v2.json' in (root/'src/workbench_analysis/v4_current_stage_authority.py').read_text()
    stage=json.loads(parent);stage.update(accepted_stage_range=c['accepted_stage_range'],v4_15_binding=hr,v4_15_entry='COMPLETED_EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED_RUNTIME',v4_15_external_acceptance=head['external_audit_decision'],v4_15_capabilities=capabilities,v4_15_capability_boundary=boundary)
    atomic(STAGE,stage,root)
if __name__=='__main__':promote()
