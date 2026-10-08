"""Recompute dated Core inputs and sector native facts with existing kernels.

No prior sector membership is manufactured. History-dependent rotation remains
unavailable where the first accepted membership is the target session.
"""
import gzip,json,sys,importlib.util
from collections import defaultdict,Counter
from dataclasses import asdict
from datetime import date as Date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from scripts.fp_domain_evidence import enter,operational_path
from scripts.build_fp05_market import verified
from workbench_service.production_v4 import frozen_current_reader
from workbench_service.current_v4_context import canonical,digest
from v4.factors.core import Bar,Observation,compute_core,rps_midrank,market_reference
from v4.market_regime_ui import RegimeUI
from sector.native_r5 import build_native

def compress(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp')
    with tmp.open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0) as f:
        for row in rows:f.write(canonical(row)+b'\n')
    tmp.replace(path);return ref(path)

def periods(bars,kind,target):
    groups=defaultdict(list)
    for b in bars:
        day=Date.fromisoformat(b['trade_date']);key=day.isocalendar()[:2] if kind=='WEEKLY' else (day.year,day.month)
        groups[key].append(b)
    records=[];keys=sorted(groups)
    for key in keys:
        group=groups[key]
        # Last observed weekly/monthly bucket is forming unless its closure is
        # separately supplied by the accepted period producer.
        if key==keys[-1]:continue
        records.append(dict(period_last_session=group[-1]['trade_date'],period_view='CLOSED_ONLY',period_status='CLOSED_ONLY_READY',price_basis='QFQ',close=float(group[-1]['qfq_ohlc'][3]) if all(b['qfq_ohlc'] for b in group) else None,source_daily_digest=digest(canonical(group))))
    return records

