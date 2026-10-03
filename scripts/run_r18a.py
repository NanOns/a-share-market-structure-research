"""Execute all frozen vectors; expectations stay outside runtime evaluators."""
import json,sys
from pathlib import Path
from scripts.prepare_r17_governance import ROOT,put,bind
sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.v4_14_authority import ReplayAuthority
from workbench_analysis.v4_14_replay_runtime import ReplayRuntime
from workbench_analysis.v4_14_replay_io import digest,publish
def run(output='reports/r18a/r3'):
    a=ReplayAuthority(ROOT);runtime=ReplayRuntime(a);book=a.config['machine_vectors'];rows=[]
    for v in book['vectors']:
        actual=runtime.evaluate_case(v['dimension'],v['input'])
        rows.append(dict(id=v['id'],dimension=v['dimension'],input_digest=digest(v['input']),actual=actual,expected=v['expected'],passed=actual==v['expected'],evidence_class='ENGINEERING_SYNTHETIC'))
    gate=dict(status='PASS_LOCAL' if all(r['passed'] for r in rows) else 'FAIL',R18A_V4_14_RUNTIME_HARNESS='PASS_LOCAL' if all(r['passed'] for r in rows) else 'FAIL',V4_14_SYNTHETIC_VECTOR_RUNTIME='PASS_LOCAL' if all(r['passed'] for r in rows) else 'FAIL',case_count=len(rows),dimension_count=len({r['dimension'] for r in rows}),rows=rows,authority=a.bindings(),contract_package_digest=a.package_digest,V4_14_RUNTIME_CANDIDATE='IMPLEMENTED_NOT_YET_EXTERNALLY_ACCEPTED',NEXT='R18B_CROSS_PROCESS_FULL_DAG_REPLAY')
    publish(ROOT,output+'/synthetic_vector_runtime.json',gate)
    if gate['status']!='PASS_LOCAL':raise AssertionError([r for r in rows if not r['passed']])
    return gate
if __name__=='__main__':print(json.dumps({k:v for k,v in run().items() if k!='rows' and k!='authority'}))
