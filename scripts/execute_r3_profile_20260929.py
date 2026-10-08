"""Build a 2026-09-29 isolated V4-04 Profile owner from R3 target-coordinate inputs."""
from __future__ import annotations
import collections, gzip, hashlib, importlib.util, json, os, sys
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/evidence/three_day_repair_r3_20261008'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from adjustment.tdx_adjustment import build_affine_factors,xrxd_from_gbbq
from tdx.gbbq_reader import read_gbbq
from v4.factors.core import market_reference
from v4.market_regime_ui import RegimeUI
from workbench_service.current_v4_context import canonical,digest

TARGET=sys.argv[1] if len(sys.argv)>1 else '2026-09-29'
if TARGET not in {'2026-09-28','2026-09-29'}:raise ValueError('unsupported R3 profile target')
REVISION='R1' if TARGET=='2026-09-28' else 'R2'
def read(path):return json.loads((ROOT/path).read_bytes())
def ref(path):
 p=ROOT/path
 return {'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def load_rows(path):
 with gzip.open(ROOT/path,'rt',encoding='utf-8') as f:return [json.loads(x) for x in f]
def main():
 head=read('data/v4/V4_DATA_ACCEPTED_HEAD.json');chain=read(head['accepted_chain']['path']);node={n['trade_date']:n for n in chain['nodes']}[TARGET]
 stock=read('config/v4_stock_operational_authority_v1.json');market_auth=read('config/v4_market_operational_authority_v1.json')
 market=read(market_auth['market']['path']);execution=read(market['sources']['execution']['path'])
 sessions=read(head['calendar']['path'])['session_dates'];sessions=[d for d in sessions if d<=TARGET]
 core_path=f'docs/evidence/three_day_repair_r1_20261008/core_owner_r2/owners/{TARGET}/core.jsonl.gz'
 core_rows=load_rows(core_path);core={x['security_id']:x for x in core_rows}
 identity=read(node['components']['IDENTITY_UNIVERSE']['artifact_path'])['rows'];ident={x['security_id']:x for x in identity}
 raw_history=collections.defaultdict(dict)
 with gzip.open(ROOT/stock['sources']['history']['path'],'rt',encoding='utf-8') as f:
  for line in f:
   row=json.loads(line);sid=row['security_id']
   if sid in ident:
    for bar in row['bars']:
     if bar['trade_date']<=TARGET:raw_history[sid][bar['trade_date']]=bar
 target_adjusted={x['security_id']:x for x in read(node['components']['ADJUSTED_DAILY']['artifact_path'])['rows']}
 status={}
 status_path=ROOT/'data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz'
 with gzip.open(status_path,'rt',encoding='utf-8') as f:
  for line in f:
   row=json.loads(line)
   if row['status']=='SUSPENDED':status.setdefault(row['security_id'],{})[row['trade_date']]='SUSPENDED'
 for row in read(node['components']['TRADING_STATUS']['artifact_path'])['rows']:
  status.setdefault(row['security_id'],{})[row['trade_date']]=row['status']
 gbbq=execution['inputs'][TARGET]['inputs']['GBBQ'];events=collections.defaultdict(list)
 for e in read_gbbq(ROOT/gbbq['path']):
  if e.event_date<=int(TARGET.replace('-','')):events[e.security_id].append(e)
 dispositions=read('config/v4_02_gbbq_price_impact_classification_v1.json')['dispositions']
 # Reuse the accepted V4-04 row builder and exact frozen contracts.
 spec=importlib.util.spec_from_file_location('r3_v4_04_builder',ROOT/'scripts/run_v4_04_full_market_candidate_r4.py')
 builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder);builder.CUTOFF=TARGET
 accepted_v4_04=read('data/v4/V4_04_ACCEPTED_HEAD.json')
 for name in builder.CONTRACT_FILES:
  if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=accepted_v4_04['contract_bindings'][name]['sha256']:
   raise ValueError('V4_04_ACCEPTED_CONTRACT_DIGEST_MISMATCH:'+name)
 period_source=ref(node['components']['PERIOD_ADJUSTED']['artifact_path'])
 rps_head=read('data/v4/V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1.json');rps_dates={d:v for d,v in rps_head['publications'].items()}
 def rps(day):
  if day not in rps_dates:return {}
  pub=read(rps_dates[day]['path']);return {x['security_id']:x for x in pub['rows']}
 current_rps=rps(TARGET);prior_day=sessions[sessions.index(TARGET)-3];prior_rps=rps(prior_day)
 # RPS values and delta endpoints are explicitly read from the accepted corrected history head.
 factors=[];bars_by={};unknown_adj=0
 for sid,crow in core.items():
  identity_row=ident.get(sid)
  if not identity_row:continue
  history=raw_history[sid];ordered=sorted(history.items());bar_dates=[int(d.replace('-','')) for d,_ in ordered]
  symbol=identity_row['source_security_key'];target_events=[e for e in events[symbol] if ordered and e.event_date>int(ordered[0][0].replace('-',''))]
  blocked=[e.category for e in target_events if dispositions.get(str(e.category),{}).get('formal_disposition','UNKNOWN_PRICE_IMPACT') in ('PRICE_AFFECTING_UNSUPPORTED','UNKNOWN_PRICE_IMPACT')]
  ready=target_adjusted.get(sid,{}).get('adjustment_readiness')=='READY'
  affine=build_affine_factors(bar_dates+[int(TARGET.replace('-',''))],[xrxd_from_gbbq(e) for e in target_events if e.category==1]) if ready and not blocked else {}
  daily=[]
  for day,raw in ordered:
   q=affine.get(int(day.replace('-','')))
   ohlc=raw.get('raw_ohlc')
   adj=[float(q.qfq_price(Decimal(str(v)))) for v in ohlc] if q is not None and ohlc else None
   daily.append({'trade_date':day,'qfq_ohlc':adj,'amount':raw.get('amount'),'volume':raw.get('volume'),
                 'adjusted_quality':'READY' if adj is not None else 'UNKNOWN'})
  bars_by[sid]=daily
  source_fields={k:dict(v) for k,v in crow['fields'].items()}
  rp=current_rps.get(sid,{})
  for horizon in (5,20):
   item=rp.get(f'rps{horizon}',{});source_fields[f'rps{horizon}']=dict(value=item.get('value'),quality_state=item.get('quality_state','UNKNOWN'),unknown_reason=item.get('unknown_reason'),contract_id='V4_RPS_PIT_HISTORY_V1')
  old=prior_rps.get(sid,{}).get('rps20',{});now=rp.get('rps20',{})
  delta=now.get('value')-old.get('value') if now.get('quality_state')=='OBSERVED' and old.get('quality_state')=='OBSERVED' else None
  source_fields['rps20_delta3']=dict(value=delta,quality_state='OBSERVED' if delta is not None else 'UNKNOWN',
    unknown_reason=None if delta is not None else 'PRIOR_RPS_ENDPOINT_NOT_ACCEPTED_OR_UNKNOWN',contract_id='V4_RPS_PIT_HISTORY_V1',
    window_start_trade_date=prior_day,window_end_trade_date=TARGET)
  factors.append({**crow,'board_scope':identity_row['board_scope'],'source_security_key':identity_row['source_security_key'],'fields':source_fields})
  if not ready or blocked:unknown_adj+=1
 # Market-relative inputs use the R3 target date Core returns and accepted start-date stock identity cohorts.
 historical=load_rows(market['sources']['historical_universe']['path'])
 hist_by_day=collections.defaultdict(set)
 for row in historical:
  if row['trade_date'] in sessions and row['board_scope'] in ('SH_MAIN','SZ_MAIN','STAR','CHINEXT'):hist_by_day[row['trade_date']].add(row['security_id'])
 for d,node2 in {n['trade_date']:n for n in chain['nodes']}.items():
  if d in sessions:
   for x in read(node2['components']['IDENTITY_UNIVERSE']['artifact_path'])['rows']:
    if x['board_scope'] in ('SH_MAIN','SZ_MAIN','STAR','CHINEXT'):hist_by_day[d].add(x['security_id'])
 by={x['security_id']:x for x in factors}
 for h in (1,5):
  start_day=sessions[sessions.index(TARGET)-h];universe=sorted(hist_by_day[start_day])
  returns={sid:by.get(sid,{}).get('fields',{}).get(f'ret{h}',{}).get('value') for sid in by}
  reference,meta=market_reference(returns,universe)
  for row in factors:
   ret=row['fields'].get(f'ret{h}',{}).get('value');value=ret-reference if ret is not None and reference is not None else None
   row['fields'][f'rel_market_{h}']=dict(value=value,quality_state='OBSERVED' if value is not None else 'UNKNOWN',
      unknown_reason=None if value is not None else 'RETURN_OR_PIT_MARKET_REFERENCE_UNKNOWN',contract_id='MARKET_RELATIVE_REFERENCE_V1',
      window_start_trade_date=start_day,window_end_trade_date=TARGET,reference=meta)
 # Derive exact target-coordinate closed periods from the full accepted raw history.
 # The one-day DM01 period component is only an incremental as-of view, so it cannot
 # replace the V4-04 full historical windows needed for weekly/monthly states.
 from datetime import date
 periods_by=collections.defaultdict(lambda:{'WEEKLY':[],'MONTHLY':[]})
 calendar_periods={'WEEKLY':collections.defaultdict(list),'MONTHLY':collections.defaultdict(list)}
 for day in sessions:
  d=date.fromisoformat(day);calendar_periods['WEEKLY'][d.isocalendar()[:2]].append(day);calendar_periods['MONTHLY'][(d.year,d.month)].append(day)
 for sid,bs in bars_by.items():
  bydate={b['trade_date']:b for b in bs}
  for kind,groups in calendar_periods.items():
   for key,expected_days in sorted(groups.items()):
    # The target week's/month's last session is not known to be closed yet.
    if expected_days[-1] >= TARGET:continue
    present=[bydate[d] for d in expected_days if d in bydate]
    if not present:continue
    unexplained=[d for d in expected_days if d not in bydate and status.get(sid,{}).get(d)!='SUSPENDED']
    adjusted_missing=[d for d in expected_days if d in bydate and bydate[d]['qfq_ohlc'] is None]
    if unexplained:quality='BLOCKED_BY_UNKNOWN_STATUS'
    elif adjusted_missing:quality='BLOCKED_BY_ADJUSTMENT'
    else:quality='CLOSED_ONLY_READY'
    actual=[bydate[d] for d in expected_days if d in bydate and bydate[d]['qfq_ohlc'] is not None]
    periods_by[sid][kind].append({'period_last_session':expected_days[-1],'period_view':'CLOSED_ONLY',
      'period_status':'NO_ACTUAL_BARS' if not actual else quality,'price_basis':'QFQ',
      'close':actual[-1]['qfq_ohlc'][3] if actual and quality=='CLOSED_ONLY_READY' else None,
      'source_daily_digest':digest(canonical([(d,bydate[d]['qfq_ohlc'] if d in bydate else status.get(sid,{}).get(d,'UNKNOWN')) for d in expected_days]))})
 # Build target-date calendars/status and exact V4-04 Profile rows.
 regime=RegimeUI('UNKNOWN','UNKNOWN',None,0,{'reason':'R3_TARGET_DAY_MARKET_REGIME_OWNER_NOT_BOUND'},'REQUIRED_MARKET_AXIS_UNKNOWN')
 sources={'core_owner':ref(core_path),'raw_history':ref(stock['sources']['history']['path']),'target_adjustment':ref(node['components']['ADJUSTED_DAILY']['artifact_path']),
          'target_periods':period_source,'full_history_periods':'RECOMPUTED_FROM_TARGET_COORDINATE_RAW_BARS_AND_ACCEPTED_CALENDAR','trading_status':ref(node['components']['TRADING_STATUS']['artifact_path']),
          'gbbq':gbbq,'rps_current':rps_dates.get(TARGET),'rps_delta3':rps_dates.get(prior_day),'profile_builder':ref('scripts/run_v4_04_full_market_candidate_r4.py')}
 source_digest=digest(canonical(sources));contract_digest=digest(canonical({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in builder.CONTRACT_FILES}))
 profiles=[];state_counts=collections.Counter();datebars=collections.Counter()
 for row in factors:
  sid=row['security_id'];bs=bars_by.get(sid,[]);if_not=[]
  core_dates={b['trade_date'] for b in bs}
  statuses=[(d,'ACTUAL_TRADED' if d in core_dates else status.get(sid,{}).get(d,'UNKNOWN')) for d in sessions if bs and d>=bs[0]['trade_date']]
  bars=[{'trade_date':b['trade_date'],'qfq_close':b['qfq_ohlc'][3] if b['qfq_ohlc'] else None,'qfq_high':b['qfq_ohlc'][1] if b['qfq_ohlc'] else None,
         'qfq_low':b['qfq_ohlc'][2] if b['qfq_ohlc'] else None,'amount':b['amount'],'adjusted_quality':b['adjusted_quality']} for b in bs]
  profiles.append(builder.build_row(row,bars,periods_by[sid]['WEEKLY'],periods_by[sid]['MONTHLY'],statuses,
                {'source_security_key':row['source_security_key']},source_digest,contract_digest,sessions,regime))
  for k,v in profiles[-1]['states'].items():state_counts[f'{k}:{v["value"]}']+=1
  if bs and bs[-1]['trade_date']==TARGET and bs[-1]['adjusted_quality']=='READY':datebars['TARGET_QFQ_READY']+=1
  else:datebars['TARGET_QFQ_UNKNOWN']+=1
 artifact=OUT/f'R3_PROFILE_{TARGET}_CANDIDATE_{REVISION}.jsonl.gz';tmp=artifact.with_suffix(artifact.suffix+'.tmp')
 with tmp.open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0,compresslevel=6) as zipped:
  for row in profiles:zipped.write((json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode())
 os.replace(tmp,artifact)
 outref={'path':artifact.relative_to(ROOT).as_posix(),'bytes':artifact.stat().st_size,'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest()}
 receipt={'contract_id':'R3_V4_04_PROFILE_OWNER_REPLAY_V1','trade_date':TARGET,'owner_contract':'V4_04_CORE_PROFILE_RULES_V1',
   'knowledge_lineage':'RECONSTRUCTED_CORRECTED','AS_RECORDED':False,'formal_acceptance':False,'production_changed':False,'rows':len(profiles),
   'target_qfq_capability':dict(ready=datebars['TARGET_QFQ_READY'],unknown=datebars['TARGET_QFQ_UNKNOWN']),
   'profile_state_counts':dict(state_counts),'owner_artifact':outref,'source_bindings':sources,'source_digest':source_digest,
   'accepted_contracts':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in builder.CONTRACT_FILES},
   'rps_endpoints':{'current':TARGET,'prior_t_minus_3':prior_day,'current_count':len(current_rps),'prior_count':len(prior_rps),
     'provider_head':ref('data/v4/V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1.json'),'historical_first_availability_proven':False},
   'isolated_candidate_only':True,'notes':['No production head or live snapshot mutation.',f'{unknown_adj} target-date QFQ capabilities fail closed.','Regime UI remains UNKNOWN because no exact target-date market-regime owner is bound.']}
 p=OUT/f'R3_PROFILE_{TARGET}_CANDIDATE_RECEIPT_{REVISION}.json';tmp=p.with_suffix('.json.tmp');tmp.write_text(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8');os.replace(tmp,p)
 print(json.dumps({'rows':len(profiles),'target_qfq':dict(datebars),'artifact_sha256':outref['sha256'],'rps_dates':[TARGET,prior_day]},ensure_ascii=False))
if __name__=='__main__':main()
