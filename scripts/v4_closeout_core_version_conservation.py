"""Compare existing dated Core cells; never reruns a numerical producer."""
import gzip,json,itertools,argparse,os
from pathlib import Path
from collections import Counter
from workbench_analysis.r43_owner_replay import checked,ref

ROOT=Path('G:/codex work/v4-production-20261012')
OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')

def main():
    p=argparse.ArgumentParser();p.add_argument('--replay',required=True);p.add_argument('--label',required=True);a=p.parse_args()
    if not a.label.isalnum():raise ValueError('VERSIONED_CONSERVATION_LABEL_REQUIRED')
    out=OUT/('CORE_VERSION_CONSERVATION_'+a.label+'.json')
    if out.exists():raise ValueError('PRESERVE_PRIOR_CONSERVATION')
    head_path=ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';before=head_path.read_bytes();head=json.loads(before)
    replay_path=(ROOT/a.replay).resolve()
    if not replay_path.is_relative_to(ROOT):raise ValueError('REPLAY_OUTSIDE_ROOT')
    replay=json.loads(replay_path.read_bytes());records=[];differences=[];count=0;byfield=Counter()
    for day in head['published_sessions']:
        prior=head['owners'][day]['core'];current=next(row['core'] for row in replay['owners'] if row['trade_date']==day)
        securities=0
        with gzip.open(checked(ROOT,prior),'rt',encoding='utf8') as old,gzip.open(checked(ROOT,current),'rt',encoding='utf8') as new:
            for left,right in itertools.zip_longest(old,new):
                if left is None or right is None:raise ValueError('CORE_CONSERVATION_ROW_DENOMINATOR_CHANGED:'+day)
                x,y=json.loads(left),json.loads(right)
                if x['security_id']!=y['security_id']:raise ValueError('CORE_CONSERVATION_ID_ORDER_CHANGED:'+day)
                securities+=1
                for field in sorted(set(x['fields'])|set(y['fields'])):
                    count+=1
                    keys=('value','unit','quality_state','unknown_reason')
                    previous={k:x['fields'].get(field,{}).get(k) for k in keys}
                    actual={k:y['fields'].get(field,{}).get(k) for k in keys}
                    if previous!=actual:
                        byfield[field]+=1;differences.append(dict(day=day,security_id=x['security_id'],field=field,previous=previous,current=actual))
        records.append(dict(T0=day,previous=prior,current=current,securities=securities))
    if head_path.read_bytes()!=before:raise ValueError('CORE_CONSERVATION_HEAD_CHANGED')
    result=dict(contract_id='V4_CORE_DATED_VERSION_CONSERVATION_R1',acceptance='PASS' if not differences else 'DIFFERENCES_RETAINED',
        scope='Existing five dated Core output cells only; excludes history prices, Profile/Sector/Focus, active consumers and publication',
        cells=count,difference_count=len(differences),differences_by_field=dict(byfield),differences=differences,dates=records,
        existing_head=ref(ROOT,head_path),new_replay=ref(ROOT,replay_path),numerical_recomputed=False,tolerance_used=False,publication=False)
    temp=out.with_suffix('.tmp');temp.write_text(json.dumps(result,indent=2),encoding='utf8');os.replace(temp,out)
    print(json.dumps({k:result[k] for k in ('acceptance','cells','difference_count','differences_by_field')}))

if __name__=='__main__':main()
