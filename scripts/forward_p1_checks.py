"""Bounded phase runs and atomic, reviewable test receipts."""
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from scripts.full_chain_repair_io import ROOT, write, binding
from scripts.forward_p1_fingerprint import PREFIX

PHASES = {
    'IA09': ['tests/test_forward_p1_isolation.py','tests/upgrade_m12'],
    'IA01': ['tests/test_forward_p1_stock.py'],
    'IA02': ['tests/test_forward_p1_sector.py'],
    'AFFECTED': ['tests/test_forward_p1_regression.py','tests/test_full_chain_repair.py','tests/test_settlement_r1r1.py',
                 'tests/test_r20d_settlement.py','tests/test_a08_governance_propagation.py',
                 'tests/fep','tests/fep_e5'],
}

def run(phase):
    if phase != 'IA09':
        import json
        receipt = json.loads((ROOT / (PREFIX+'IA09_TEST_RECEIPT.json')).read_bytes())
        if receipt['exit_code'] != 0: raise ValueError('IA09_GATE_NOT_PASS')
    predecessor = {'IA02':'IA01','AFFECTED':'IA02'}.get(phase)
    if predecessor:
        import json
        if json.loads((ROOT/(PREFIX+predecessor+'_TEST_RECEIPT.json')).read_bytes())['exit_code'] != 0:
            raise ValueError('PREDECESSOR_GATE_NOT_PASS')
    started = datetime.now(timezone.utc).isoformat()
    source_paths = ['conftest.py','tests/runtime_isolation_plugin.py','src/workbench_analysis/v4_15_forward_p1.py','scripts/v4_16_forward_p1_worker.py',
                    'tests/runtime_isolation.py','tests/upgrade_m12/conftest.py','tests/forward_p1_vectors.py',
                    'tests/test_forward_p1_isolation.py','tests/test_forward_p1_stock.py',
                    'tests/test_forward_p1_sector.py','tests/test_forward_p1_regression.py']
    before = [binding(p) for p in source_paths]
    base = Path('E:/codex_tmp/test_temp') / ('forward_p1_'+phase.lower()+'_'+str(time.time_ns()))
    xml = base.with_suffix('.xml')
    command = [sys.executable,'-m','pytest',*PHASES[phase],'-q','--basetemp='+str(base),'--junitxml='+str(xml)]
    env = dict(os.environ, TEMP='E:/codex_tmp/test_temp', TMP='E:/codex_tmp/test_temp',
               PYTHONIOENCODING='utf-8', PYTHONPATH='E:/codex_tmp/fep_e3_deps;.;src')
    result = subprocess.run(command,cwd=ROOT,env=env,capture_output=True)
    protected_calls_path = Path(str(base)+'_protected_connects.json')
    if protected_calls_path.exists():
        import json
        protected_calls = json.loads(protected_calls_path.read_bytes())
    else:
        protected_calls = []
    log = write(PREFIX+phase+'_PYTEST.log',result.stdout+result.stderr,raw=True)
    suites = ET.parse(xml).getroot()
    counts = {k:sum(int(s.get(k,0)) for s in suites.findall('testsuite')) for k in ('tests','failures','errors','skipped')}
    skipped = [dict(node=case.get('classname','')+'::'+case.get('name',''),reason=case.find('skipped').get('message'))
               for case in suites.iter('testcase') if case.find('skipped') is not None]
    if before != [binding(p) for p in source_paths]: raise ValueError('TEST_SOURCE_CHANGED_DURING_RUN')
    receipt = dict(phase=phase, command=command, exit_code=result.returncode, counts=counts, log=log,
                   source_bindings=before,started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),
                   protected_database_connection_attempts=protected_calls,
                   skipped_coverage=skipped,stage_contract='V4_FORWARD_P1_REPAIR_R1_IA09_IA01_IA02',
                   next_stage={'IA09':'IA01','IA01':'IA02','IA02':'AFFECTED','AFFECTED':'PROTECTED_STATE_AND_INDEPENDENT_EXTERNAL_AUDIT'}[phase],
                   evidence_class='ENGINEERING_REGRESSION_ONLY', runtime_authorization=False)
    write(PREFIX+phase+'_TEST_RECEIPT.json',receipt)
    print({k:receipt[k] for k in ('phase','exit_code','counts','log')})
    return result.returncode

if __name__ == '__main__': sys.exit(run(sys.argv[1]))
