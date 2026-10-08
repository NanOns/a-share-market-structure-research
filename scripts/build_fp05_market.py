"""Current-session four-axis materialization using accepted inputs and V4 kernels.

Reconstructs a declared successor market path, retaining the original path bytes.
No current membership is applied to historical market returns.
"""
import gzip
import json
import sys
from collections import defaultdict
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from statistics import median, fmean
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from scripts.fp_domain_evidence import enter,operational_path
from workbench_service.production_v4 import frozen_current_reader,reference
from workbench_service.current_v4_context import canonical,digest
from adjustment.tdx_adjustment import build_affine_factors,xrxd_from_gbbq
from tdx.gbbq_reader import read_gbbq
from v4.factors.native import market_axis_primitives,market_trend_axis
from v4.market_regime_ui import project

def verified(binding):
    p=ROOT/binding['path'];assert reference(ROOT,p)['sha256']==binding['sha256'],binding['path'];return p

def main():
    out=enter(5);reader,_=frozen_current_reader(ROOT);contract,_=reader._contract();ctx=reader.load_context()['context'];date=ctx['accepted_trade_date']
    head_binding=ref('data/v4/V4_DATA_ACCEPTED_HEAD.json');assert head_binding['sha256']==ctx['data_head_digest'];head=reader._read(head_binding);chain=reader._read(head['accepted_chain'])
    nodes=[n for n in chain['nodes'] if n['trade_date']<=date]
    execution_path=next((ROOT/'data/v4/source_evidence/dm01_a01_r3/durable_chain_inputs_r2').glob('chain_execution_context*'))
    execution=json.loads(execution_path.read_bytes());assert execution['calendar']['binding']==head['calendar']
    sources={'data_head':head_binding,'accepted_chain':head['accepted_chain'],'execution':ref(execution_path),'projection_adapter':ref('scripts/build_fp05_market.py')}
    history_receipt=ROOT/'reports/v4_05/V4_05_R4_DAILY_HISTORY_RECEIPT.json';hr=json.loads(history_receipt.read_bytes())
    sources['history']=dict(path=hr['artifact_path'],sha256=hr['artifact_sha256']);sources['history_receipt']=ref(history_receipt)
    history=defaultdict(list)
    with gzip.open(verified(sources['history']),'rt',encoding='utf8') as f:
        for line in f:
            row=json.loads(line);d=str(row['trade_date']);d=f'{d[:4]}-{d[4:6]}-{d[6:]}'
            if d<=date:history[row['security_id']].append(dict(trade_date=d,raw_ohlc=row['raw_ohlc'],volume=row['volume'],amount=row['amount'],symbol=row['source_security_key']))
    components={};members={}
    for node in nodes:
        day=node['trade_date'];components[day]={}
        for kind in ('RAW_DAILY','ADJUSTED_DAILY','PRICE_LIMIT','TRADING_STATUS','IDENTITY_UNIVERSE'):
            b=node['components'][kind];binding=dict(path=b['artifact_path'],sha256=b['artifact_sha256']);sources[day+':'+kind]=binding
            rows=json.loads(verified(binding).read_bytes())['rows'];components[day][kind]={r['security_id']:r for r in rows}
        members[day]={sid for sid,r in components[day]['IDENTITY_UNIVERSE'].items() if r.get('board_scope') in ('SH_MAIN','SZ_MAIN','STAR','CHINEXT')}
        for sid,row in components[day]['RAW_DAILY'].items():
            history[sid]=[b for b in history[sid] if b['trade_date']!=day]
            history[sid].append(dict(trade_date=day,raw_ohlc=[str(row[k]) for k in ('open','high','low','close')],volume=row['volume'],amount=row['amount'],symbol=row['source_security_key']))
    gbbq=execution['inputs'][date]['inputs']['GBBQ'];sources['gbbq']=gbbq
    events=defaultdict(list);target=int(date.replace('-',''))
    for e in read_gbbq(verified(gbbq)):
        if e.event_date<=target:events[e.security_id].append(e)
    dispositions=json.loads((ROOT/'config/v4_02_gbbq_price_impact_classification_v1.json').read_bytes())['dispositions']
    sources['adjustment_classification']=ref('config/v4_02_gbbq_price_impact_classification_v1.json')
    for sid,bars in history.items():
        bars.sort(key=lambda b:b['trade_date']);bars[:]=bars[-253:]
        relevant=[e for e in events[bars[-1]['symbol']] if int(bars[0]['trade_date'].replace('-',''))<e.event_date<=target]
        blocked=[e.category for e in relevant if dispositions.get(str(e.category),{}).get('formal_disposition','UNKNOWN_PRICE_IMPACT') in ('PRICE_AFFECTING_UNSUPPORTED','UNKNOWN_PRICE_IMPACT')]
        factors=build_affine_factors([int(b['trade_date'].replace('-','')) for b in bars],[xrxd_from_gbbq(e) for e in relevant if e.category==1]) if not blocked else {}
        for b in bars:
            factor=factors.get(int(b['trade_date'].replace('-','')))
            b['qfq_ohlc']=[str(factor.qfq_price(Decimal(x))) for x in b['raw_ohlc']] if factor else None
            b['adjustment_reason']='UNSUPPORTED_OR_UNKNOWN_PRICE_IMPACT' if blocked else None
    sessions=execution['calendar']['session_dates'];sources['calendar']=head['calendar'];idx=sessions.index(date);prior3=sessions[idx-3]
    universe_path=ROOT/'data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz';sources['historical_universe']=ref(universe_path)
    with gzip.open(universe_path,'rt',encoding='utf8') as f:
        for line in f:
            r=json.loads(line)
            if r['trade_date']==prior3 and r['board_scope'] in ('SH_MAIN','SZ_MAIN','STAR','CHINEXT'):members.setdefault(prior3,set()).add(r['security_id'])
    returns=defaultdict(dict);ratios=defaultdict(dict)
    for sid,bars in history.items():
        by={b['trade_date']:b for b in bars}
        for day in [prior3,*components]:
            i=sessions.index(day);b=by.get(day);prev=by.get(sessions[i-1])
            if b and prev and b['qfq_ohlc'] and prev['qfq_ohlc'] and float(prev['qfq_ohlc'][3])>0:
                returns[day][sid]=float(b['qfq_ohlc'][3])/float(prev['qfq_ohlc'][3])-1
            prior=[x for x in bars if x['trade_date']<day][-20:]
            if b and b['qfq_ohlc'] and len(prior)==20 and all(x['amount'] is not None and x['amount']>=0 for x in prior):
                # Missing sessions are not silently treated as suspensions.
                actual={x['trade_date'] for x in prior}
                needed=[s for s in sessions if prior[0]['trade_date']<=s<day]
                if set(needed)==actual and fmean(x['amount'] for x in prior)>0:ratios[day][sid]=b['amount']/fmean(x['amount'] for x in prior)
    path_source=ROOT/'reports/v4_03/staging/V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R3.jsonl.gz';sources['prior_market_path']=ref(path_source)
    prior_path=[json.loads(l) for l in gzip.open(path_source,'rt',encoding='utf8')]
    assert prior_path[-1]['trade_date']==prior3 and prior_path[-1]['level'] is not None
    # Explicit new version carries a frozen accepted prefix and links every bridge session.
    path_contract=json.loads((ROOT/'config/v4_market_path_successor_contract_v1.json').read_bytes());sources['path_contract']=ref('config/v4_market_path_successor_contract_v1.json')
    levels=[r['level'] for r in prior_path];level=levels[-1];bridge=[];previous=prior3
    for day in components:
        start=members[previous];valid=sorted(start&returns[day].keys());coverage=len(valid)/len(start)
        ret=fmean(returns[day][sid] for sid in valid) if coverage>=path_contract['minimum_bridge_coverage'] else None
        level=level*(1+ret) if level is not None and ret is not None else None;levels.append(level)
        bridge.append(dict(trade_date=day,start_session=previous,start_member_count=len(start),evaluable_count=len(valid),coverage=coverage,return_value=ret,level=level,start_member_digest=digest(canonical(sorted(start)))))
        previous=day
    current=members[date];previous=sessions[idx-1]
    common=current&members[prior3];valid=sorted(common&returns[date].keys()&returns[prior3].keys())
    now=sum(returns[date][s]>0 for s in valid)/len(valid) if valid else None;old=sum(returns[prior3][s]>0 for s in valid)/len(valid) if valid else None
    def limits(day):return {s:r['limit_status'] for s,r in components[day]['PRICE_LIMIT'].items() if s in members[day] and r['limit_status'] in ('LIMIT_UP','LIMIT_DOWN','NOT_LIMIT')}
    lim=limits(date);plim=limits(previous);stressset=current&members[previous]&lim.keys()&plim.keys()
    identity=dict(trade_date=date,market_calendar_id=head['calendar']['sha256'],market_snapshot_id=digest(canonical(sorted(current))),adjustment_basis_id=gbbq['sha256'],input_source_digest=digest(canonical(sources)))
    participation=[v for s,v in ratios[date].items() if s in current]
    raw=dict(breadth_t=now,breadth_t_minus_3=old,breadth_delta3=now-old if valid else None,breadth_evaluable_count=len(valid),breadth_common_count=len(common),participation_evaluable_count=len(participation),participation_median_amount_ratio20=median(participation) if participation else None,universe_count=len(current),limit_evaluable_count=len(lim),limit_coverage=len(lim)/len(current),stress_ratio=sum(v=='LIMIT_DOWN' for v in lim.values())/len(lim) if lim else None,stress_common_count=len(stressset),stress_same_member_prior_ratio=sum(plim[s]=='LIMIT_DOWN' for s in stressset)/len(stressset) if stressset else None,stress_same_member_current_ratio=sum(lim[s]=='LIMIT_DOWN' for s in stressset)/len(stressset) if stressset else None)
    axes=market_axis_primitives(breadth=raw['breadth_delta3'],participation=raw['participation_median_amount_ratio20'],limit_coverage=raw['limit_coverage'],stress_ratio=raw['stress_ratio'],prior_stress_ratio=raw['stress_same_member_prior_ratio'],stress_change_current_ratio=raw['stress_same_member_current_ratio'],stress_change_current_provided=True,**identity)
    ma=lambda xs:fmean(xs) if len(xs)==20 and all(x is not None for x in xs) else None
    trend=market_trend_axis(index_close=level,index_ma20=ma(levels[-20:]),index_ma20_t_minus_5=ma(levels[-25:-5]),**identity)
    row=dict(trade_date=date,trend_axis=trend['trend_axis'],**{k:axes[k] for k in ('breadth_axis','participation_axis','stress_level','stress_change')})
    oldregime=[json.loads(l) for l in gzip.open(ROOT/'reports/v4_03/staging/V4_03_MARKET_REGIME_NATIVE_CANDIDATE_R3.jsonl.gz','rt',encoding='utf8')]
    # No fabricated intermediate axes: uncomputed bridge dates reset hysteresis explicitly.
    gaps=[dict(trade_date=day) for day in components if day!=date]
    regime=asdict(project([*oldregime,*gaps,row])[date])
    payload=dict(contract_id='FP05_CURRENT_MARKET_FOUR_AXES_V1',trade_date=date,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,sources=sources,raw=raw,axes=axes,trend=trend,regime=regime,comparison_trade_date=prior3,stress_comparison_trade_date=previous,path_successor=dict(series_version='DAILY_REBALANCED_RESEARCH_INDEX_FP05_V2',prefix=sources['prior_market_path'],bridge=bridge,old_series_modified=False),row=row)
    folder=ROOT/'data/v4/fp05_market'/digest(canonical(payload));write(folder/'market.json',payload)
    # Retain corrected coordinate bars for subsequent FP07, separately from PIT research history.
    historyfile=folder/'history.jsonl.gz';tmp=historyfile.with_suffix('.tmp')
    with tmp.open('wb') as rawstream,gzip.GzipFile(fileobj=rawstream,mode='wb',filename='',mtime=0) as f:
        for sid,bars in sorted(history.items()):f.write(canonical(dict(security_id=sid,bars=bars))+b'\n')
    tmp.replace(historyfile)
    authority=dict(contract_id='FP05_MARKET_AUTHORITY_V1',trade_date=date,market=ref(folder/'market.json'),history=ref(historyfile),input_data_head=head_binding)
    write(operational_path('v4_market_operational_authority_v1.json',for_write=True),authority)
    write(out/'SOURCE_AND_VALUE_READBACK.json',dict(authority=authority,raw=raw,row=row,regime=regime,bridge=bridge,qa='NATIVE_KERNELS_BOUND_TO_EXACT_REAL_INPUTS',old_path_modified=False))
    print(json.dumps(dict(status='MATERIALIZED',axes=row,regime=regime['value'],history_entities=len(history)),ensure_ascii=False))
if __name__=='__main__':main()
