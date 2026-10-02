"""R10 evidence seal; unified candidate delivery, never Stage acceptance."""
import argparse
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT,atomic,bind,PERMISSIONS
from scripts.prepare_v4_12_runtime_entry_r1 import BASELINE,OUT,ENTRY,ACCEPTANCE
from scripts.validate_v4_12_runtime_r1 import validate
from scripts.record_r7_stage_contract import put

def seal(junit,clean=None):
    result=validate(emit=True);raw=Path(junit).read_bytes();root=ET.fromstring(raw)
    suites=[root] if root.tag=='testsuite' else list(root.iter('testsuite'))
    counts={k:sum(int(s.get(k,'0')) for s in suites) for k in ['tests','failures','errors','skipped']}
    assert counts==dict(tests=275,failures=0,errors=0,skipped=0),counts
    atomic(OUT+'R10_TEST_RESULTS.xml',raw)
    source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if clean:
        receipt=json.loads(Path(clean).read_bytes());assert receipt['status']=='PASS' and receipt['tested_source_sha']==source
        for ref in receipt['source_manifest']:assert bind(ref['path'])==ref
        put(OUT+'R10_CLEAN_CHECKOUT_REPLAY.json',receipt)
    runtime_files=[bind(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT/'src/workbench_analysis').glob('v4_12_*.py'))]
    supplementary=[OUT+n+'.json' for n in ['V4_12_RUNTIME_R2_AUTHORITY_PARITY','V4_12_RUNTIME_TIME_DOMAIN_NEGATIVE_PARITY',
        'V4_12_SYNTHETIC_CANDIDATE_LIFECYCLE_R1_SCHEMA_VALID','V4_12_FRESH_RUNTIME_RERUN_DIGEST_EQUALITY','V4_12_RUNTIME_READBACK']]
    put(OUT+'R10_RUNTIME_HANDOFF.json',dict(status=result['candidate_status'],starting_remote_head=BASELINE,tested_source_sha=source if clean else None,
        R10A_contract_acceptance=bind(ACCEPTANCE),R10A_runtime_entry=bind(ENTRY),R10A_readback=bind(OUT+'R10A_LOCAL_READBACK.json'),
        runtime_source_manifest=runtime_files,base_candidate_manifest=bind(OUT+'V4_12_RUNTIME_MANIFEST.json'),supplemental_evidence=[bind(p) for p in supplementary],
        frozen_contracts=json.loads((ROOT/ENTRY).read_bytes())['frozen_contracts'],
        tests=dict(total=275,PASS=275,FAIL=0,ERROR=0,SKIP=0,Deselect=4),
        deselected_tests=dict(reason='Historical R9 CONTRACT_DESIGN_ONLY gates prohibit all src changes; R10 explicitly authorizes scoped runtime. Their business/source/counter/protected checks are covered independently by R10.',
            names=['test_candidate_only_scope_and_protected_heads','test_completeness_requires_authority_parity_not_file_presence','test_r6r1_and_r1_ast_vectors_preserved','test_full_contract_time_gate']),
        parity=dict(amended_business_vectors=69,R2_authority_vectors=12,sequence_steps=33,time_domain_vectors=10,quality_correction='PASS_1_0_1',DAG_and_coordinate_negative='PASS'),
        real_scoped_replay=bind(OUT+'V4_12_REAL_SCOPED_REPLAY.json'),universe_count=result['universe_count'],binding_fields=result['binding_fields'],
        performance=bind(OUT+'V4_12_RUNTIME_PERFORMANCE.json'),prior_D1_history_status='NO_ACCEPTED_PRIOR_D1_PUBLICATION',
        capability_matrix=bind(OUT+'V4_12_RUNTIME_CAPABILITY_MATRIX.json'),
        constructor_diagnostic_disposition='Initial synthetic lifecycle receipt retained as diagnostic; authoritative schema readback is V4_12_SYNTHETIC_CANDIDATE_LIFECYCLE_R1_SCHEMA_VALID.json. No real Anchor existed in the initial replay.',
        protected_artifacts=result['entry_readback']['protected_artifacts'],stage_head=result['entry_readback']['stage_head'],data_head=result['entry_readback']['data_head'],
        raw_fallback_count=0,V4_11_candidate_substitution_count=0,provider_replacement_count=0,schema_migration=False,D2_integration=False,
        formal_V4_12_head_created=False,stage_accepted=False,permissions=PERMISSIONS,clean_checkout='PASS' if clean else 'PENDING',
        external_runtime_acceptance=False,next_stage='STOP_AFTER_UNIFIED_COMMIT_PUSH_WAIT_INDEPENDENT_EXTERNAL_AUDIT'))
    print(json.dumps(dict(status=result['candidate_status'],tests=counts,clean_checkout=bool(clean))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--junit',required=True);p.add_argument('--clean');a=p.parse_args();seal(a.junit,a.clean)
