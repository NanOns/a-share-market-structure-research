"""Bind R7 code/design/evidence and stop handoff; no accepted head mutation."""
import argparse
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT, atomic, bind, PERMISSIONS
from scripts.record_r7_stage_contract import BASELINE, put, protected_proof
from scripts.validate_v4_12_contract_freeze_r1 import validate

SOURCES=['AGENTS.md','scripts/prepare_v4_11_promotion_r1.py','scripts/record_r7_stage_contract.py',
         'scripts/freeze_v4_12_contracts_r1.py','scripts/v4_12_independent_vector_oracle_r1.py',
         'scripts/validate_v4_12_contract_freeze_r1.py','scripts/verify_v4_r7_clean_checkout.py',
         'scripts/seal_v4_r7_contract_handoff.py','tests/test_r6r1_governance_cleanup.py','tests/test_v4_12_contract_freeze_r1.py']

def statistics(path):
    suite=ET.parse(path).getroot()
    cases=suite.findall('.//testcase')
    return dict(total=len(cases),passed=sum(not (r.find('failure') is not None or r.find('error') is not None or r.find('skipped') is not None) for r in cases),
        failed=sum(r.find('failure') is not None for r in cases),errors=sum(r.find('error') is not None for r in cases),
        skipped=sum(r.find('skipped') is not None for r in cases),deselected=0)

def seal(test_xml, clean_receipt=None):
    result=validate();stats=statistics(test_xml)
    assert stats['failed']==stats['errors']==stats['skipped']==0
    test_dest='reports/v4_12_r1/R7_TARGETED_TESTS.xml'
    atomic(test_dest,Path(test_xml).read_bytes())
    clean=None
    if clean_receipt:
        raw=Path(clean_receipt).read_bytes();clean=json.loads(raw);assert clean['status']=='PASS'
        for field in ['clean_before','clean_after','agents_exact_baseline']:assert clean[field]
        commit=clean['tested_source_commit']
        # Receipt is about the source/design commit, which must remain exactly
        # equal in this final evidence-only sealing step.
        for path in SOURCES+[r['path'] for r in result['contracts']]:
            assert subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)==(ROOT/path).read_bytes(),path
        atomic('reports/v4_12_r1/R7_CLEAN_DETACHED_REPLAY.json',raw)
    reports=[p.as_posix() for folder in ['reports/next_round_r6r1','reports/v4_12_r1']
             for p in Path(folder).glob('*') if p.is_file() and p.name not in ['R7_SOURCE_EVIDENCE_MANIFEST.json','R7_FINAL_STOP_HANDOFF.json']]
    docs=[p.as_posix() for p in Path('docs/evidence/next_round_v4_12').glob('*') if p.is_file()]
    put('reports/v4_12_r1/R7_SOURCE_EVIDENCE_MANIFEST.json',dict(contract_id='V4_R7_SOURCE_EVIDENCE_MANIFEST_V1',
        starting_remote_head=BASELINE,sources=[bind(p) for p in SOURCES],contracts=result['contracts'],
        evidence=[bind(p) for p in sorted(reports)],documents=[bind(p) for p in sorted(docs)],protected_artifacts=protected_proof()))
    status=dict(contract_id='V4_R7_STOP_HANDOFF_V1',starting_remote_head=BASELINE,
        governance='R6R1_GOVERNANCE_REPLAY_CLEANUP_CANDIDATE_READY_FOR_EXTERNAL_AUDIT',
        contract_freeze=result['status'],G01='PASS_EXACT_BASELINE_RESTORED',G02='PASS_REPO_FIRST_EXPLICIT_BOOTSTRAP_FAIL_CLOSED',
        protected_artifacts=protected_proof(),tests=stats,test_report=bind(test_dest),
        clean_checkout='PASS' if clean else 'PENDING_SOURCE_COMMIT_DETACHED_REPLAY',
        clean_receipt=bind('reports/v4_12_r1/R7_CLEAN_DETACHED_REPLAY.json') if clean else None,
        tested_source_commit=clean['tested_source_commit'] if clean else None,
        manifest=bind('reports/v4_12_r1/R7_SOURCE_EVIDENCE_MANIFEST.json'),
        contract_config_files=[r['path'] for r in result['contracts']],registries=result['registries'],
        parameter_literal_audit=result['literal_audit_summary'],dag_edge_audit='PASS',independent_oracle=result['independent_vector_oracle'],
        completeness_matrix='reports/v4_12_r1/V4_12_R1_CONTRACT_COMPLETENESS_MATRIX.json',blocked_capabilities=result['blocked_capabilities'],
        scope_proof=result['scope_proof'],permissions=PERMISSIONS,
        full_repository_runtime_pass_claim=False,external_acceptance_claim=False,
        historical_data_stage_binding='Unchanged Data Head retains its accepted historical V4-10 hash; read-only chain preflight uses exact R6 parent archive; current stage checked separately by post-promotion validator',
        next_stage='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT; NO_V4_12_RUNTIME_AUTHORIZATION')
    put('reports/v4_12_r1/R7_FINAL_STOP_HANDOFF.json',status)
    print(json.dumps({k:status[k] for k in ['governance','contract_freeze','tests','clean_checkout']}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--test-xml',required=True);p.add_argument('--clean-receipt');args=p.parse_args()
    seal(args.test_xml,args.clean_receipt)
