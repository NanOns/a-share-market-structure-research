import os,pathlib,json,hashlib,collections,sys
from pathlib import Path
import psycopg
from psycopg import sql
repo=next(p for p in Path(__file__).resolve().parents if (p/'config/.env').is_file() and (p/'src').is_dir())
sys.path.insert(0,str(repo/'src'))

for line in (repo/'config/.env').read_text(encoding='utf-8-sig').splitlines():
 item=line.strip()
 if not item or item.startswith('#') or '=' not in item: continue
 k,v=item.split('=',1);k=k.strip();v=v.strip().strip('"').strip("'")
 if k in ('WORKBENCH_PG_DSN','V4_NATIVE_PG_DSN','V4_NATIVE_PG_READER_DSN') and v:os.environ.setdefault(k,v)
dsn=os.environ.get('V4_NATIVE_PG_READER_DSN') or os.environ.get('V4_NATIVE_PG_DSN') or os.environ.get('WORKBENCH_PG_DSN')
schema='v4_r8_forward_0c2b84fb3e1a0c42'
with psycopg.connect(dsn,connect_timeout=5) as pg:
 pg.execute('SET TRANSACTION READ ONLY')
 kinds=pg.execute(sql.SQL('SELECT kind,count(*) FROM {}.forward_facts GROUP BY kind ORDER BY kind').format(sql.Identifier(schema))).fetchall()
 facts=pg.execute(sql.SQL("SELECT kind,fact_key,payload FROM {}.forward_facts WHERE kind IN ('r7_daily_universe','r7_settlement_schedule','r7_publish_index','r7_aggregate_stats') ORDER BY ordinal").format(sql.Identifier(schema))).fetchall()
print('KIND_COUNTS',json.dumps(kinds))
dailies=[]; settlements=[]; indexes=[]; aggregates=[]
for kind,key,payload in facts:
 obj=json.loads(payload)
 if kind=='r7_daily_universe':dailies.append((key,obj))
 elif kind=='r7_settlement_schedule':settlements.append((key,obj))
 elif kind=='r7_publish_index':indexes.append((key,obj))
 else:aggregates.append((key,obj))
print('FACT_COUNTS',json.dumps({'daily_bundles':len(dailies),'settlement_bundles':len(settlements),'publish_indexes':len(indexes),'aggregate_rows':len(aggregates)}))
latest={}; raw_by_day=collections.Counter(); hashes=collections.defaultdict(set); rule=collections.defaultdict(set); errors=[]
for key,bundle in dailies:
 for row in bundle.get('rows',[]):
  day=row.get('T0'); lane=row.get('evidence_lane') or bundle.get('lane') or 'RETROSPECTIVE_RESEARCH'; rid=row.get('rule_id'); version=row.get('rule_version'); ent=row.get('entity_id'); rev=int(row.get('capture_revision',row.get('revision',1)))
  ident=(day,lane,rid,version,ent);raw_by_day[day]+=1
  hashes[day].add(row.get('source_digest') or bundle.get('source_digest') or '')
  rule[day].add((rid,version,row.get('entity_type')))
  if not all((day,lane,rid,version,ent)):errors.append({'day':day,'error':'identity_missing'})
  old=latest.get(ident)
  if old is None or rev>=old[0]:latest[ident]=(rev,row,bundle)
counts=collections.defaultdict(collections.Counter)
for (day,lane,rid,version,ent),(rev,row,bundle) in latest.items():
 counts[day][row.get('status','UNKNOWN')]+=1
settle_latest={}
for key,bundle in settlements:
 for item in bundle.get('items',[]):
  obs=item.get('observation_id');hor=item.get('horizon_sessions');lane=bundle.get('lane','RETROSPECTIVE_RESEARCH');rev=int(item.get('settlement_revision',bundle.get('revision',1)))
  ident=(lane,obs,hor); old=settle_latest.get(ident)
  if old is None or rev>=old[0]:settle_latest[ident]=(rev,item,bundle)
by_settle=collections.defaultdict(collections.Counter); valid_obs={}
for (_,_,_,_,_),(_,row,bundle) in latest.items():
 from workbench_analysis.forward_r7 import make_observation_id
 valid_obs[make_observation_id(row)]=row
for (lane,obs,hor),(rev,item,bundle) in settle_latest.items():
 row=valid_obs.get(obs)
 if row:
  by_settle[(row.get('T0'),lane,hor)][item.get('schedule_status','UNKNOWN')]+=1
sessions=sorted(set(raw_by_day))
print('DAILY',json.dumps([{'trade_date':d,'raw_rows':raw_by_day[d],'latest_unique':sum(counts[d].values()),'duplicate_revision_rows_collapsed':raw_by_day[d]-sum(counts[d].values()),'MATCH':counts[d]['MATCH'],'NO_MATCH':counts[d]['NO_MATCH'],'UNKNOWN':counts[d]['UNKNOWN'],'late':counts[d]['LATE_OBSERVED_NOT_PIT'],'other_status':{k:v for k,v in counts[d].items() if k not in ('MATCH','NO_MATCH','UNKNOWN','LATE_OBSERVED_NOT_PIT')},'rules':[list(x) for x in sorted(rule[d])],'source_sha256':sorted(h for h in hashes[d] if h),'binding_missing':any(not h for h in hashes[d])} for d in sessions],ensure_ascii=False))
print('SETTLEMENT',json.dumps([{'trade_date':d,'lane':lane,'horizon':h,'counts':dict(c)} for (d,lane,h),c in sorted(by_settle.items())],ensure_ascii=False))
print('INDEXES',json.dumps([{k:o.get(k) for k in ('lane','generation','trade_date','payload_sha256','source_run_id','published_at')} for _,o in indexes],ensure_ascii=False))
print('FACT_ERRORS',json.dumps(errors[:20]))
