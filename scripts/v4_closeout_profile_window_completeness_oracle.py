"""Independent Profile daily window availability and metadata, retaining known arithmetic PASS."""
import json,hashlib
from pathlib import Path
from collections import Counter
from scripts.v4_closeout_profile_rule_oracle import ROOT,OUT
from scripts.v4_closeout_core_uncovered_numeric_oracle import jsonlines
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json

def main():
    target=OUT/'PROFILE_WINDOW_COMPLETENESS_ORACLE_R6_R1.json'
    if target.exists():raise ValueError('PRESERVE_WINDOW_ORACLE')
    prep=json.loads((OUT/'SEALED_METADATA_CONSERVATION_R6_R3.json').read_bytes());candidate=json.loads(checked(ROOT,prep['candidate']).read_bytes());day=candidate['accepted_trade_date']
    diagnostic=json.loads(checked(ROOT,candidate['owners'][day]['diagnostic']).read_bytes());m=json.loads(checked(ROOT,diagnostic['structure_manifest']).read_bytes());owner=m['owner_inputs']
    from workbench_analysis.market_source_acquisition import official_sessions
    calendar=official_sessions(ROOT);historical=json.loads((ROOT/'config/v4_sector_operational_authority_v1.json').read_bytes())['sources']['historical_status'];statuses={(r['security_id'],r['trade_date']):r['status'] for r in jsonlines(checked(ROOT,historical))}
    ids={r['source_security_key'].lower():r['security_id'] for r in json.loads(checked(ROOT,owner['sources']['identity']).read_bytes())['rows']}
    folder=(ROOT/owner['history']['path']).parents[3];acquisition=folder/'sources/acquisition.json';acq=json.loads(acquisition.read_bytes());source_refs=[ref(ROOT,acquisition),historical]
    for query in acq['queries']:
        if query.get('method')!='query_daily_history_k_AStock' or not query.get('path'):continue
        p=Path(query['path']);p=p if p.is_absolute() else ROOT/p
        if not p.resolve().is_relative_to(ROOT.resolve()):
            normalized=query['path'].replace(chr(92),'/');tail=normalized.split('/docs/evidence/',1)
            if len(tail)!=2:raise ValueError('STATUS_SOURCE_ESCAPE')
            p=ROOT/'docs/evidence'/tail[1]
        raw=p.read_bytes()
        if query.get('hash') and hashlib.sha256(json.dumps(json.loads(raw)['rows'],sort_keys=True).encode()).hexdigest()!=query['hash']:raise ValueError('STATUS_SOURCE_HASH_MISMATCH')
        if not query.get('hash') and not p.resolve().is_relative_to(folder.resolve()):raise ValueError('UNBOUND_CURRENT_STATUS_SOURCE')
        d=query['params'].get('date',query['params'].get('day'));source_refs.append(ref(ROOT,p))
        for r in json.loads(p.read_bytes()).get('rows',[]):
            sid=ids.get(r['code'].lower())
            if sid:statuses[sid,d]='SUSPENDED' if r.get('tradestatus')=='0' else 'ACTUAL_TRADED'
    core={r['security_id']:r['fields'] for r in jsonlines(checked(ROOT,owner['core']))};profiles={r['security_id']:r for r in jsonlines(checked(ROOT,candidate['owners'][day]['profile']))};counts=Counter();errors=[];error_count=0
    def check(sid,name,key,actual,expected):
        nonlocal error_count
        counts[key]+=1
        if actual!=expected:
            error_count+=1
            if len(errors)<100:errors.append(dict(security_id=sid,field=name,key=key,actual=actual,expected=expected))
    for hist in jsonlines(checked(ROOT,owner['history'])):
        sid=hist['security_id'];bars=hist['bars'];actual={b['trade_date'] for b in bars};latest=bars[-1] if bars else None;current=bool(latest and latest['trade_date']==day and latest['qfq_ohlc']);fields=core[sid]
        for name,cell in profiles[sid]['derived_fields'].items():
            if name in ('ma10','pos250','minimum_liquidity'):
                n={'ma10':10,'pos250':250,'minimum_liquidity':20}[name];window=bars[-n-1:-1] if name=='minimum_liquidity' and current else [] if name=='minimum_liquidity' else bars[-n:]
                start=window[0]['trade_date'] if window else None;end=window[-1]['trade_date'] if window else None;dates=[d for d in calendar if start is not None and start<=d<=end]
                dated=[(d,'ACTUAL_TRADED' if d in actual else statuses.get((sid,d),'UNKNOWN')) for d in dates];status_ok=bool(window) and all(st in ('ACTUAL_TRADED','SUSPENDED') for d,st in dated) and {d for d,st in dated if st=='ACTUAL_TRADED'}=={b['trade_date'] for b in window}
                ready=current and len(window)==n and status_ok and (all(isinstance(b['amount'],(int,float)) for b in window) if name=='minimum_liquidity' else all(b['qfq_ohlc'] for b in window))
                if name=='pos250' and ready:ready=max(b['qfq_ohlc'][1] for b in window)>min(b['qfq_ohlc'][2] for b in window)
                reason=None if ready else {'ma10':'MA10_WINDOW_OR_ENDPOINT_UNAVAILABLE','pos250':'POS250_WINDOW_OR_DENOMINATOR_UNAVAILABLE','minimum_liquidity':'PRIOR20_AMOUNT_UNAVAILABLE'}[name]
                metadata=dict(actual_count=len(window),calendar_span=len(dates),suspended_count=sum(st=='SUSPENDED' for d,st in dated),window_start_trade_date=start,window_end_trade_date=end)
            else:
                atr=fields['atr20'];other=fields['ma20' if name=='bias20_atr' else 'prior_high20'];ready=current and atr['quality_state']=='OBSERVED' and isinstance(atr['value'],(int,float)) and atr['value']>0 and other['quality_state']=='OBSERVED' and other['value'] is not None
                reason=None if ready else 'ATR_OR_PRICE_INPUT_UNAVAILABLE';metadata=dict(actual_count=1,calendar_span=1,suspended_count=0,window_start_trade_date=latest['trade_date'] if latest else None,window_end_trade_date=day)
            for key,wanted in dict(metadata,quality='OBSERVED' if ready else 'UNKNOWN',unknown_reason=reason).items():check(sid,name,key,cell.get(key),wanted)
            if not ready:check(sid,name,'unknown_value',cell['value'],None)
    result=dict(contract_id='V4_CURRENT_PROFILE_WINDOW_COMPLETENESS_INDEPENDENT_ORACLE_R1',acceptance='PASS_PROFILE_DAILY_WINDOW_SCOPE' if not error_count else 'FAIL',T0=day,candidate=prep['candidate'],history=owner['history'],profile=candidate['owners'][day]['profile'],status_sources=source_refs,checks=dict(counts),check_count=sum(counts.values()),error_count=error_count,first_errors=errors,known_arithmetic_pass_reexecuted=False,primary_profile_primitives_imported=False,scope='Five daily primitive availability, calendar/status window and UNKNOWN metadata. Closed-period primitives remain separate.')
    atomic_json(OUT,target,result);print(json.dumps(dict(acceptance=result['acceptance'],checks=result['check_count'],errors=error_count)))
if __name__=='__main__':main()
