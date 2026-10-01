"""Seal a completed clean regression without granting external acceptance."""
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json, atomic_bytes
from scripts.enter_source_authority_remediation_r2 import bind

def main():
    clean=ROOT.parent/'_a10_source_authority_clean_r1'
    receipt=json.loads((clean/'reports/audits/A10_CLEAN_CHECKOUT_R1.json').read_text(encoding='utf8'))
    assert receipt['status']=='PASS' and receipt['protected_heads_unchanged']
    contract=json.loads((ROOT/'config/source_authority_governance_r1.json').read_text(encoding='utf8'))
    assert all(bind(r['path'])['sha256']==r['sha256'] for r in contract['protected_bindings'])
    paths=['reports/audits/A10_'+s for s in ['CLEAN_CHECKOUT_R1.json','CLEAN_REGRESSION_R1.xml','CLEAN_REGRESSION_R1.log','NO_SYMBOL_SCAN_R1.json']]
    for p in paths:atomic_bytes(ROOT/p,(clean/p).read_bytes())
    gatepath='reports/audits/A10_ENGINEERING_GATES_R1.json'
    gates=json.loads((ROOT/gatepath).read_text(encoding='utf8'))
    gates.update(status='SOURCE_AUTHORITY_GOVERNANCE_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',clean_regression=bind(paths[0]))
    gates['gates']['A10-G11']='PASS_ENGINEERING';atomic_json(ROOT/gatepath,gates)
    statuspath='reports/audits/work_packages/WP-A10-SOURCE-AUTHORITY-GOVERNANCE/STATUS_R2.json'
    old=json.loads((ROOT/statuspath.replace('R2','R1')).read_text(encoding='utf8'))
    old.update(implementation_status=gates['status'],evidence=[bind(gatepath),*[bind(p) for p in paths]],next_step='Independent external A10 audit; A11/A12/DM01 candidate engineering authorized, no formal consumer or accepted-head promotion.')
    atomic_json(ROOT/statuspath,old)
    registry_path='reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R2.json'
    registry=json.loads((ROOT/registry_path).read_text(encoding='utf8'))
    registry['execution_scope']=['A10','A11','A12','A01_R2','A08','A09']
    registry['scope_authorization']='User reply: 本轮也执行 A08/A09; additive engineering candidates only.'
    for e in registry['entries']:
        if e['work_package']==old['work_package']:
            e.update(implementation_status=old['implementation_status'],status_path=statuspath,evidence=old['evidence'])
    atomic_json(ROOT/registry_path,registry)
    atomic_json(ROOT/'reports/audits/A10_STAGE_CLOSURE_R1.json',dict(status=gates['status'],tested_commit=receipt['tested_commit'],gates=bind(gatepath),protected_bindings=contract['protected_bindings'],accepted_heads_unchanged=True,external_acceptance=None,next_stage='A11 identity authority audit; A12 producer freeze; A01_R2 capture; authorized A08/A09 independent repairs',permissions={'production':False,'shadow':False,'focus_cutover':False}))
    print(gates['status'])

if __name__=='__main__':main()
