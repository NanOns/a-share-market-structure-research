"""Independent A12 R2 entry; retained R1 artifacts and no accepted owner writes."""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from scripts.formalize_source_authority_registry_r3 import protected_bindings,PERMISSIONS

def main():
    protected=protected_bindings()
    extra=['reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R3.json',
        'reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R4.json',
        'data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY.json','data/v4/V4_SOURCE_AUTHORITY_GOVERNANCE_HEAD_R1.json',
        'config/source_authority_governance_r2.json','src/workbench_analysis/status_st_authority_r1.py',
        'reports/audits/A10_R2_EXTERNAL_ACCEPTANCE_RECORD_R1.json']
    extra.extend(p.relative_to(ROOT).as_posix() for p in (ROOT/'reports/audits').glob('A12_*_R1.json'))
    protected.extend(bind(p) for p in extra)
    atomic_json(ROOT/'reports/audits/A12_R2_STAGE_ENTRY_R1.json',dict(
        contract_id='WP-A12-R2-REAL-DATED-STATUS-ST-AUTHORITY',
        baseline_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        task=bind('docs/evidence/source_authority/V4_A12_R2_REAL_DATED_STATUS_ST_AUTHORITY_REPAIR_TASK_20261001.md'),
        infrastructure_acceptance=bind('reports/audits/A10_R2_EXTERNAL_ACCEPTANCE_RECORD_R1.json'),
        protected_bindings=protected,phase0_status='FULL_PASS',
        phase0_evidence=bind('reports/v4_phase0/V4_PHASE0_STAGE_RECEIPTS_R5_20260928.json'),
        permissions=PERMISSIONS,stage_contract='REAL_SOURCE_ARCHAEOLOGY_THEN_UNIQUE_AUTHORITY_CANDIDATE_THEN_UNCHANGED_REPLAYS',
        external_acceptance=None,owner_registration_permitted=False,dm01_final_all_nine_permitted=False,
        next_stage='Independent A12 R2 external reaudit; owner registration and DM01 remain separately gated'))
    print('A12 R2 entry frozen; R1 preserved; owner registration prohibited')

if __name__=='__main__':main()
