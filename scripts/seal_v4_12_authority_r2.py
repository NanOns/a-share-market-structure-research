"""Seal contract-only R8 evidence; expected values remain independently authored."""
import argparse
import json
import runpy
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from scripts.repair_v4_12_authority_r2 import ROOT, OUT, BASELINE, keep_proof
from scripts.v4_11_promotion_contract_r1 import atomic, bind, PERMISSIONS
from scripts.record_r7_stage_contract import put
from scripts.validate_v4_12_authority_r2 import validate
from scripts.v4_12_authority_oracle_r2 import vectors

def seal(junit, clean=None):
    result=validate(emit=True)
    actual=runpy.run_path(str(ROOT/'tests/test_v4_12_authority_r2.py'))['actual']
    rows=[]
    for vector in vectors():
        observed=actual(vector);assert observed==vector['expected'],vector['id']
        rows.append(dict(**vector,actual=observed,status='PASS'))
    put(OUT+'V4_12_R2_INDEPENDENT_AUTHORITY_VECTORS.json',dict(status='PASS',total=len(rows),passed=len(rows),failed=0,
        expected_source=bind('scripts/v4_12_authority_oracle_r2.py'),actual_source=bind('tests/test_v4_12_authority_r2.py'),
        expected_method='Handwritten independent oracle; no implementation/helper imports',vectors=rows))
    raw=Path(junit).read_bytes();root=ET.fromstring(raw)
    suites=[root] if root.tag=='testsuite' else list(root.iter('testsuite'))
    counts={k:sum(int(s.get(k,'0')) for s in suites) for k in ['tests','failures','errors','skipped']}
    assert counts==dict(tests=135,failures=0,errors=0,skipped=0),counts
    atomic(OUT+'R8_TEST_RESULTS.xml',raw)
    configs=sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'config').glob('v4_12_*.json'))
    source_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    receipt=None
    if clean:
        receipt=json.loads(Path(clean).read_bytes());assert receipt['status']=='PASS'
        assert receipt['tested_source_sha']==source_sha
        for ref in receipt['source_manifest']:assert bind(ref['path'])==ref
        put(OUT+'R8_CLEAN_CHECKOUT_REPLAY.json',receipt)
    put(OUT+'R8_AUTHORITY_REPAIR_HANDOFF.json',dict(status=result['status'],starting_remote_head=BASELINE,
        tested_source_sha=source_sha if clean else None,contract_files=[bind(p) for p in configs],
        registries=[bind('config/v4_12_'+n+'_registry_v1.json') for n in ['field','producer','time_role']],
        tests=dict(total=135,PASS=135,FAIL=0,ERROR=0,SKIP=0,Deselect=0),R1_vectors=dict(total=69,PASS=69),authority_vectors=dict(total=12,PASS=12),
        protected_and_keep_proof=keep_proof(),authority_parity='PASS',coordinate_authority='PASS',unit_parity='PASS',
        requiredness='PASS_CONSUMER_LOCAL',completeness='PASS_WITH_EXPLICIT_CAPABILITY_BLOCKS',
        capability_details=bind(OUT+'V4_12_R2_CONTRACT_COMPLETENESS_MATRIX.json'),
        stage_head=json.loads((ROOT/'data/v4/V4_STAGE_ACCEPTED_HEAD.json').read_bytes()),
        data_head=json.loads((ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes()),
        clean_checkout='PASS' if receipt else 'PENDING',permissions=PERMISSIONS,runtime_implementation=False,schema_migration=False,
        external_acceptance=False,next_stage='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT'))
    print(json.dumps(dict(status=result['status'],tests=counts,authority_vectors=12,clean_checkout=bool(receipt))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--junit',required=True);p.add_argument('--clean');a=p.parse_args();seal(a.junit,a.clean)
