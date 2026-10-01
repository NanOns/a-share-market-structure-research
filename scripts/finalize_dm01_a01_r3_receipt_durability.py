"""Index the versioned metadata-byte repair without altering its original inputs."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
P='reports/audits/DM01_A01_R3_'
def read(path):return json.loads((ROOT/path).read_text(encoding='utf8'))
def main():
    final=read(P+'CONTINUOUS_CHAIN_POSTCHECK_R3.json')
    assert final['status']=='PASS' and final['all_nine_each_day']
    assert read(P+'DETERMINISM_R3.json')['status']=='PASS'
    assert read(P+'DETERMINISM_R3.json')['fresh_namespace_exact_component_logical_digests']
    assert read(P+'ATOMIC_FAILURE_PROBES_R3.json')['status']=='PASS'
    entry=read(P+'STAGE_ENTRY_R1.json')
    assert all(bind(r['path'])['sha256']==r['sha256'] for r in entry['protected_bindings'])
    initial=read(P+'CONTINUOUS_CHAIN_POSTCHECK_R1.json')
    assert all(bind(r['path'])==r for r in initial['candidates'])
    assert all(bind(r['path'])==r for r in read(P+'CONTINUOUS_CHAIN_POSTCHECK_R2.json')['candidates'])
    repair=read(P+'METADATA_DURABILITY_REPAIR_R2.json')
    assert bind(repair['original_capture_receipt']['path'])['sha256']==repair['original_capture_receipt']['sha256']
    assert bind(repair['exact_original_byte_archive']['path'])==repair['exact_original_byte_archive']
    repair.update(status='PASS_ENGINEERING',external_acceptance='PENDING_INDEPENDENT_EXTERNAL_REAUDIT',
        durable_contract=bind('config/dm01_incremental_builders_contract_r3_3.json'),
        durable_chain=bind(P+'CONTINUOUS_CHAIN_POSTCHECK_R3.json'),determinism=bind(P+'DETERMINISM_R3.json'),
        scope='EXACT_ORIGINAL_TDX_CAPTURE_RECEIPT_BYTES; ALL_ORIGINAL_SOURCES_AND_BUSINESS_HEADS_PRESERVED')
    atomic_json(ROOT/(P+'METADATA_DURABILITY_REPAIR_R2.json'),repair)
    handoff=read(P+'EXTERNAL_REAUDIT_HANDOFF_R3.json')
    handoff.update(chain_postcheck=bind(P+'CONTINUOUS_CHAIN_POSTCHECK_R3.json'),determinism=bind(P+'DETERMINISM_R3.json'),
        atomicity=bind(P+'ATOMIC_FAILURE_PROBES_R3.json'),metadata_durability=bind(P+'METADATA_DURABILITY_REPAIR_R2.json'),
        handoff_index_correction='R3 execution metadata binds R3 receipts; original R1/R2 handoffs preserved')
    atomic_json(ROOT/(P+'EXTERNAL_REAUDIT_HANDOFF_R3.json'),handoff)
    additions=[P+n for n in ('20260928_CANDIDATE_R3.json','20260929_CANDIDATE_R3.json','20260930_CANDIDATE_R3.json',
        'CONTINUOUS_CHAIN_POSTCHECK_R3.json','ATOMIC_FAILURE_PROBES_R3.json','DETERMINISM_R3.json',
        'METADATA_DURABILITY_REPAIR_R2.json','EXTERNAL_REAUDIT_HANDOFF_R3.json')]
    gates=read(P+'ENGINEERING_GATES_R1.json')
    gates['evidence']=[bind(r['path']) for r in gates['evidence'] if r['path'] not in additions]+[bind(p) for p in additions]
    gates['final_contract']=bind('config/dm01_incremental_builders_contract_r3_3.json')
    gates['gates']['EXACT_BYTE_METADATA_DURABILITY']='PASS_ENGINEERING'
    atomic_json(ROOT/(P+'ENGINEERING_GATES_R1.json'),gates)
    audit=dict(audit_id='DM01_R3_ACCEPTED_METADATA_GIT_REPRESENTATION',priority='P1',status='OPEN',
        scope='Accepted metadata input byte durability across original CRLF and committed LF representations',
        implementation_status='PASS_ENGINEERING_PENDING_CLEAN_AND_EXTERNAL_REAUDIT',
        external_acceptance='PENDING',acceptance_independent_from_dm01=True,formal_consumer_authorization=False,
        evidence=[bind(P+'METADATA_DURABILITY_REPAIR_R2.json')],business_heads_unchanged=True,
        next_step='Independent review of exact original-byte archive and predeclared namespace hashes')
    for version in (8,9):
        path=f'reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R{version}.json';ledger=read(path)
        ledger['entries']=[e for e in ledger['entries'] if e.get('audit_id')!=audit['audit_id']]+[audit]
        for e in ledger['entries']:
            if e.get('audit_id')=='DM01_REAL_INCREMENTAL_BUILDERS':
                e['evidence']=[bind(r['path']) if r['path'].startswith(P) else r for r in e['evidence'] if r['path'] not in additions]+[bind(p) for p in additions]
                e['latest_task']=bind('docs/evidence/source_authority/V4_A10_A12_R3_ACCEPTANCE_FORMALIZATION_AND_DM01_A01_R3_ENTRY_TASK_20261001.md')
                e['source_authority_dependency_disposition']='FULFILLED_BY_ACTUAL_INDEPENDENT_A10_A12_R3_ACCEPTANCE_AND_PHASE_A_FORMAL_REGISTRATION'
                e['remaining_external_gate']='DM01_INDEPENDENT_EXTERNAL_REAUDIT'
                e['final_contract']=gates['final_contract']
        if version==9:ledger['extends']=bind('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R8.json')
        atomic_json(ROOT/path,ledger)
    print('PASS_ENGINEERING_FINAL_R3_INDEX; EXTERNAL_REAUDIT_PENDING')
if __name__=='__main__':main()
