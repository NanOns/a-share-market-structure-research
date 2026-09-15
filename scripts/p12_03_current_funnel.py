"""Read-only 2026-09-14 full-stock P12-03 predicate funnel."""
from __future__ import annotations
import hashlib,json,os,sys,tempfile
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.today_research_factors_v3_3 import calculate_today_facts
from workbench_analysis.today_research_scanner_v3_3 import scan_today_research
DB=ROOT/'data/database/market_research.duckdb';PARQUET=ROOT/'data/normalized/adjusted_daily.parquet'
OUT=ROOT/'reports/p12_03/current_funnel.json';TARGET='2026-09-14'
def sha(path):
 h=hashlib.sha256();h.update(path.read_bytes());return h.hexdigest()
def main():
 baseline=json.loads((ROOT/'reports/p12_01/baseline_v2.json').read_text(encoding='utf-8'));run=baseline['input_identity']['run_id']
 with duckdb.connect(str(DB),read_only=True) as c:
  dates=[x[0].isoformat() for x in c.execute("select distinct date from read_parquet(?) where date<='2026-09-14' order by date",[str(PARQUET)]).fetchall()]; window=dates[-27:]; idx={d:i for i,d in enumerate(dates)}
  rows=c.execute("select security_id,date,adj_open,adj_high,adj_low,adj_close,raw_open,raw_close,raw_amount,raw_volume,has_actual_bar,is_synthetic_fill,universe_status from read_parquet(?) where date between ? and ? order by security_id,date",[str(PARQUET),window[0],TARGET]).fetchall()
  old=c.execute("select security_id,setup,breakout,recovery,trend_background,structure_break,risk_codes from research_stock_states where run_id=?",[run]).fetchall()
  strength_slice=next(x[2] for x in baseline['input_identity']['dependency_bindings']['analysis_slices'] if x[0]=='strength' and x[1]==TARGET)
  rps=dict(c.execute("select security_id,rps20 from strength_result_daily where slice_id=?",[strength_slice]).fetchall())
 by=defaultdict(dict)
 for x in rows:by[x[0]][x[1].isoformat()]=x
 old={x[0]:x[1:] for x in old};counts={k:Counter() for k in ('launch','pullback','recovery_turn','trend_continue_stock_only','trend_continue','setup_watch')}; failed=Counter();unknown=Counter()
 for sid,bars in by.items():
  inputs=[]
  for d in window[-22:]:
   x=bars.get(d);base={'date':d,'session_index':idx[d],'anchor_cutoff':TARGET,'price_basis':'TDX_NATIVE_AFFINE_QFQ'}
   inputs.append({**base,'has_actual_bar':False} if x is None or not x[10] else {**base,'has_actual_bar':True,'is_synthetic_fill':bool(x[11]),'open':x[2],'high':x[3],'low':x[4],'close':x[5],'raw_open':x[6],'raw_close':x[7],'amount':x[8],'volume':x[9]})
  f=calculate_today_facts(inputs); o=old.get(sid,(None,)*6); current=bars[TARGET]; c=f['ma20']*(1+f['bias20']) if f['ma20'] is not None and f['bias20'] is not None else None
  prior=bars.get(window[-2]); prior5=[]
  for d in window[-6:-1]:
   seq=[bars.get(k) for k in window[:window.index(d)+1]]
   valid=[x for x in seq[-20:] if x and x[10] and not x[11] and x[5] is not None]
   prior5.append(None if len(valid)!=20 else float(bars[d][5]) < sum(float(x[5]) for x in valid)/20)
  risks=json.loads(o[5]) if isinstance(o[5],str) else (o[5] or [])
  row={**f,'security_id':sid,'trade_date':TARGET,'normal_universe':current[12]=='IN_NORMAL_UNIVERSE','actual_bar':bool(current[10]) and not bool(current[11]),'window_valid':f['quality']=='READY','input_identity_compatible':True,'setup_v3':o[0],'breakout_v3':o[1],'recovery_v3':o[2],'trend_background_v3':o[3],'structure_break_v3':o[4],'extended_v3':'EXTENDED' in risks,'pullback_episode_confirmed':None,'rps20':rps.get(sid),'rps5_delta3':None,'prior5_below_ma20_count':sum(prior5) if all(x is not None for x in prior5) else None,'ma20_nondeclining_3':None,'close_to_ma20':c/f['ma20'] if c and f['ma20'] else None,'close_to_ma5':c/f['ma5'] if c and f['ma5'] else None,'ma5_to_ma20':f['ma5']/f['ma20'] if f['ma5'] and f['ma20'] else None,'close_above_prior_high':c>float(prior[3]) if c and prior and prior[3] else None,'current_with_loo_breadth_support':None}
  out=scan_today_research(row)
  for name in counts:
   item=out[name];counts[name][str(item['eligible'])]+=1
   failed.update(f'{name}.{x}' for x in item['known_failed_checks']);unknown.update(f'{name}.{x}' for x in item['unknown_checks'])
 result={'stage_contract':'P12-03_CURRENT_FUNNEL_V1','captured_at_utc':datetime.now(timezone.utc).isoformat(),'target_date':TARGET,'input_identity':{'run_id':run,'parquet_sha256':sha(PARQUET)},'stocks':len(by),'scenario_counts':{k:dict(v) for k,v in counts.items()},'top_known_failures':failed.most_common(),'top_unknowns':unknown.most_common(),'limitations':['PULLBACK_HISTORIC_FROZEN_SEED_UNAVAILABLE','RPS5_DELTA3_FORMAL_PIT_UNAVAILABLE','CURRENT_LOO_SUPPORT_P12_04'], 'acceptance_result':'DEGRADED_PASS','next_stage':'P12-03_SCANNER_V3_3_CONTINUE'}
 if len(by)!=6182 or any(sum(v.values())!=6182 for v in counts.values()):result.update(acceptance_result='BLOCKED',next_stage='P12-03_REPAIR')
 OUT.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(dir=OUT.parent)
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as s:json.dump(result,s,ensure_ascii=False,indent=2);s.write('\n');s.flush();os.fsync(s.fileno())
  os.replace(tmp,OUT)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
 if result['acceptance_result']=='BLOCKED':raise RuntimeError('funnel blocked')
 print(OUT)
if __name__=='__main__':main()
