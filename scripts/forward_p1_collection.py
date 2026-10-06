"""Collection diagnostics only, after the isolation gate; no test execution."""
import json
import os
import subprocess
import sys
from scripts.full_chain_repair_io import ROOT, write
from scripts.forward_p1_fingerprint import PREFIX

if __name__ == '__main__':
    gate = json.loads((ROOT / (PREFIX+'IA09_TEST_RECEIPT.json')).read_bytes())
    if gate['exit_code'] != 0: raise ValueError('IA09_GATE_NOT_PASS')
    command = [sys.executable,'-m','pytest','--collect-only','-q',
               '--basetemp=E:/codex_tmp/test_temp/forward_p1_collection']
    env = dict(os.environ,TEMP='E:/codex_tmp/test_temp',TMP='E:/codex_tmp/test_temp',
               PYTHONIOENCODING='utf-8',PYTHONPATH='E:/codex_tmp/fep_e3_deps;.;src')
    result = subprocess.run(command,cwd=ROOT,env=env,capture_output=True)
    log = write(PREFIX+'SAFE_COLLECTION.log',result.stdout+result.stderr,raw=True)
    receipt = dict(command=command,exit_code=result.returncode,log=log,test_execution=False,
                   global_pytest_pass_claimed=False,IA05='OPEN',IA06='OPEN')
    write(PREFIX+'SAFE_COLLECTION_RECEIPT.json',receipt)
    print((result.stdout+result.stderr).decode('utf8',errors='replace')[-3500:])
