"""Compare stored chart fields across versions; no adjustment computation."""
import json,gzip,itertools,argparse
from pathlib import Path
from collections import Counter
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json

ROOT=Path('G:/codex work/v4-production-20261012');OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--label',required=True);a=p.parse_args()
    if not a.label.isalnum():raise ValueError('VERSIONED_PROJECTION_REQUIRED')
    out=OUT/('HISTORY_PROJECTION_CONSERVATION_'+a.label+'.json')
    if out.exists():raise ValueError('PRESERVE_PRIOR_PROJECTION')
    run=json.loads(Path(a.run).read_bytes());folder=checked(ROOT,run['candidate']).parent
    replay=json.loads((folder/'owner_v3/CORE_REPLAY.json').read_bytes())
    authority=json.loads((ROOT/'config/core_product_read_authority_r1.json').read_bytes());records=[]
    fields=('trade_date','raw_ohlc','qfq_ohlc','amount','volume')
    for day,binding in authority['dates'].items():
        manifest=json.loads(checked(ROOT,binding).read_bytes());previous=manifest['source_bindings']['history']
        current=next(row['history'] for row in replay['owners'] if row['trade_date']==day)
        differences=0;checks=0;bars_count=0;first=[];byfield=Counter();bysecurity=Counter();coverage=[]
        with gzip.open(checked(ROOT,previous),'rt',encoding='utf8') as old,gzip.open(checked(ROOT,current),'rt',encoding='utf8') as new:
            for left,right in itertools.zip_longest(old,new):
                if left is None or right is None:raise ValueError('HISTORY_SECURITY_DENOMINATOR_CHANGED')
                x,y=json.loads(left),json.loads(right)
                if x['security_id']!=y['security_id']:raise ValueError('HISTORY_SECURITY_ORDER_CHANGED')
                old_bars={b['trade_date']:b for b in x['bars']};new_bars={b['trade_date']:b for b in y['bars']}
                if set(old_bars)!=set(new_bars):coverage.append(dict(security_id=x['security_id'],old_only=sorted(set(old_bars)-set(new_bars)),new_only=sorted(set(new_bars)-set(old_bars))))
                for trade_date in sorted(set(old_bars)&set(new_bars)):
                    xb,yb=old_bars[trade_date],new_bars[trade_date]
                    bars_count+=1
                    for field in fields:
                        checks+=1
                        if xb.get(field)!=yb.get(field):
                            differences+=1;byfield[field]+=1;bysecurity[x['security_id']]+=1
                            if len(first)<40:first.append(dict(security_id=x['security_id'],day=xb['trade_date'],field=field,previous=xb.get(field),current=yb.get(field)))
        row=dict(T0=day,previous=previous,current=current,bars=bars_count,checks=checks,differences=differences,
            differences_by_field=dict(byfield),differences_by_security=dict(bysecurity),first_differences=first,coverage_differences=coverage)
        records.append(row);print(json.dumps(dict(T0=day,bars=bars_count,differences=differences)),flush=True)
    result=dict(contract_id='V4_HISTORY_CONSUMED_PROJECTION_CONSERVATION_R1',acceptance='PASS_COMMON_DATES_ONLY' if all(not row['differences'] for row in records) else 'DIFFERENCES_RETAINED',
        dates=records,fields=list(fields),source_replay=ref(ROOT,folder/'owner_v3/CORE_REPLAY.json'),
        scope='Exact chart consumed fields on common dates only; all coverage differences retained, audit metadata excluded. No numerical producer reexecution.',publication=False)
    atomic_json(OUT,out,result)

if __name__=='__main__':main()
