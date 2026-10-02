"""R9 handoff and evidence-only clean replay seal."""
import argparse
import json
import runpy
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from scripts.repair_v4_12_time_counter_r2_1 import BASELINE,OUT
from scripts.validate_v4_12_time_counter_r2_1 import validate,keep_proof
from scripts.v4_11_promotion_contract_r1 import ROOT,atomic,bind,PERMISSIONS
from scripts.record_r7_stage_contract import put
from scripts.v4_12_authority_oracle_r2 import vectors

def seal(junit,clean=None):
    r=validate(emit=True)
    actual=runpy.run_path(str(ROOT/'tests/test_v4_12_authority_r2.py'))['actual'];rows=[]
    for v in vectors():
        observed=actual(v);assert observed==v['expected'];rows.append(dict(**v,actual=observed,status='PASS'))
    put(OUT+'V4_12_R2_AUTHORITY_VECTORS_KEEP.json',dict(status='PASS_KEEP',total=12,vectors=rows,independent_expected_source=bind('scripts/v4_12_authority_oracle_r2.py')))
    raw=Path(junit).read_bytes();root=ET.fromstring(raw);suites=[root] if root.tag=='testsuite' else list(root.iter('testsuite'))
    counts={k:sum(int(s.get(k,'0')) for s in suites) for k in ['tests','failures','errors','skipped']}
    assert counts==dict(tests=156,failures=0,errors=0,skipped=0),counts
    atomic(OUT+'R9_TEST_RESULTS.xml',raw)
    source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if clean:
        receipt=json.loads(Path(clean).read_bytes());assert receipt['status']=='PASS' and receipt['tested_source_sha']==source
        for ref in receipt['source_manifest']:assert ref==bind(ref['path'])
        put(OUT+'R9_CLEAN_CHECKOUT_REPLAY.json',receipt)
    put(OUT+'V4_12_R2_1_CONTRACT_COMPLETENESS_MATRIX.json',dict(status='FROZEN_DESIGN_CANDIDATE_WITH_EXPLICIT_BLOCKS',
        checks=dict(counter_split='PASS',old_anchor_market_age_only='PASS',PENDING_evaluable_count_only='PASS',
            time_domain_compatibility='PASS_ZERO_INCOMPATIBLE_EDGES',R2_authority='PASS_KEEP',coordinate_authority='PASS_KEEP',
            parameter_values='24_VALUES_UNCHANGED',B03_missing='CORRECTED_TO_PENDING',unaffected_prior_expected='68_UNCHANGED'),
        blocked_capabilities=bind('reports/v4_12_r2/V4_12_R2_CONTRACT_COMPLETENESS_MATRIX.json'),runtime_authorized=False))
    stage=json.loads((ROOT/'data/v4/V4_STAGE_ACCEPTED_HEAD.json').read_bytes());data=json.loads((ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes())
    put(OUT+'R9_TIME_COUNTER_HANDOFF.json',dict(status=r['status'],starting_remote_head=BASELINE,tested_source_sha=source if clean else None,
        contract_files=[bind(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT/'config').glob('v4_12_*.json'))],
        tests=dict(total=156,PASS=156,FAIL=0,ERROR=0,SKIP=0,Deselect=0),amended_prior_vectors=dict(total=69,PASS=69,unaffected_expected=68,B03_missing='PENDING'),
        sequence_steps=dict(total=33,PASS=33),time_domain_vectors=dict(total=10,PASS=10),authority_vectors=dict(total=12,PASS=12),
        incompatible_edges=0,authority_keep=r['authority_keep'],protected_and_keep_proof=keep_proof(),
        stage_head=stage['accepted_stage_range'],data_head=data['accepted_trade_date'],permissions=PERMISSIONS,
        runtime_implemented=False,schema_migration=False,D2_integration=False,external_acceptance=False,
        clean_checkout='PASS' if clean else 'PENDING',next_stage='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT'))
    print(json.dumps(dict(status=r['status'],tests=counts,clean_checkout=bool(clean))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--junit',required=True);p.add_argument('--clean');a=p.parse_args();seal(a.junit,a.clean)
