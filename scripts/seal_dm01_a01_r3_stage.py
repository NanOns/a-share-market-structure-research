"""Seal exact clean engineering receipts; formal producer acceptance remains separate."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.enter_source_authority_remediation_r2 import bind
from scripts.build_v4_08_r2_membership_evidence import atomic_bytes,atomic_json
P='reports/audits/DM01_A01_R3_'
def read(path):return json.loads((ROOT/path).read_text(encoding='utf8'))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--clean-root',required=True);args=parser.parse_args();clean=Path(args.clean_root)
    receipts=[P+n for n in ('CLEAN_CHECKOUT_R1.json','CLEAN_REGRESSION_R1.xml','CLEAN_REGRESSION_R1.log','NO_SYMBOL_SCAN_R1.json')]
    proof=json.loads((clean/receipts[0]).read_text(encoding='utf8'))
    assert proof['status']=='PASS' and proof['tested_commit']==subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    entry=read(P+'STAGE_ENTRY_R1.json')
    assert all(bind(r['path'])['sha256']==r['sha256'] for r in entry['protected_bindings'])
    assert hashlib.sha256((clean/receipts[1]).read_bytes()).hexdigest()==proof['junit_sha256']
    for path in receipts:atomic_bytes(ROOT/path,(clean/path).read_bytes())
    dependency=read(P+'SOURCE_DEPENDENCY_DURABILITY_R1.json')
    assert all(bind(r['path'])==r for r in dependency['missing_from_previous_git_checkout'])
    dependency.update(clean_regression=bind(receipts[0]),tested_commit=proof['tested_commit'])
    atomic_json(ROOT/(P+'SOURCE_DEPENDENCY_DURABILITY_R1.json'),dependency)
    gatepath=P+'ENGINEERING_GATES_R1.json';gates=read(gatepath)
    assert read(P+'CONTINUOUS_CHAIN_POSTCHECK_R2.json')['status']=='PASS'
    assert read(P+'METADATA_DURABILITY_REPAIR_R1.json')['status']=='PASS_ENGINEERING'
    for key,value in gates['gates'].items():
        if value=='PENDING_CLEAN_DETACHED':gates['gates'][key]='PASS_ENGINEERING'
    assert all(v in ('PASS_ENGINEERING','PENDING_INDEPENDENT_EXTERNAL_AUDIT') for v in gates['gates'].values())
    gates.update(status='READY_FOR_EXTERNAL_REAUDIT',clean_regression=bind(receipts[0]))
    if not any(r['path']==P+'SOURCE_DEPENDENCY_DURABILITY_R1.json' for r in gates['evidence']):
        gates['evidence'].append(bind(P+'SOURCE_DEPENDENCY_DURABILITY_R1.json'))
    # The stronger determinism check may have completed after the initial engineering index was drafted.
    gates['evidence']=[bind(r['path']) for r in gates['evidence']]
    handoff=read(P+'EXTERNAL_REAUDIT_HANDOFF_R2.json');handoff.update(clean_regression=bind(receipts[0]),tested_commit=proof['tested_commit'],
        chain_postcheck=bind(P+'CONTINUOUS_CHAIN_POSTCHECK_R2.json'),determinism=bind(P+'DETERMINISM_R2.json'),
        atomicity=bind(P+'ATOMIC_FAILURE_PROBES_R2.json'),metadata_durability=bind(P+'METADATA_DURABILITY_REPAIR_R1.json'),
        contract=bind('config/dm01_incremental_builders_contract_r3_2.json'))
    atomic_json(ROOT/(P+'EXTERNAL_REAUDIT_HANDOFF_R2.json'),handoff)
    gates['evidence']=[bind(r['path']) for r in gates['evidence']]
    atomic_json(ROOT/gatepath,gates)
    atomic_json(ROOT/(P+'STAGE_CLOSURE_R1.json'),dict(status='READY_FOR_EXTERNAL_REAUDIT',stage_completed=True,
        phase_A_acceptance_formalization='PASS',phase_B_continuous_chain='READY_FOR_EXTERNAL_REAUDIT',
        external_acceptance='PENDING_DM01_EXTERNAL_REAUDIT',tested_commit=proof['tested_commit'],gates=bind(gatepath),
        evidence_bindings=[bind(p) for p in receipts],final_handoff=bind(P+'EXTERNAL_REAUDIT_HANDOFF_R2.json'),protected_bindings=entry['protected_bindings'],
        accepted_business_heads_unchanged=True,data_head_moved=False,stage_head_moved=False,
        permissions=dict(production=False,shadow=False,focus_cutover=False),next_stage='INDEPENDENT_EXTERNAL_REAUDIT_ONLY'))
    # Append-only registry versions were introduced by this work package; older versions remain untouched.
    for version in (8,9):
        path=f'reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R{version}.json';ledger=read(path)
        for e in ledger['entries']:
            if e.get('audit_id')=='DM01_REAL_INCREMENTAL_BUILDERS':
                e['evidence']=[bind(r['path']) if r.get('path','').startswith(P) else r for r in e['evidence']]
                e['clean_regression']=bind(receipts[0])
                e['final_handoff']=bind(P+'EXTERNAL_REAUDIT_HANDOFF_R2.json')
            if e.get('audit_id')=='DM01_R3_ACCEPTED_METADATA_GIT_REPRESENTATION':
                e['clean_regression']=bind(receipts[0])
                e['implementation_status']='PASS_ENGINEERING_PENDING_EXTERNAL_REAUDIT'
                e['additional_scope']='Exact previously untracked accepted source artifact publication'
                e['evidence'].append(bind(P+'SOURCE_DEPENDENCY_DURABILITY_R1.json'))
        if version==9:ledger['extends']=bind('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R8.json')
        atomic_json(ROOT/path,ledger)
    print('READY_FOR_EXTERNAL_REAUDIT')
if __name__=='__main__':main()
