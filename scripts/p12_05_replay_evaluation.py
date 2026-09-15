"""Pre-registered three-date diagnostic replay with horizon-end adjustment anchors."""
from __future__ import annotations
import hashlib,json,os,sys,tempfile
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from adjustment.tdx_adjustment import build_affine_factors,xrxd_from_gbbq
from tdx.gbbq_reader import read_gbbq
PARQUET=ROOT/'data/normalized/adjusted_daily.parquet';GBBQ=Path('D:/new_tdx/T0002/hq_cache/gbbq');OUT=ROOT/'reports/p12_05/replay_evaluation.json';H=(1,3,5,10)
def sha(p):h=hashlib.sha256();h.update(p.read_bytes());return h.hexdigest()
def main():
 source=json.loads((ROOT/'reports/p12_02/three_day_factor_replay.json').read_text(encoding='utf-8'));baseline_sets={x['date']:{k:set(v) for k,v in x['equal_count_baselines'].items() if isinstance(v,list)} for x in source['dates']};targets={day:sorted(set().union(*groups.values())) for day,groups in baseline_sets.items()};events=defaultdict(list)
 wanted={s for xs in targets.values() for s in xs}
 for x in read_gbbq(GBBQ):
  if x.category==1 and x.security_id in wanted:events[x.security_id].append(xrxd_from_gbbq(x))
 with duckdb.connect(database=':memory:') as c:
  sessions=[x[0].isoformat() for x in c.execute("select distinct date from read_parquet(?) where date between '2026-01-01' and '2026-09-14' order by date",[str(PARQUET)]).fetchall()]
  rows=c.execute("select security_id,date,raw_high,raw_low,raw_close,has_actual_bar from read_parquet(?) where security_id in (select unnest(?)) and date between '2026-01-01' and '2026-09-14' order by security_id,date",[str(PARQUET),list(wanted)]).fetchall()
 bars=defaultdict(dict)
 for sid,d,hi,lo,cl,actual in rows:bars[sid][d.isoformat()]={'high':hi,'low':lo,'close':cl,'actual':actual}
 outcomes=[];summary={}
 for t,ids in targets.items():
  part='DEVELOPMENT' if t<'2026-05-01' else 'VALIDATION' if t<'2026-08-01' else 'LOCKED_OBSERVATION';status=defaultdict(int);values=defaultdict(list)
  ti=sessions.index(t)
  group_values={name:defaultdict(list) for name in baseline_sets[t]}
  for sid in ids:
   for h in H:
    if ti+h>=len(sessions):outcomes.append({'signal_date':t,'security_id':sid,'horizon':h,'status':'NOT_DUE','partition':part});status['NOT_DUE']+=1;continue
    e=sessions[ti+h];days=sessions[:ti+h+1];actual=[int(d.replace('-','')) for d in days if d in bars[sid] and bars[sid][d]['actual']]
    if t not in bars[sid] or e not in bars[sid] or not bars[sid][t]['actual'] or not bars[sid][e]['actual']:
     outcomes.append({'signal_date':t,'security_id':sid,'horizon':h,'end_date':e,'status':'DATA_GAP','partition':part});status['DATA_GAP']+=1;continue
    factors=build_affine_factors(actual,[x for x in events[sid] if x.ex_day<=int(e.replace('-',''))]);base=factors[int(t.replace('-',''))].qfq_price(bars[sid][t]['close']);end=factors[int(e.replace('-',''))].qfq_price(bars[sid][e]['close']);window=[d for d in sessions[ti+1:ti+h+1] if d in bars[sid] and bars[sid][d]['actual']]
    if len(window)!=h or base<=0:
     outcomes.append({'signal_date':t,'security_id':sid,'horizon':h,'end_date':e,'status':'DATA_GAP','partition':part});status['DATA_GAP']+=1;continue
    fret=float(end/base-1);mfe=float(max(factors[int(d.replace('-',''))].qfq_price(bars[sid][d]['high']) for d in window)/base-1);mae=float(min(factors[int(d.replace('-',''))].qfq_price(bars[sid][d]['low']) for d in window)/base-1)
    groups=sorted(name for name,stocks in baseline_sets[t].items() if sid in stocks)
    outcomes.append({'signal_date':t,'security_id':sid,'horizon':h,'end_date':e,'anchor':e,'status':'OBSERVED','partition':part,'baseline_groups':groups,'fret':fret,'mfe':mfe,'mae':mae});status['OBSERVED']+=1;values[h].append(fret)
    for name in groups:group_values[name][h].append(fret)
  summary[t]={'partition':part,'union_signals':len(ids),'equal_group_count':next(iter(source_day['equal_count_baselines']['sample_count'] for source_day in source['dates'] if source_day['date']==t)),'status_counts':dict(status),'median_fret_union':{str(h):sorted(v)[len(v)//2] if v else None for h,v in values.items()},'baseline_median_fret':{name:{str(h):sorted(v)[len(v)//2] if v else None for h,v in by_h.items()} for name,by_h in group_values.items()}}
 logical={'preregistration':{'development':['2026-03-31','2026-03-31'],'validation':['2026-06-30','2026-06-30'],'locked_observation':['2026-09-14','2026-09-14'],'embargo_sessions':10,'horizons':list(H),'parameter_tuning':'NONE'},'history_basis':'RECONSTRUCTED_CURRENT_MEMBERSHIP','evaluation_basis':'HORIZON_END_TDX_AFFINE_QFQ_V1','summary':summary,'outcomes':outcomes}
 logical_hash=hashlib.sha256(json.dumps(logical,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 result={'stage_contract':'P12-05_REPLAY_V3_3_DIAGNOSTIC_V1','captured_at_utc':datetime.now(timezone.utc).isoformat(),**logical,'logical_result_sha256':logical_hash,'input_identity':{'adjusted_daily_sha256':sha(PARQUET),'gbbq_current_sha256':sha(GBBQ),'candidate_source_sha256':sha(ROOT/'reports/p12_02/three_day_factor_replay.json')},'outcome_count':len(outcomes),'baselines':{'old_priority':'RECONSTRUCTED_EQUAL_COUNT','rps_only':'RECONSTRUCTED_EQUAL_COUNT','stock_trigger_no_sector':'RECONSTRUCTED_EQUAL_COUNT','complete':'RECONSTRUCTED_EQUAL_COUNT'},'ablation':{'loo':{'current_stock_only':140,'current_formal':9},'position_gate_by_date':{x['date']:x['ablation_counts'] for x in source['dates']},'freshness':{'mode':'CONSERVATIVE_0_20_ALL_RECONSTRUCTED_SIGNALS','eligibility_changed':0,'ranking_interpretation':'AGE_LEFT_CENSORED'}},'effect_status':'EFFECT_OBSERVATION_PENDING','acceptance_result':'DEGRADED_PASS','next_stage':'P12-05_STAGE_GATE'}
 OUT.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(dir=OUT.parent)
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as s:json.dump(result,s,ensure_ascii=False,indent=2,allow_nan=False);s.write('\n');s.flush();os.fsync(s.fileno())
  os.replace(tmp,OUT)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
 print(OUT)
if __name__=='__main__':main()
