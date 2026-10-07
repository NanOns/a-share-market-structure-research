"""R2 explicit stage gates, exact source bindings and honest coverage receipts."""
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
from scripts.full_chain_repair_io import ROOT,write,binding
P='reports/forward_repair_r2_20261007/'
PHASES={
 'IA09':['tests/test_forward_p1_isolation.py','tests/upgrade_m12'],
 'FORWARD':['tests/test_forward_r2.py'],
 'CLI':['tests/test_forward_r2_cli.py'],
 'AFFECTED':['tests/test_forward_p1_stock.py','tests/test_forward_p1_sector.py','tests/test_forward_p1_regression.py',
    'tests/test_full_chain_repair.py','tests/test_settlement_r1r1.py','tests/test_r20d_settlement.py',
    'tests/test_a08_governance_propagation.py','tests/fep','tests/fep_e5','tests/v4_dm01_r4','tests/v4_dm01_r4r1']}
SOURCES=['src/workbench_analysis/v4_15_forward_r2.py','scripts/v4_16_forward_r2_worker.py','scripts/_bootstrap.py',
    'tests/test_forward_r2.py','tests/test_forward_r2_cli.py','config/v4_15_forward_r2_semantics_v1.json',
    'config/dm01_standalone_bootstrap_r2_v1.json','tests/runtime_isolation.py','tests/runtime_isolation_plugin.py',
    'tests/upgrade_m12/conftest.py','tests/forward_p1_vectors.py']

def run(phase):
    index=list(PHASES).index(phase)
    if index:
        prior=json.loads((ROOT/(P+list(PHASES)[index-1]+'_TEST_RECEIPT.json')).read_bytes())
        if prior['exit_code']!=0: raise ValueError('PREDECESSOR_GATE_NOT_PASS')
    before=[binding(p) for p in SOURCES]
    started=datetime.now(timezone.utc).isoformat()
    base=Path('E:/codex_tmp/test_temp')/('forward_r2_'+phase.lower()+'_'+str(time.time_ns()))
    xml=base.with_suffix('.xml')
    command=[sys.executable,'-m','pytest',*PHASES[phase],'-q','--basetemp='+str(base),'--junitxml='+str(xml)]
    env=dict(os.environ,TEMP='E:/codex_tmp/test_temp',TMP='E:/codex_tmp/test_temp',PYTHONIOENCODING='utf8',PYTHONPATH='E:/codex_tmp/fep_e3_deps;.;src')
    result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True)
    log=write(P+phase+'_PYTEST.log',result.stdout+result.stderr,raw=True)
    tree=ET.parse(xml).getroot()
    counts={k:sum(int(s.get(k,0)) for s in tree.findall('testsuite')) for k in ('tests','failures','errors','skipped')}
    skips=[dict(node=c.get('classname','')+'::'+c.get('name',''),reason=c.find('skipped').get('message')) for c in tree.iter('testcase') if c.find('skipped') is not None]
    assert before==[binding(p) for p in SOURCES],'TEST_SOURCE_CHANGED_DURING_RUN'
    calls=Path(str(base)+'_protected_connects.json')
    receipt=dict(phase=phase,stage_contract='V4_FORWARD_REPAIR_R2_IA03_IA04_IA10',consulted_task=binding('docs/evidence/forward_repair_r2_20261007/V4_FORWARD_REPAIR_R2_IA03_IA04_IA10_TASK_R1_20261007.md'),command=command,exit_code=result.returncode,counts=counts,skipped_coverage=skips,skip_is_pass=False,log=log,source_bindings=before,started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),protected_connection_attempts=json.loads(calls.read_bytes()) if calls.exists() else [],evidence_class='ENGINEERING_ONLY',runtime_authorized=False,next_stage=(list(PHASES)[index+1] if index<3 else 'PROTECTED_STATE_AND_CANDIDATE_SEAL'))
    write(P+phase+'_TEST_RECEIPT.json',receipt)
    print(dict(phase=phase,exit_code=result.returncode,counts=counts),flush=True)
    return result.returncode
if __name__=='__main__':raise SystemExit(run(sys.argv[1]))
