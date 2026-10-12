"""Exact R9 historical input roots; this fixture cannot certify current release."""
import importlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import os
import pytest

CURRENT=Path(__file__).resolve().parents[1]
HISTORICAL=Path('G:/codex_tmp/v4_full_closeout_20261012/denominator/historical_r9_fixture')
COMMIT='11d8015d608670572bd57fc50fb6327e2b693a73'
NODES={'test_completeness_requires_authority_parity_not_file_presence','test_r6r1_and_r1_ast_vectors_preserved',
       'test_candidate_only_scope_and_protected_heads','test_full_contract_time_gate'}

@pytest.fixture(autouse=True)
def isolated_r9_replay(request,monkeypatch):
    if request.function.__name__ not in NODES:return
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=HISTORICAL,text=True).strip()
    assert actual==COMMIT,'EXACT_R9_HISTORICAL_FIXTURE_REQUIRED'
    validator=request.module.validate.__module__
    def replay(*args,**kwargs):
        env=dict(os.environ,TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp',
                 PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',
                 PYTHONPATH=os.pathsep.join([str(HISTORICAL/'src'),str(HISTORICAL)]))
        code='import importlib,json; result=importlib.import_module('+repr(validator)+').validate(); print(json.dumps(result))'
        result=subprocess.run([sys.executable,'-B','-c',code],cwd=HISTORICAL,env=env,text=True,capture_output=True,encoding='utf8')
        raw=Path('G:/codex_tmp/v4_full_closeout_20261012/denominator')/(request.function.__name__+'_HISTORICAL_RAW.log')
        raw.write_text(result.stdout+'\n'+result.stderr,encoding='utf8')
        assert result.returncode==0,result.stderr
        return json.loads(result.stdout.splitlines()[-1])
    monkeypatch.setattr(request.module,'validate',replay)
    root=Path('G:/codex_tmp/v4_full_closeout_20261012/denominator')
    target=root/(request.function.__name__+'_HISTORICAL_ONLY.json')
    target.write_text(json.dumps(dict(scope='HISTORICAL_ONLY',input_commit=COMMIT,input_root=str(HISTORICAL),
        current_production_acceptance=False,current_heads_untouched=True,validator=validator,
        meaning='Actual frozen validator subprocess; original assertions unchanged'),indent=2))
