"""Seal completed independent R2 engineering work without claiming an all-nine candidate."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json,atomic_bytes
from scripts.enter_source_authority_remediation_r2 import bind

def main():
    p=argparse.ArgumentParser();p.add_argument('--clean-root',required=True);args=p.parse_args();clean=Path(args.clean_root)
    names=['A01_R2_CLEAN_CHECKOUT_R1.json','A01_R2_CLEAN_REGRESSION_R1.xml','A01_R2_CLEAN_REGRESSION_R1.log','A01_R2_NO_SYMBOL_SCAN_R1.json']
    clean_result=json.loads((clean/'reports/audits'/names[0]).read_text(encoding='utf8'));assert clean_result['status']=='PASS'
    for name in names:atomic_bytes(ROOT/'reports/audits'/name,(clean/'reports/audits'/name).read_bytes())
    protected=json.loads((ROOT/'config/source_authority_governance_r1.json').read_text(encoding='utf8'))['protected_bindings'];assert all(bind(b['path'])['sha256']==b['sha256'] for b in protected)
    blocker=json.loads((ROOT/'reports/audits/A01_R2_DEPENDENCY_BLOCKER_R1.json').read_text(encoding='utf8'))
    assert blocker['status']=='BLOCKED_A12_EXTERNAL_OWNER_ACCEPTANCE'
    receipt=dict(status='INDEPENDENT_R2_RUNTIME_CAPTURE_AND_PREFLIGHT_ENGINEERING_PASS_FINAL_ALL_NINE_BLOCKED',stage_completed=False,work_package='WP-A01-DM01',tested_commit=clean_result['tested_commit'],clean_regression=bind('reports/audits/'+names[0]),blocker=bind('reports/audits/A01_R2_DEPENDENCY_BLOCKER_R1.json'),runtime_capture=bind('reports/audits/A01_R2_NORMALIZED_RUNTIME_AND_TARGET_CAPTURE_R2.json'),normalization_storage_repair=bind('reports/audits/A01_R2_NORMALIZATION_PATH_COLLISION_REPAIR_R1.json'),independent_source_checks=bind('reports/audits/A01_R2_INDEPENDENT_CAPTURE_AND_SOURCE_PREFLIGHT_R1.json'),next_stage=blocker['next_stage'],accepted_heads_unchanged=True,external_acceptance=None,all_nine_final_execution_performed=False,production_permission=False,shadow_production_permission=False,focus_cutover_permission=False)
    atomic_json(ROOT/'reports/audits/A01_R2_PARTIAL_ENGINEERING_CLOSURE_R1.json',receipt)
    path=ROOT/'reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R2.json';registry=json.loads(path.read_text(encoding='utf8'));entry=next(e for e in registry['entries'] if e['work_package']=='WP-A01-DM01')
    old=json.loads((ROOT/entry['status_path']).read_text(encoding='utf8'));statuspath='reports/audits/work_packages/WP-A01-DM01/STATUS_R2_RUNTIME_CAPTURE_ENGINEERING_PASS_FINAL_BLOCKED.json'
    evidence=[bind('reports/audits/A01_R2_PARTIAL_ENGINEERING_CLOSURE_R1.json'),bind('reports/audits/A01_R2_DEPENDENCY_BLOCKER_R1.json')]
    old.update(implementation_status=receipt['status'],status='OPEN',external_acceptance=None,evidence=evidence,next_step=blocker['next_stage'],pending_required_scope=blocker['pending_required_scope'])
    atomic_json(ROOT/statuspath,old);entry.update(implementation_status=receipt['status'],status_path=statuspath,evidence=evidence,next_step=blocker['next_stage']);atomic_json(path,registry)
    print(receipt['status'])

if __name__=='__main__':main()