def main():
    out=enter(6);r,_=frozen_current_reader(ROOT);context=r.load_context();contract,_=r._contract()
    target=context['context']['accepted_trade_date'];a=json.loads((operational_path('v4_market_operational_authority_v1.json')).read_bytes());assert a['trade_date']==target
    market=json.loads(verified(a['market']).read_bytes());sources=dict(history=a['history'],market=a['market'],membership=contract['sources']['membership'],projection_adapter=ref('scripts/build_fp06_sector.py'))
    sessions=json.loads(verified(market['sources']['calendar']).read_bytes())['session_dates'];sessions=[s for s in sessions if s<=target]
    identity=json.loads(verified(market['sources'][target+':IDENTITY_UNIVERSE']).read_bytes())['rows'];universe={x['security_id']:x for x in identity}
    statuses=defaultdict(dict)
    statuspath=ROOT/'data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz';sources['historical_status']=ref(statuspath)
    with gzip.open(statuspath,'rt',encoding='utf8') as f:
        for line in f:
            x=json.loads(line)
            if x['status']=='SUSPENDED':statuses[x['security_id']][x['trade_date']]='SUSPENDED'
    for key,b in market['sources'].items():
        if key.endswith(':TRADING_STATUS'):
            for x in json.loads(verified(b).read_bytes())['rows']:statuses[x['security_id']][x['trade_date']]=x['status']
    data={};factors=[]
    with gzip.open(verified(a['history']),'rt',encoding='utf8') as f:
        for line in f:
            row=json.loads(line);sid=row['security_id']
            if sid not in universe:continue
            bars=row['bars'];data[sid]=bars;by={b['trade_date']:b for b in bars};observations=[]
            for day in sessions:
                if day<bars[0]['trade_date']:continue
                b=by.get(day)
                if b and b['qfq_ohlc']:
                    observations.append(Observation(day,'ACTUAL',Bar(*map(float,b['qfq_ohlc']),float(b['amount']),float(b['volume']),market['sources']['gbbq']['sha256'],a['history']['sha256'])))
                else:observations.append(Observation(day,'ADJUSTMENT_UNKNOWN' if b else 'CONFIRMED_SUSPENSION' if statuses[sid].get(day)=='SUSPENDED' else 'UNKNOWN'))
            fields={k:asdict(v) for k,v in compute_core(observations,sid,asof=target).items()}
            factors.append(dict(security_id=sid,source_security_key=universe[sid]['source_security_key'],board_scope=universe[sid]['board_scope'],trade_date=target,fields=fields))
    factorby={x['security_id']:x for x in factors};members=sorted(universe)
    for horizon in (5,20):
        scores,coverage=rps_midrank({s:factorby[s]['fields'].get(f'ret{horizon}',{}).get('value') for s in factorby},members)
        for sid,row in factorby.items():row['fields'][f'rps{horizon}']=dict(value=scores[sid],quality_state='OBSERVED' if scores[sid] is not None else 'UNKNOWN',unknown_reason=None if scores[sid] is not None else 'RETURN_OR_UNIVERSE_UNKNOWN',contract_id='RPS_MIDRANK_V1',parameter_set_id='V4_03_CORE_FACTOR_PARAMETER_SET_V1',window_identity=digest(canonical([target,horizon,members])),denominator=coverage['universe_count'])
    wanted={h:sessions[sessions.index(target)-h] for h in (1,3,5)};start={d:set() for d in wanted.values()}
    with gzip.open(verified(market['sources']['historical_universe']),'rt',encoding='utf8') as f:
        for line in f:
            x=json.loads(line)
            if x['trade_date'] in start and x['board_scope'] in ('SH_MAIN','SZ_MAIN','STAR','CHINEXT'):start[x['trade_date']].add(x['security_id'])
    for key,b in market['sources'].items():
        if key.endswith(':IDENTITY_UNIVERSE') and key.split(':')[0] in start:
            start[key.split(':')[0]]={x['security_id'] for x in json.loads(verified(b).read_bytes())['rows'] if x['board_scope'] in ('SH_MAIN','SZ_MAIN','STAR','CHINEXT')}
    for h,day in wanted.items():
        reference,meta=market_reference({s:factorby[s]['fields'].get(f'ret{h}',{}).get('value') for s in factorby},sorted(start[day]))
        for sid,row in factorby.items():
            ret=row['fields'].get(f'ret{h}',{}).get('value');v=ret-reference if ret is not None and reference is not None else None
            row['fields'][f'rel_market_{h}']=dict(value=v,quality_state='OBSERVED' if v is not None else 'UNKNOWN',unknown_reason=None if v is not None else 'RETURN_OR_PIT_MARKET_REFERENCE_UNKNOWN',contract_id='MARKET_RELATIVE_REFERENCE_V1',parameter_set_id='V4_03_CORE_FACTOR_PARAMETER_SET_V1',window_identity=digest(canonical([day,target,sorted(start[day])])),denominator=len(start[day]),reference=meta)
    for row in factors:
        for key in ('rps5_delta1','rps5_delta3','rps20_delta3'):row['fields'][key]=dict(value=None,quality_state='UNKNOWN',unknown_reason='PRIOR_PUBLISHED_RPS_NOT_BOUND_NOT_BACKFILLED',contract_id='RPS_MIDRANK_V1')
    spec=importlib.util.spec_from_file_location('fp06_unchanged_core_builder',ROOT/'scripts/run_v4_04_full_market_candidate_r4.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder);builder.CUTOFF=target
    regime=RegimeUI(**market['regime']);profiles=[];source_digest=digest(canonical(sources));contract_digest=digest(canonical({p:ref(p) for p in builder.CONTRACT_FILES}))
    for row in factors:
        sid=row['security_id'];bs=data[sid];bars=[dict(trade_date=b['trade_date'],qfq_close=float(b['qfq_ohlc'][3]) if b['qfq_ohlc'] else None,qfq_high=float(b['qfq_ohlc'][1]) if b['qfq_ohlc'] else None,qfq_low=float(b['qfq_ohlc'][2]) if b['qfq_ohlc'] else None,amount=b['amount'],adjusted_quality='READY' if b['qfq_ohlc'] else 'UNKNOWN') for b in bs]
        dates={b['trade_date'] for b in bs};status=[(d,'ACTUAL_TRADED' if d in dates else statuses[sid].get(d,'UNKNOWN')) for d in sessions if d>=bs[0]['trade_date']]
        profiles.append(builder.build_row(row,bars,periods(bs,'WEEKLY',target),periods(bs,'MONTHLY',target),status,{'source_security_key':row['source_security_key']},source_digest,contract_digest,sessions,regime))
    current={}
    for row in factors:
        sid=row['security_id'];fields={k:dict(value=v.get('value'),quality='ACCEPTED' if v['quality_state']=='OBSERVED' else 'UNKNOWN',max_source_date=target) for k,v in row['fields'].items()};last=data[sid][-1];at_target=last['trade_date']==target
        fields['amount']=dict(value=last['amount'] if at_target else None,quality='ACCEPTED' if at_target else 'UNKNOWN',max_source_date=target)
        fields['close']=dict(value=float(last['qfq_ohlc'][3]) if at_target and last['qfq_ohlc'] else None,quality='ACCEPTED' if at_target and last['qfq_ohlc'] else 'UNKNOWN',max_source_date=target)
        current[sid]=dict(trade_date=target,fields=fields,price_basis_id=market['sources']['gbbq']['sha256'])
    memberships=[json.loads(l) for l in gzip.open(verified(sources['membership']),'rt',encoding='utf8')];snapshot=memberships[0]['snapshot_id'];params=json.loads((ROOT/'config/v4_08_algorithm_parameter_set_r5.json').read_bytes())
    sources.update(core_kernel=ref('src/v4/factors/core.py'),profile_kernel=ref('scripts/run_v4_04_full_market_candidate_r4.py'),native_kernel=ref('src/sector/native_r5.py'),sector_parameters=ref('config/v4_08_algorithm_parameter_set_r5.json'))
    folder=ROOT/'data/v4/fp06_sector'/digest(canonical(sources));native=build_native(memberships,current,target=target,snapshot_id=snapshot,publication_id=folder.name,parameter_set=params,source_bindings=sources,max_source_date=target)
    authority=dict(contract_id='FP06_SECTOR_OPERATIONAL_AUTHORITY_V1',trade_date=target,input_data_head=a['input_data_head'],sources=sources,
        factors=compress(folder/'factors.jsonl.gz',factors),profiles=compress(folder/'profiles.jsonl.gz',profiles),native=compress(folder/'native.jsonl.gz',native),
        quality='FIELD_LOCAL_DEGRADED',history_claim='CURRENT_MEMBERSHIP_NOT_REPLAYED_AS_PRIOR',profile_period_policy='LAST_FORMING_BUCKET_EXCLUDED')
    write(operational_path('v4_sector_operational_authority_v1.json',for_write=True),authority)
    known=Counter(k for row in native for k,v in row['fields'].items() if v['value'] is not None)
    write(out/'REAL_MATERIALIZATION.json',dict(authority=authority,core_rows=len(factors),profile_rows=len(profiles),sectors=len(native),known_native_fields=dict(known),prior_membership_fabricated=False))
    print(json.dumps(dict(status='MATERIALIZED',core_rows=len(factors),sectors=len(native),known_native_fields=dict(known)),ensure_ascii=False))
if __name__=='__main__':main()
