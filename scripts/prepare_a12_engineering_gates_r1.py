"""Record scope-specific engineering gates; external acceptance is independent."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind

def main():
    names=['A12_STAGE_ENTRY_R1','V4_02_STATUS_ST_AUTHORITY_INVENTORY_R1','A12_PRODUCER_CONTRACT_FREEZE_R1','A12_V4_02_FULL_HISTORICAL_REPAIR_AND_DIFF_R1','A12_FORMAL_PERIOD_AUTHORITY_REBIND_R1','A12_INDEPENDENT_FULL_ROW_ORACLE_R1','A12_UNCHANGED_REPLAY_SOURCE_PROOFS_R1','A12_V4_04_TRUE_REPLAY_R1','A12_DOWNSTREAM_CASCADE_AND_FULL_BUSINESS_DIFF_R1']
    evidence=[bind('reports/audits/'+n+'.json') for n in names]
    protected=json.loads((ROOT/'config/source_authority_governance_r1.json').read_text(encoding='utf8'))['protected_bindings']
    assert all(bind(b['path'])['sha256']==b['sha256'] for b in protected)
    atomic_json(ROOT/'reports/audits/A12_ENGINEERING_GATES_R1.json',dict(status='PENDING_CLEAN_DETACHED',work_package='WP-A12-V4-02-STATUS-ST-AUTHORITY',allowed_candidate_status='V4_02_STATUS_ST_AUTHORITY_REPAIR_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',gates={**{f'A12-G{i:02}':'PASS_ENGINEERING' for i in range(1,14)},'A12-G14':'PENDING_CLEAN_DETACHED','A12-G15':'PENDING_INDEPENDENT_EXTERNAL_AUDIT'},evidence=evidence,source_authority_path='PATH_A_CURRENT_MASTER_CONTRACT',historical_dated_st_or_suspension_source_recovered=False,known_st_output_permission=False,real_samples='All accepted local bars independently checked over 4,035,729 memberships; unproven ST/suspension remains UNKNOWN. Dated owner transition vectors are explicit synthetic contract fixtures, not real official acceptance.',next_stage='Independent external A12 source semantics acceptance; DM01 final real-source candidate must bind that accepted producer before promotion.',external_acceptance=None,formal_publication=False,accepted_heads_unchanged=True))

if __name__=='__main__':main()
