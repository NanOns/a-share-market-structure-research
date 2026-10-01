"""Append work-package engineering evidence; external audit items remain OPEN."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_bytes,atomic_json
from scripts.enter_source_authority_remediation_r2 import bind

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--package',required=True);parser.add_argument('--clean-root',required=True);args=parser.parse_args()
    wp=args.package;clean=Path(args.clean_root)
    paths=[f'reports/audits/{wp}_{s}' for s in ['CLEAN_CHECKOUT_R1.json','CLEAN_REGRESSION_R1.xml','CLEAN_REGRESSION_R1.log','NO_SYMBOL_SCAN_R1.json']]
    receipt=json.loads((clean/paths[0]).read_text(encoding='utf8'));assert receipt['status']=='PASS'
    contract=json.loads((ROOT/'config/source_authority_governance_r1.json').read_text(encoding='utf8'))
    assert all(bind(r['path'])['sha256']==r['sha256'] for r in contract['protected_bindings'])
    for p in paths:atomic_bytes(ROOT/p,(clean/p).read_bytes())
    gatepath=f'reports/audits/{wp}_ENGINEERING_GATES_R1.json'
    gates=json.loads((ROOT/gatepath).read_text(encoding='utf8'))
    for k,v in gates['gates'].items():
        if v=='PENDING_CLEAN_DETACHED':gates['gates'][k]='PASS_ENGINEERING'
    assert all(v in ['PASS_ENGINEERING','PENDING_INDEPENDENT_EXTERNAL_AUDIT'] for v in gates['gates'].values())
    gates.update(status=gates['allowed_candidate_status'],clean_regression=bind(paths[0]));atomic_json(ROOT/gatepath,gates)
    registry_path='reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R2.json'
    registry=json.loads((ROOT/registry_path).read_text(encoding='utf8'))
    entry=next(e for e in registry['entries'] if e['work_package']==gates['work_package'])
    old=json.loads((ROOT/entry['status_path']).read_text(encoding='utf8'))
    newstatus=str(Path(entry['status_path']).with_name('STATUS_ENGINEERING_CANDIDATE_R1.json')).replace('\\','/')
    old.update(implementation_status=gates['status'],evidence=[bind(gatepath),*[bind(p) for p in paths]],next_step='Independent external reaudit; audit remains OPEN, accepted heads and formal permissions unchanged.')
    atomic_json(ROOT/newstatus,old)
    entry.update(implementation_status=old['implementation_status'],status_path=newstatus,evidence=old['evidence']);atomic_json(ROOT/registry_path,registry)
    atomic_json(ROOT/f'reports/audits/{wp}_STAGE_CLOSURE_R1.json',dict(status=gates['status'],tested_commit=receipt['tested_commit'],gates=bind(gatepath),protected_bindings=contract['protected_bindings'],accepted_heads_unchanged=True,external_acceptance=None,next_stage=gates['next_stage'],permissions={'production':False,'shadow':False,'focus_cutover':False}))
    print(gates['status'])

if __name__=='__main__':main()
