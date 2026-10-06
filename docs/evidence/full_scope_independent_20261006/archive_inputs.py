"""Archive supplied evidence and resolve namespace scope atomically."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
def atomic(path,raw):
    tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)
def emit(name,value):atomic(OUT/name,(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
online=Path('D:/Users/lps/Desktop/阶段任务/V4_00_TO_V4_22_PLUS_FEP_CROSS_MODEL_FULL_STAGE_CONFORMANCE_AUDIT_R1_20261006.md')
raw=online.read_bytes();atomic(OUT/'online_model_report_input.md',raw)
emit('online_report_identity.json',dict(source_path=str(online),archive_path='docs/evidence/full_scope_independent_20261006/online_model_report_input.md',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),audited_head='b7ca247745976aa390387a0701601b00ac0d8498',role='EVIDENCE_NOT_USER_INSTRUCTIONS',drive_comparison='ONLINE_REPORT_CLAIM_NOT_INDEPENDENTLY_REPEATED'))
contract='config/v4_18_migration_replay_contract_v1_3.json'
c=json.loads((ROOT/contract).read_bytes())
paths=list((ROOT/'src/workbench_db').rglob('*.sql'))+[ROOT/p for p in ('migrations/v4_16_r24_real_shadow_v1.sql','migrations/v4_16_settlement_queue_v2.sql','migrations/v4_16_real_shadow_integrity_v2.sql')]
actual={(p.relative_to(ROOT).as_posix(),name) for p in paths for name in re.findall(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w.]+)',p.read_text(encoding='utf8'),re.I)}
registered={(r['declaration'],r['state_or_table']) for r in c['namespace_matrix'] if r['declaration']!='DESIGN_ONLY_NOT_CREATED'}
legacy=ROOT/'migrations/v4_16_r23_shadow_v1.sql'
legacy_names=re.findall(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w.]+)',legacy.read_text(encoding='utf8'),re.I)
emit('migration_namespace_coverage.json',dict(contract=contract,active_scope='All src/workbench_db SQL + R24 real shadow + queue v2 + integrity v2; matches current successor test scope',declared=len(registered),actual=len(actual),missing=sorted(actual-registered),declared_not_present=sorted(registered-actual),result='PASS' if actual==registered else 'FAIL',excluded_historical_engineering_schema=dict(path=str(legacy.relative_to(ROOT)),tables=legacy_names,reason='R23 simulation engineering schema is not an active migration source; naive all-migrations count 242 would misclassify these 16 as omissions.')))
db=ROOT/'data/database/market_research.duckdb'
emit('global_rerun_interruption.json',dict(status='INTERRUPTED_NOT_COMPLETED_NO_JUNIT',progress_last_log='84%',reason='Legacy browser session fixture starts serve against actual workspace DB; serve invokes publication recovery and may mutate jobs/restart publication requests.',fixture='tests/upgrade_m12/test_browser_behavior.py:41',startup='src/workbench_service/app.py:2297',recovery='src/workbench_publish/service.py:272',terminated_processes=[39176,37788],no_python_processes_observed_after_stop=True,database_stat_after_stop=dict(path=str(db),size=db.stat().st_size,mtime_utc=datetime.fromtimestamp(db.stat().st_mtime,timezone.utc).isoformat()) if db.exists() else None,limitation='No pre-run exact DB fingerprint was captured. Cannot prove zero DB writes or claim all tests isolated. No TDX write was issued. No business tracked files changed.',tracked_changes_after_stop=subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).splitlines()))
print('Archived online evidence and active namespace coverage')
