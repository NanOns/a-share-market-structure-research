"""Explicit stage/FEP rerun; excludes legacy workstation UI recovery fixtures."""
from pathlib import Path
import json
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
directories=sorted(p for p in (ROOT/'tests').iterdir() if p.is_dir() and (p.name.startswith('v4_') or p.name.startswith('fep')))
files=sorted(p for p in (ROOT/'tests').glob('test_*.py') if p.name.startswith(('test_v4_', 'test_r17', 'test_r18', 'test_r19', 'test_r20', 'test_r21', 'test_r22', 'test_r23', 'test_r24', 'test_r25', 'test_full_chain_', 'test_settlement_', 'test_a08_', 'test_pre16_')))
args=[sys.executable,'-m','pytest','-q',*[str(p.relative_to(ROOT)) for p in directories+files],
      '--basetemp','tmp/full_scope_audit_stage_tests_20261006','--junitxml='+str((OUT/'pytest_stages.xml').relative_to(ROOT))]
raw=(json.dumps(dict(command=args,excluded_scope='Legacy upgrade/phase/r0-r4 and unselected root tests; default global collection is independently recorded as failing; partial global rerun was stopped upon discovering real-workspace browser startup recovery.'),ensure_ascii=False,indent=2)+'\n').encode('utf8')
tmp=OUT/'stage_test_selection.json.tmp';tmp.write_bytes(raw);os.replace(tmp,OUT/'stage_test_selection.json')
with (OUT/'pytest_stages.log').open('w',encoding='utf8') as log:
    result=subprocess.run(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
print('STAGE_TEST_EXIT='+str(result.returncode))
raise SystemExit(result.returncode)
