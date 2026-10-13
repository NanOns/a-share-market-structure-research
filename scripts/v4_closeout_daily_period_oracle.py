"""Independent new-session period output checks, with no producer invocation."""
import argparse,json,gzip,hashlib
from pathlib import Path
from datetime import date
from decimal import Decimal
from collections import defaultdict
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json

ROOT=Path('G:/codex work/v4-production-20261012')
OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')

def rows(binding):
    with gzip.open(checked(ROOT,binding),'rt',encoding='utf8') as stream:
        return [json.loads(line) for line in stream]

def period_key(day,kind):
    if kind=='MONTHLY':return day[:7]
    y,w,_=date.fromisoformat(day).isocalendar();return f'{y}-W{w:02d}'

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--label',required=True);a=p.parse_args()
    if not a.label.isalnum():raise ValueError('VERSIONED_ORACLE_REQUIRED')
    out=OUT/('DAILY_PERIOD_ORACLE_'+a.label+'.json')
    if out.exists():raise ValueError('PRESERVE_PRIOR_ORACLE')
    runpath=Path(a.run).resolve()
    if not runpath.is_relative_to(OUT):raise ValueError('SEALED_RUN_SCOPE_REQUIRED')
    run=json.loads(runpath.read_bytes());candidate=json.loads(checked(ROOT,run['candidate']).read_bytes())
    day=candidate['accepted_trade_date'];folder=checked(ROOT,run['candidate']).parent
    replay=json.loads((folder/'owner_v3/CORE_REPLAY.json').read_bytes())
    owner=next(row for row in replay['owners'] if row['trade_date']==day)
    profile=json.loads((folder/'owner_v3/PROFILE_STRUCTURE_REPLAY.json').read_bytes())
    status={row['owner']['trade_date']:{x['security_id']:x['status'] for x in rows(row['owner']['status'])} for row in profile['owners']}
    # Calendar and identity are immutable source documents, not period algorithms.
    from workbench_analysis.market_source_acquisition import official_sessions
    calendar=official_sessions(ROOT)
    identities=json.loads(checked(ROOT,owner['sources']['identity']).read_bytes())['rows']
    identity={row['security_id']:row for row in identities}
    first_month=min(d for d in calendar if d[:7]==day[:7]);checks=0;errors=[];differences=0;denominator={}
    periods={}
    for domain in ('period_raw','period_adjusted'):
        grouped=defaultdict(list);values=rows(candidate['owners'][day][domain])
        for row in values:grouped[row['security_id']].append(row)
        periods[domain]=grouped;denominator[domain]=dict(securities=len(grouped),rows=len(values))
    def compare(actual,expected,scope):
        nonlocal checks,differences
        checks+=1
        equal=Decimal(str(actual))==expected if actual is not None and isinstance(expected,Decimal) else actual==expected
        if not equal:
            differences+=1
            if len(errors)<40:errors.append(dict(scope=scope,actual=actual,expected=str(expected) if isinstance(expected,Decimal) else expected))
    seen=set()
    with gzip.open(checked(ROOT,owner['history']),'rt',encoding='utf8') as stream:
        for line in stream:
            item=json.loads(line);sid=item['security_id'];seen.add(sid)
            start=max(first_month,identity[sid]['list_date']);dates=[d for d in calendar if start<=d<=day]
            bars={b['trade_date']:b for b in item['bars'] if start<=b['trade_date']<=day}
            groups={(kind,period_key(d,kind)) for kind in ('WEEKLY','MONTHLY') for d in dates}
            for domain,prices_key in (('period_raw','raw_ohlc'),('period_adjusted','qfq_ohlc')):
                actual_rows=periods[domain].get(sid,[])
                compare({(r['period_type'],r['period_key']) for r in actual_rows},groups,[sid,domain,'period_denominator'])
                for row in actual_rows:
                    cutoff=row['as_of_date'];kind=row['period_type'];pk=row['period_key']
                    required=[d for d in dates if d<=cutoff and period_key(d,kind)==pk]
                    actual=[bars[d] for d in required if d in bars]
                    missing=[d for d in required if d not in bars]
                    suspended=sum(status.get(d,{}).get(sid)=='SUSPENDED' for d in missing)
                    unknown=len(missing)-suspended
                    blocked_adjustment=any(not bar.get(prices_key) for bar in actual)
                    prices=[list(map(lambda v:Decimal(str(v)),bar[prices_key])) for bar in actual if bar.get(prices_key)]
                    expected_prices=[None]*4 if blocked_adjustment or not prices else [prices[0][0],max(v[1] for v in prices),min(v[2] for v in prices),prices[-1][3]]
                    fields=dict(zip(('open','high','low','close'),expected_prices))
                    fields.update(actual_count=len(actual),calendar_count=len(required),unknown_count=unknown,suspended_count=suspended,data_gap_count=0,
                        volume=sum(bar['volume'] for bar in actual),amount=sum(float(bar['amount']) for bar in actual),
                        price_basis='RAW' if domain=='period_raw' else 'QFQ',first_source_date=actual[0]['trade_date'] if actual else None,
                        max_source_date=actual[-1]['trade_date'] if actual else None)
                    fields['period_status']='BLOCKED_BY_ADJUSTMENT' if blocked_adjustment else 'BLOCKED_BY_UNKNOWN_STATUS' if unknown else 'NO_ACTUAL_BARS' if not actual else 'CLOSED_ONLY_READY' if row['period_view']=='CLOSED_ONLY' else 'AS_OF_PARTIAL_READY'
                    for field,value in fields.items():compare(row.get(field),value,[sid,domain,pk,field])
            if len(seen)%1000==0:print(json.dumps(dict(securities=len(seen),checks=checks,differences=differences)),flush=True)
    for domain in periods:
        if set(periods[domain])!=seen:raise ValueError('PERIOD_SECURITY_DENOMINATOR_MISMATCH')
    result=dict(contract_id='V4_DAILY_PERIOD_INDEPENDENT_ORACLE_R1',target_session=day,acceptance='PASS' if not differences else 'FAIL',
        owners={domain:candidate['owners'][day][domain] for domain in periods},input_history=owner['history'],verifier=ref(Path.cwd(),Path(__file__).resolve()),
        checks=checks,differences=differences,errors=errors,denominator=denominator,
        scope='New dated RAW/QFQ current-month and week period outputs; existing prior full-history PASS evidence not rerun',
        numerical_producer_recomputed=False,publication=False,source_candidate=run['candidate'])
    atomic_json(OUT,out,result);print(json.dumps(dict(acceptance=result['acceptance'],checks=checks,differences=differences)),flush=True)
    return int(bool(differences))

if __name__=='__main__':raise SystemExit(main())
