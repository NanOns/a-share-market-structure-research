"""Clean processes exercise the formal DM01 direct/module launch contract."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from scripts.full_chain_repair_io import ROOT
from tests.runtime_isolation import DISPOSABLE_BASE

def child_vector(number,root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    env={k:os.environ[k] for k in ('SystemRoot','WINDIR','PATH') if k in os.environ}
    env.update(TEMP=str(DISPOSABLE_BASE),TMP=str(DISPOSABLE_BASE),PYTHONNOUSERSITE='1',PYTHONPATH='',PYTHONIOENCODING='utf8')
    command=[sys.executable,'-I','-B',str(ROOT/'scripts/_bootstrap.py')]
    cwd=root
    if number in (1,2,3):command+=['--help']
    elif number==4:command+=['--','--target-date','2026-10-08']
    elif number==5:command+=['--preflight','--target-date','2026-10-07']
    elif number==6:command+=['--preflight','--target-date','2026-10-08']
    elif number==7:command+=['--module','scripts.verify_dm01_r4r1_runtime','--fixture-root',str(root/'fixture')]
    else:command+=['--preflight','--target-date','2026-10-08']
    completed=subprocess.run(command,cwd=cwd,env=env,capture_output=True,timeout=180)
    stdout=completed.stdout.decode('utf8',errors='replace');stderr=completed.stderr.decode('utf8',errors='replace')
    result=None
    if number<=3:
        assert completed.returncode==0 and '--module' in stdout
    else:
        assert completed.returncode==(2 if number==5 else 0),(stdout,stderr)
        result=json.loads(stdout.strip().splitlines()[-1])
        if number==5:assert result['status']=='BLOCKED' and result['source_requests']==0
        elif number==7:assert result['status']=='ENGINEERING_FIXTURE_EXECUTED' and result['real_forward_evidence'] is False
        else:assert result['status']=='WAIT_MARKET_CLOSE' and result['source_requests']==0
    module_result=None
    if number==8:
        other=[sys.executable,'-s','-B','-m','scripts._bootstrap','--preflight','--target-date','2026-10-08']
        proc=subprocess.run(other,cwd=ROOT,env=env,capture_output=True,timeout=60)
        assert proc.returncode==0,proc.stderr
        module_result=json.loads(proc.stdout.decode().strip().splitlines()[-1]);assert module_result==result
    return dict(id=f'CLI-{number:02}',command=command,cwd=str(cwd),PYTHONPATH='',user_site_disabled=True,exit_code=completed.returncode,stdout=stdout,stderr=stderr,result=result,module_launcher_result=module_result,tdx_write_count=0)

@pytest.mark.parametrize('number',range(1,9))
def test_clean_child_vector(number,tmp_path):child_vector(number,tmp_path)


def test_clean_direct_r4_fixture_and_legacy_module_help(tmp_path):
    env={k:os.environ[k] for k in ('SystemRoot','WINDIR','PATH') if k in os.environ}
    env.update(PYTHONPATH='',PYTHONNOUSERSITE='1',TEMP=str(DISPOSABLE_BASE),TMP=str(DISPOSABLE_BASE))
    base=[sys.executable,'-I','-B',str(ROOT/'scripts/_bootstrap.py')]
    result=subprocess.run(base+['--module','scripts.verify_dm01_r4_runtime','--fixture-root',str(tmp_path/'r4')],cwd=tmp_path,env=env,capture_output=True,timeout=180)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['status']=='ENGINEERING_FIXTURE_EXECUTED'
    for module in ('scripts.run_v4_dm01_daily_increment','scripts.build_dm01_r4_tdx_delta','scripts.freeze_v4_dm01_daily_sources'):
        result=subprocess.run(base+['--module',module,'--','--help'],cwd=tmp_path,env=env,capture_output=True,timeout=60)
        assert result.returncode==0,result.stderr
        assert b'--target-date' in result.stdout

def test_bootstrap_fixture_rejects_tdx_before_creation(tmp_path):
    result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/_bootstrap.py'),'--module','scripts.verify_dm01_r4_runtime','--fixture-root','D:/new_tdx'],cwd=tmp_path,capture_output=True,timeout=30)
    assert result.returncode!=0 and b'PROTECTED_ROOT' in result.stderr
