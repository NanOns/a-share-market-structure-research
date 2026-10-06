"""Repeat inherited suites, retain known debts, publish atomic execution receipts."""
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from scripts.full_chain_repair_io import ROOT,PREFIX,write,binding

def run(name,command,env,known=()):
    xml=ROOT/(PREFIX+name+'.xml.working')
    command=[sys.executable,*command,'--junitxml='+str(xml)]
    proc=subprocess.run(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    write(PREFIX+name+'.log',proc.stdout,raw=True)
    raw=xml.read_bytes();write(PREFIX+name+'.xml',raw,raw=True);xml.unlink()
    cases=ET.fromstring(raw).findall('.//testcase');failed=[]
    skipped=0
    for case in cases:
        node=case.attrib['classname']+'::'+case.attrib['name']
        if case.find('failure') is not None or case.find('error') is not None:failed.append(node)
        if case.find('skipped') is not None:skipped+=1
    summary=dict(command=command,exit_code=proc.returncode,passed=len(cases)-len(failed)-skipped,skipped=skipped,failed_nodes=sorted(failed),
        known_debt_nodes=sorted(known),introduced_failure_nodes=sorted(set(failed)-set(known)),
        removed_debt_nodes=sorted(set(known)-set(failed)),xml=binding(PREFIX+name+'.xml'),log=binding(PREFIX+name+'.log'))
    write(PREFIX+name.upper()+'_SUMMARY.json',summary)
    print(json.dumps(dict(suite=name,passed=summary['passed'],skipped=skipped,failed=len(failed),introduced=summary['introduced_failure_nodes']),ensure_ascii=True),flush=True)
    return summary

def main():
    env=os.environ.copy();env.update(PYTHONPATH='E:/codex_tmp/fep_e3_deps;.;src',TEMP='E:/codex_tmp/test_temp',TMP='E:/codex_tmp/test_temp',
        FEP_E1_TEST_DSN='host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh',
        FEP_E5_TEST_DSN='host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh',
        WORKBENCH_PG_DSN='host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh',
        FEP_E5_CANONICAL_TEST_ENABLE='1',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2')
    env['FEP_TEST_RECEIPT_ROOT']=PREFIX+'inherited_test_receipts'
    result=run('targeted',['-B','-m','pytest','tests/test_full_chain_repair.py','tests/test_full_chain_fep_db.py','-q','--tb=short'],env)
    previous=json.loads((ROOT/'reports/fep_e5_r1r1c/TARGETED_SUMMARY.json').read_bytes())
    command=[c for c in previous['command'][1:] if not c.startswith(('--basetemp=','--junitxml='))]
    # The inherited canonical fixtures keep their original B ports for provenance.
    target=run('affected_stage',command,env)
    previous=json.loads((ROOT/'reports/fep_e5_r1r1c/SCOPED_REGRESSION_SUMMARY.json').read_bytes())
    command=[c for c in previous['command'][1:] if not c.startswith(('--basetemp=','--junitxml='))]
    scoped=run('scoped_regression',command,env,previous['failed_nodes'])
    cross=run('cross_stage',['-B','-m','pytest','tests/v4_09','tests/v4_dm01_r4r2','tests/test_r20a_current.py','tests/test_r20c_runtime.py','tests/test_r20d_settlement.py','tests/test_r20e_persisted.py','-q','--tb=short'],env,previous['failed_nodes'])
    return not any(s['introduced_failure_nodes'] for s in (result,target,scoped,cross))

if __name__=='__main__':sys.exit(0 if main() else 1)
