"""Independent bounded Focus oracle and lossless pause checkpoint; no admission."""
import gzip,hashlib,json,os,subprocess,zipfile
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal
import psycopg
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/audits/r4_r3_integration_20261011/PAUSE_CHECKPOINT_20261012_R1'
OUT.mkdir(exist_ok=False)
sha=lambda b:hashlib.sha256(b).hexdigest()
workspace=Path('G:/codex_tmp/r4_r3_pg_publication_v2')
receipt=json.loads((ROOT/'docs/audits/r4_r3_consumers_20261011/FOCUS_RESUME_R1/RESULT.json').read_bytes())
assert receipt['result']['status']=='ENGINEERING_FOCUS_PROJECTED' and receipt['inputs_unchanged']
p=workspace/receipt['result']['focus']['path']; payload=p.read_bytes(); projection=json.loads(gzip.decompress(payload))
assert sha(payload)==receipt['result']['focus']['sha256']
binding=projection['source_bindings']; descriptor=json.loads((workspace/binding['series']['path']).read_bytes())
clusters=[]
for port in (55791,55792,55793,55794):
 with psycopg.connect(host='127.0.0.1',port=port,user='r4_isolated_admin',dbname='postgres',connect_timeout=10) as c:
  directory=c.execute('show data_directory').fetchone()[0]
  identity=c.execute('select system_identifier::text from pg_control_system()').fetchone()[0]
  assert directory.replace('\\','/').startswith('G:/codex_tmp/')
  if port==55791:assert identity=='7695278778933357404'
  clusters.append(dict(port=port,data_directory=directory,system_identifier=identity))
with psycopg.connect(host='127.0.0.1',port=55791,user='r4_isolated_admin',dbname='postgres',options='-c default_transaction_read_only=on') as c:
 c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
 bars={}
 from psycopg import sql
 for sid,day,raw in c.execute(sql.SQL('SELECT security,day::text,payload FROM {}.bars ORDER BY security,day').format(sql.Identifier(descriptor['schema']))):bars.setdefault(sid,{})[day]=json.loads(raw)
# Parser only: independently calculate no-corporate-action paths using rational arithmetic.
from tdx.gbbq_reader import read_gbbq
events={}
for e in read_gbbq(workspace/binding['gbbq']['path']):events.setdefault(e.security_id,[]).append(e.event_date)
comparisons=0; skipped=0; mismatches=[]; unique=set()
for episode in projection['episodes']:
 sid=episode['entity_id']; start=episode['start_date']
 for obs in episode['observations']:
  end=obs['trade_date']; fact=obs['price_path']; key=(sid,start,end)
  if key in unique:continue
  unique.add(key)
  if fact['quality']!='READY':skipped+=1;continue
  rows=[r for d,r in sorted(bars[sid].items()) if start<=d<=end]
  if any(int(start.replace('-',''))<d<=int(end.replace('-','')) for d in events.get(rows[-1]['symbol'],[])):skipped+=1;continue
  values=[[F(str(x)) for x in r['raw_ohlc']] for r in rows]; entry=values[0][3]
  closes=[v[3] for v in values]; peak=closes[0]; worst=F(0)
  for close in closes:peak=max(peak,close);worst=min(worst,close/peak-1)
  expected=dict(return_close=closes[-1]/entry-1,mfe=max(v[1] for v in values)/entry-1,mae=min(v[2] for v in values)/entry-1,peak_close=max(closes),drawdown_current=closes[-1]/max(closes)-1,mdd_close=worst)
  for name,value in expected.items():
   actual=F(Decimal(fact['metrics'][name]));comparisons+=1
   if abs(actual-value)>F(1,10**24):mismatches.append(dict(key=key,metric=name,expected=str(value),actual=str(actual)))
oracle=dict(contract='INDEPENDENT_RATIONAL_NO_ACTION_FOCUS_PATH_ORACLE_V1',comparisons=comparisons,unique_paths=len(unique),excluded_paths=skipped,mismatches=mismatches,scope='READY paths with no corporate action; full adjustment and lifecycle semantics remain OPEN')
(OUT/'INDEPENDENT_FOCUS_NUMBERS.json').write_text(json.dumps(oracle,indent=2)+'\n')
assert comparisons and not mismatches
(OUT/'CLUSTER_READBACK.json').write_text(json.dumps(clusters,indent=2)+'\n')
(OUT/'CORRECTED_FOCUS_FORWARD.json.gz').write_bytes(payload)
manifest=[]
def archive(path,role):
 data=path.read_bytes(); relative=path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
 name=f'{len(manifest):05d}.gz';(OUT/name).write_bytes(gzip.compress(data,mtime=0))
 manifest.append(dict(source=relative,archive=name,bytes=len(data),sha256=sha(data),role=role))
for prefix in ('SERIES_VERIFIED_SCOPE_R1','SERIES_VERIFIED_SCOPE_R2'):
 for path in sorted((ROOT/'docs/audits/r4_r3_scope_20261011').glob(prefix+'*')):
  if path.is_file():archive(path,'actual_matrix_raw_including_previous_failure')
for path in sorted((ROOT/'docs/audits/r4_r3_consumers_20261011/FOCUS_RESUME_R1').glob('*')):
 if path.is_file():archive(path,'actual_focus_resume')
archive(Path('G:/codex_tmp/FOCUS_RESUME_R1_RAW.log'),'actual_focus_stdout')
for path in Path('G:/codex_tmp/r4_r3_isolated_recovery_20261012').rglob('*'):
 if path.is_file():archive(path,'isolated_recovery_raw')
# Preserve unfinished working changes as evidence, without claiming they are completed implementation.
patch=subprocess.check_output(['git','diff','--binary'],cwd=ROOT)
(OUT/'UNFINISHED_TRACKED_WORK.patch.gz').write_bytes(gzip.compress(patch,mtime=0))
untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT).decode().splitlines()
for name in untracked:
 path=ROOT/name
 if path.is_file() and not path.is_relative_to(OUT):archive(path,'uncommitted_checkpoint_NOT_ACCEPTED')
(OUT/'ARCHIVE_MANIFEST.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
seal=dict(status='USER_REQUESTED_PAUSE_AFTER_CURRENT_PACKAGE',series_tests=26,series_exit_code=0,focus_episodes=receipt['result']['episodes'],focus_runtime_seconds=receipt['seconds'],independent_numerical_scope=oracle,completed_source_paths=['src/workbench_db/v4_series_pg_r1.py','src/focus_tracker/v4_native_core_adapter.py','scripts/resume_r4_r3_focus_projection.py','tests/test_v4_series_verified_scope_r3.py','scripts/seal_r4_r3_pause_checkpoint.py'],open=['full legal V4 denominator','all real consumers','56 adjustment classes','complete semantics','Focus candidate seal and PG publication','DM01 current runtime qualification'],production_changed=False,external_acceptance='BLOCKED',future_gates=['real trading-day capture','mature samples','deployment authorization'],preservation='unfinished changes archived as NOT_ACCEPTED; old accepted outputs unchanged')
(OUT/'SEAL.json').write_text(json.dumps(seal,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print(json.dumps(dict(comparisons=comparisons,mismatches=len(mismatches),archived_files=len(manifest),out=str(OUT))))
