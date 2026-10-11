import os,sys,json,hashlib,subprocess
from pathlib import Path
from contextlib import contextmanager
B=Path('G:/codex_tmp/full_system_audit_r2_58faf74e');R=Path('G:/codex work/大A交易');V=Path('G:/codex_tmp/full_system_audit_a2eadda/frozen');O=B/'b0_historical_profile';O.mkdir(exist_ok=True)
a=json.loads((V/'reports/v4_08/V4_08_R5_B0_IMPLEMENTATION.json').read_bytes());p=a['producer'];commit='90cef3e17a44e7170d1164771895bc517d10a478';raw=subprocess.check_output(['git','show',commit+':'+p['path']],cwd=R)
assert hashlib.sha256(raw).hexdigest()==p['sha256'];out=O/p['path'];out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
for rel in ['reports/v4_08/V4_08_R5_B0_IMPLEMENTATION.json','data/v4/V4_08_ACCEPTED_HEAD_AMENDED_R1.json',a['contract']['path'],'src/sector/native_r5.py','config/v4_08_sector_native_contract_r5.json']:
 q=O/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((V/rel).read_bytes())
sys.path[:0]=[str(V),str(V/'src')];from scripts import promote_v4_08_accepted_head as v8
oldroot=v8.ROOT;v8.ROOT=O
checks=v8.b0_semantic_checks(v8.read(v8.AMENDED));negative={}
from copy import deepcopy
for field,wrong in [('b0_producer','src/sector/native_r5.py'),('b0_contract','config/v4_08_sector_native_contract_r5.json')]:
 h=deepcopy(v8.read(v8.AMENDED));h[field]=v8.bind(wrong);h['evidence_bindings'][field]=v8.bind(wrong);negative[field]=not all(v8.b0_semantic_checks(h).values())
v8.ROOT=oldroot
result=dict(stage_contract='B0_EXACT_HISTORICAL_BYTE_FIXTURE_R2',historical_source_commit=commit,producer=p,fixture_root=str(O),positive_checks=checks,negative_tamper_rejected=negative,current_source_rebound=False,status='HISTORICAL_VALIDATOR_PASS_SCOPED' if all(checks.values()) and all(negative.values()) else 'FAIL')
(B/'b3_b0_historical_validation.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
