"""Recheck two isolated fixture suites with an approved E-drive TEMP namespace."""
from pathlib import Path
import json
import os
import subprocess
import sys
from write_reports import atomic,EVIDENCE,ROOT

temp_root=Path('E:/codex_tmp/test_temp')
temp_root.mkdir(parents=True,exist_ok=True)
env=os.environ.copy()
env.update(TEMP=str(temp_root),TMP=str(temp_root),PYTHONIOENCODING='utf-8')
args=[sys.executable,'-m','pytest','-q','tests/test_r20r1r1_maturity.py','tests/test_r20r1r2_dm01.py',
      '--basetemp',str(temp_root/'full_scope_namespace_recheck_20261006'),
      '--junitxml='+str((EVIDENCE/'pytest_namespace_recheck.xml').relative_to(ROOT))]
atomic(EVIDENCE/'namespace_recheck_selection.json',(json.dumps(dict(command=args,child_environment_overrides={k:env[k] for k in ('TEMP','TMP','PYTHONIOENCODING')},reason='Initial 68 namespace rejections occurred because E-drive --basetemp was outside tempfile.gettempdir() and fixed engineering-fixture roots; recheck aligns both while keeping all writes on E.'),ensure_ascii=False,indent=2)+'\n').encode('utf8'))
tmp=EVIDENCE/'pytest_namespace_recheck.log.tmp'
with tmp.open('w',encoding='utf8') as log:
    result=subprocess.run(args,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
os.replace(tmp,EVIDENCE/'pytest_namespace_recheck.log')
print('NAMESPACE_RECHECK_EXIT='+str(result.returncode))
raise SystemExit(result.returncode)
