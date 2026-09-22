"""Read-only latest-complete-publication full-stock P12-03 predicate funnel."""
from __future__ import annotations
import hashlib,json,os,sys,tempfile,math
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.today_research_factors_v3_3 import calculate_today_facts
from workbench_analysis.today_research_scanner_v3_3 import scan_today_research
from workbench_analysis.history_170_v3_3 import load_stock_facts
DB=Path(os.environ.get('WORKBENCH_COMPUTE_DUCKDB',str(ROOT/'data/database/market_research.duckdb'))).resolve();PARQUET=ROOT/'data/normalized/adjusted_daily.parquet'
OUT=ROOT/'reports/p12_03/current_funnel.json'
def sha(path):
 h=hashlib.sha256();h.update(path.read_bytes());return h.hexdigest()
def main():
 with duckdb.connect(str(DB),read_only=True) as c:
  run,pub,TARGET=c.execute("select run_id,publication_id,cast(trade_date as varchar) from research_runs where status='COMPLETE' order by trade_date desc,completed_at desc limit 1").fetchone()
  expected_pub=os.environ.get('P12_EXPECTED_PUBLICATION_ID');expected_day=os.environ.get('P12_EXPECTED_TRADE_DATE')
  if (expected_pub and pub!=expected_pub) or (expected_day and TARGET!=expected_day):raise RuntimeError('P12_INPUT_IDENTITY_MISMATCH')
  dates=[x[0].isoformat() for x in c.execute("select distinct date from read_parquet(?) where date<=? order by date",[str(PARQUET),TARGET]).fetchall()]; window=dates[-27:]; idx={d:i for i,d in enumerate(dates)}
  rows=c.execute("select security_id,date,adj_open,adj_high,adj_low,adj_close,raw_open,raw_close,raw_amount,raw_volume,has_actual_bar,is_synthetic_fill,universe_status from read_parquet(?) where date between ? and ? order by security_id,date",[str(PARQUET),window[0],TARGET]).fetchall()
  old=c.execute("select security_id,setup,breakout,recovery,trend_background,structure_break,risk_codes from research_stock_states where run_id=?",[run]).fetchall()
  snapshot=c.execute("select snapshot_id from publication_analysis_snapshots where publication_id=? and domain='LOCAL_RECONSTRUCTED'",[pub]).fetchone()[0]
  strength_slice=c.execute("select slice_id from analysis_snapshot_entries where snapshot_id=? and domain='strength' and trade_date=?",[snapshot,TARGET]).fetchone()[0]
  rps=dict(c.execute("select security_id,rps20 from strength_result_daily where slice_id=?",[strength_slice]).fetchall())
  names=dict(c.execute("select security_id,security_name from stock_daily where publication_id=?",[pub]).fetchall())
 history_facts,history_identity=load_stock_facts(ROOT,TARGET)
 by=defaultdict(dict)
 for x in rows:by[x[0]][x[1].isoformat()]=x
 old={x[0]:x[1:] for x in old};counts={k:Counter() for k in ('launch','pullback','recovery_turn','trend_continue_stock_only','trend_continue','setup_watch')}; failed=Counter();unknown=Counter();eligible_rows=[]
 for sid,bars in by.items():
  inputs=[]
  for d in window[-22:]:
   x=bars.get(d);base={'date':d,'session_index':idx[d],'anchor_cutoff':TARGET,'price_basis':'TDX_NATIVE_AFFINE_QFQ'}
   inputs.append({**base,'has_actual_bar':False} if x is None or not x[10] else {**base,'has_actual_bar':True,'is_synthetic_fill':bool(x[11]),'open':x[2],'high':x[3],'low':x[4],'close':x[5],'raw_open':x[6],'raw_close':x[7],'amount':x[8],'volume':x[9]})
  f=calculate_today_facts(inputs); historical=history_facts.get(sid)
  if historical:
   for key in tuple(f):
    if key in historical:
     value=historical[key];f[key]=None if isinstance(value,float) and math.isnan(value) else value
  o=old.get(sid,(None,)*6); current=bars[TARGET]; c=f['ma20']*(1+f['bias20']) if f['ma20'] is not None and f['bias20'] is not None else None
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
  matched=[]
  if out['launch']['eligible'] is True:matched.append('LAUNCH_CONFIRM')
  if out['recovery_turn']['eligible'] is True:matched.append('RECOVERY_TURN')
  if out['pullback']['eligible'] is True:matched.append('STRONG_PULLBACK')
  if out['trend_continue_stock_only']['eligible'] is True:matched.append('TREND_CONTINUE')
  if matched or out['setup_watch']['eligible'] is True:
   eligible_rows.append({'security_id':sid,'security_name':names.get(sid),'matched_stock_only_categories':matched,'setup_watch':out['setup_watch']['eligible'],'clv':f['clv'],'liq20_amount':f['liq20_amount'],'break_margin_close20':f['break_margin_close20'],'amr20_mean_prior':f['amr20_mean_prior'],'rps5_delta3':None,'slope20':f['slope20'],'r2_20':f['r2_20'],'rps20':rps.get(sid),'bias20':f['bias20'],'freshness':.20,'risk_codes':risks,'factor_evidence':f,'scanner_evidence':out})
 result={'stage_contract':'P12-03_CURRENT_FUNNEL_V1','captured_at_utc':datetime.now(timezone.utc).isoformat(),'target_date':TARGET,'input_identity':{'run_id':run,'publication_id':pub,'snapshot_id':snapshot,'strength_slice':strength_slice,'parquet_sha256':sha(PARQUET),'history_170':history_identity},'stocks':len(by),'scenario_counts':{k:dict(v) for k,v in counts.items()},'eligible_or_watch_rows':eligible_rows,'top_known_failures':failed.most_common(),'top_unknowns':unknown.most_common(),'limitations':['PULLBACK_HISTORIC_FROZEN_SEED_UNAVAILABLE','RPS5_DELTA3_FORMAL_PIT_UNAVAILABLE','CURRENT_LOO_SUPPORT_P12_04'], 'acceptance_result':'DEGRADED_PASS','next_stage':'P12-03_SCANNER_V3_3_CONTINUE'}
 if not by or any(sum(v.values())!=len(by) for v in counts.values()):result.update(acceptance_result='BLOCKED',next_stage='P12-03_REPAIR')
 OUT.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(dir=OUT.parent)
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as s:json.dump(result,s,ensure_ascii=False,indent=2);s.write('\n');s.flush();os.fsync(s.fileno())
  os.replace(tmp,OUT)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
 if result['acceptance_result']=='BLOCKED':raise RuntimeError('funnel blocked')
 print(OUT)
if __name__=='__main__':main()
