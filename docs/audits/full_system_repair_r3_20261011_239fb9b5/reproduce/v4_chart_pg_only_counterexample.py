from pathlib import Path
import sys,json,hashlib,sqlite3,time
ROOT=Path('G:/codex work/大A交易');BASE=Path('G:/codex_tmp/full_system_repair_r3_239fb9b5');sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.operational_successor_v1 import accepted_api
from workbench_service.core_product_bff_r1 import CoreProductBFFR1
heads={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'data/v4').glob('*HEAD.json')}
attempts=[]
def reject(path,*args,**kwargs):
 attempts.append(dict(path=str(path),uri=kwargs.get('uri'),database_opened=False))
 raise ValueError('V4_POSTGRES_ONLY_HISTORY_INDEX_SQLITE_ATTEMPT')
sqlite3.connect=reject
started=time.monotonic();api=accepted_api(ROOT);bff=CoreProductBFFR1(api,None)
try:bff.chart('2026-10-09','SEC-EDEDE35FE66896ACCA0AC85EEB2F133B',{})
except ValueError as e:
 assert str(e)=='V4_POSTGRES_ONLY_HISTORY_INDEX_SQLITE_ATTEMPT'
else:raise AssertionError('Actual chart did not exercise SQLite index')
assert len(attempts)==1 and attempts[0]['uri'] is True and '?mode=ro' in attempts[0]['path']
assert heads=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'data/v4').glob('*HEAD.json')}
result=dict(contract_id='FA019_ACTUAL_DATED_V4_CHART_BACKEND_COUNTEREXAMPLE_R3',date='2026-10-09',entity_id='SEC-EDEDE35FE66896ACCA0AC85EEB2F133B',actual_consumer='CoreProductBFFR1.chart over accepted_api real frozen Owners; no synthetic history fixture',attempts=attempts,seconds=time.monotonic()-started,protected_heads_unchanged=True,acceptance='CONFIRMED_CURRENT_READONLY_SQLITE_INDEX_DEPENDENCY_NOT_FIXED',source_sha256=hashlib.sha256((ROOT/'src/workbench_service/core_product_bff_r1.py').read_bytes()).hexdigest())
(BASE/'fa019_chart_counterexample.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());print(result)
