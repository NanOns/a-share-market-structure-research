"""Record actual pending-owner rejection, scan findings and invariant proofs."""
import ast
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from scripts.scan_source_authority_governance_r1 import run
from workbench_analysis.source_authority_governance_r1 import evaluate_consumer_gate
from workbench_analysis.source_authority_accepted_owners_v1 import load_registered_owners,ERROR,REGISTRY_PATH,HEAD_PATH
from workbench_analysis.dm01_source_boundary_r2 import require_external_a12_owner_for_final_candidate

def read(path):return json.loads((ROOT/path).read_text(encoding='utf8'))

def main():
    entry=read('reports/audits/A10_R2_STAGE_ENTRY_R1.json')
    assert all(bind(b['path'])['sha256']==b['sha256'] for b in entry['protected_bindings'])
    registry=load_registered_owners(ROOT);assert registry['owners']==[]
    contract=read('config/source_authority_governance_r2.json')
    assert bind(contract['runtime']['path'])['sha256']==contract['runtime']['sha256']
    assert bind(contract['owner_runtime']['path'])['sha256']==contract['owner_runtime']['sha256']
    phase0=read(entry['phase0_evidence']['path']);assert phase0['phase0_status']=='FULL_PASS'
    target=read('data/v4/V4_09_ACCEPTED_HEAD.json')['artifact']['trade_date']
    pending={}
    for rule in contract['field_rules']:
        if rule['role'] in ('CORE_AUTHORITY','FIELD_AUTHORITY'):
            result=evaluate_consumer_gate(rule,project_root=ROOT,consumer_contract_id=rule['allowed_consumers'][0],
                availability='AVAILABLE',target_trade_date=target,core_value='PRESERVED',supplemental_value='UNACCEPTED',required=True)
            assert result['status']==ERROR and result['core_value']=='PRESERVED'
            pending[rule['field_id']]=result
    a12=read('config/v4_02_status_st_authority_r1.json')
    assert a12['external_acceptance'] is None and a12['formal_consumer_authorization'] is False
    try:require_external_a12_owner_for_final_candidate(ROOT,bind('config/v4_02_status_st_authority_r1.json'),target_trade_date=target)
    except ValueError as exc:private_gate=str(exc)
    else:raise AssertionError('Pending A12 must never authorize DM01')
    # All temporal helpers retain exactly the independently audited implementation AST.
    path='src/workbench_analysis/source_authority_governance_r1.py'
    old=ast.parse(subprocess.check_output(['git','show','1655f84d1a47faca43c281d66e7704f2fa56b1b8:'+path],cwd=ROOT).decode('utf8'))
    new=ast.parse((ROOT/path).read_text(encoding='utf8'))
    functions=lambda tree:{n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('timestamp','validate_temporal_lineage','validate_availability','validate_role_contract')}
    assert functions(old)==functions(new)
    scan=run(ROOT);assert scan['status']=='PASS_SCAN_COMPLETE_FINDINGS_OPEN'
    for field in ('TRADING_STATUS','ISST'):
        assert any(f['path']=='config/source_authority_governance_r2.json' and f['category']=='FIELD_AUTHORITY_WITHOUT_ACCEPTED_OWNER_BINDING'
            and f['confidence']=='PENDING_OWNER' and field in f['evidence'] for f in scan['findings'])
    scanpath='reports/audits/V4_SOURCE_AUTHORITY_GOVERNANCE_SCAN_R2.json';atomic_json(ROOT/scanpath,scan)
    targeted='reports/audits/A10_R2_TARGETED_REGRESSION_R1.xml'
    nodes=list(ET.parse(ROOT/targeted).getroot().iter('testsuite'))
    summary={k:sum(int(n.attrib.get(k,0)) for n in nodes) for k in ['tests','failures','errors','skipped']}
    assert summary['tests'] and summary['failures']==summary['errors']==summary['skipped']==0
    evidencepath='reports/audits/A10_R2_OWNER_GATE_AND_PENDING_SOURCE_EVIDENCE_R1.json'
    atomic_json(ROOT/evidencepath,dict(status='PASS_ENGINEERING_PENDING_EXTERNAL_REAUDIT',
        registry=bind(REGISTRY_PATH),global_authority_head=bind(HEAD_PATH),actual_accepted_owner_count=0,
        actual_pending_field_gates=pending,dm01_private_gate=private_gate,
        historical_helpers_ast_unchanged=True,targeted_summary=summary,targeted_tests=bind(targeted),
        tests=bind('tests/v4_a10_r2/test_owner_acceptance.py'),scanner=bind(scanpath),
        positive_authorization_scope='SYNTHETIC_FIXTURE_ONLY_NO_REAL_OWNER_ACCEPTANCE',
        all_nine_final_execution_performed=False,accepted_business_heads_unchanged=True,
        external_acceptance=None,permissions=dict(production=False,shadow=False,focus_cutover=False)))
    labels=['registry_schema','owner_hash','external_acceptance','formal_authorization','scope',
        'supplemental_promotion','actual_a12_pending','synthetic_positive','dm01_consistency',
        'historical_mode_preserved','scanner','accepted_heads_unchanged','clean_detached','external_reaudit']
    atomic_json(ROOT/'reports/audits/A10_R2_ENGINEERING_GATES_R1.json',dict(
        status='PENDING_CLEAN_DETACHED',allowed_candidate_status='A10_R2_OWNER_ACCEPTANCE_BINDING_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',
        gates={f'A10R2-G{i:02d}': 'PENDING_CLEAN_DETACHED' if i==13 else 'PENDING_INDEPENDENT_EXTERNAL_AUDIT' if i==14 else 'PASS_ENGINEERING' for i in range(1,15)},
        gate_labels={f'A10R2-G{i:02d}':label for i,label in enumerate(labels,1)},evidence=bind(evidencepath),
        next_stage='Independent A10 R2 external reaudit; A12 R2 owner semantics require their own task; DM01 final all-nine remains gated by both acceptances'))
    print(json.dumps(dict(status='PASS_ENGINEERING',accepted_owner_count=0,targeted_summary=summary,scan_findings=len(scan['findings']))))

if __name__=='__main__':main()
