"""R4.3 actual stock, market and retrospective Focus producer entry."""
import csv, hashlib, json, os, sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.r43_owner_replay import OUT, load, checked, gzrows, ref
from workbench_analysis.market_source_acquisition import write
def lineage():
    out=ROOT/OUT;profiles=load(out/'PROFILE_STRUCTURE_REPLAY.json');records=[]
    def emit(day,family,field,cells,source):
        count=Counter()
        for c in cells:
            value=c.get('value');quality=c.get('quality_state',c.get('quality'))
            reason=c.get('unknown_reason',c.get('reason'))
            known=value not in (None,'UNKNOWN') and quality not in ('UNKNOWN',)
            count[('KNOWN' if known else 'UNKNOWN',json.dumps(reason,ensure_ascii=False,sort_keys=True) if not known else '')]+=1
        for (q,r),n in count.items():records.append(dict(trade_date=day,family=family,field=field,quality=q,reason=r,count=n,source_path=source['path'],source_sha256=source['sha256'],knowledge_lineage='RECONSTRUCTED_LATEST_MEMBERSHIP' if family!='CORE' else 'RECONSTRUCTED_CORRECTED',AS_RECORDED=False,PIT_ELIGIBLE=False))
    for item in profiles['owners']:
        owner=item['owner'];day=owner['trade_date']
        for family,binding,key in [('CORE',owner['core'],'fields'),('PROFILE',owner['profiles'],'states'),('STRUCTURE',item['advanced_projection'],'fields')]:
            rs=gzrows(checked(ROOT,binding));names=sorted({k for r in rs for k in r[key]})
            for name in names:emit(day,family,name,[r[key].get(name,{}) for r in rs],binding)
    market=load(out/'MARKET_REPLAY.json')
    for item in market['owners']:
        row=load(checked(ROOT,item['market']))
        for k,q in row['axes']['field_quality'].items():emit(item['trade_date'],'MARKET',k,[dict(value=row['axes'][k],**q)],item['market'])
        emit(item['trade_date'],'MARKET','trend_axis',[dict(value=row['trend']['trend_axis'],quality_state=row['trend']['quality_state'],unknown_reason=row['trend']['unknown_reason'])],item['market'])
        records.append(dict(trade_date=item['trade_date'],family='MARKET',field='intraday_touch',quality='UNKNOWN',reason='NOT_OBSERVABLE_FROM_DAILY',count=1,source_path=item['market']['path'],source_sha256=item['market']['sha256'],knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,PIT_ELIGIBLE=False))
    target=out.parent/'07_FIELD_LINEAGE_AND_UNKNOWN_REASONS_BY_DATE.csv';temp=target.with_suffix('.tmp.stock')
    with temp.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    os.replace(temp,target)
    write(out/'W3_W5_RECEIPT.json',dict(contract='V4_R43_CORRECTED_OWNER_REPLAY_V3',core=ref(ROOT,out/'CORE_REPLAY.json'),profiles=ref(ROOT,out/'PROFILE_STRUCTURE_REPLAY.json'),health=ref(ROOT,out/'HEALTH_PROJECTION_REPLAY.json'),market=ref(ROOT,out/'MARKET_REPLAY.json'),focus=ref(ROOT,out/'FOCUS_FORWARD_REPLAY.json'),lineage=ref(ROOT,target),corrected_candidate_rebuilt=True,formal_accepted=False,production_changed=False,next_stage='INDEPENDENT_OPERATIONAL_SOURCE_NUMERIC_REVIEW'))
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['profile','market','focus','lineage'],required=True);args=p.parse_args()
    if args.stage=='profile':
        from workbench_analysis.r43_structure_replay import materialize_profiles_structure
        from workbench_analysis.r43_health_projection import materialize_health
        materialize_profiles_structure(ROOT);materialize_health(ROOT)
        from workbench_analysis.r43_breakout_observations import materialize_breakout_observations
        materialize_breakout_observations(ROOT)
    elif args.stage=='market':
        from workbench_analysis.r43_market_replay import materialize_market
        materialize_market(ROOT)
    elif args.stage=='focus':
        from workbench_analysis.r43_focus_replay import materialize_focus
        materialize_focus(ROOT)
    else:lineage()
