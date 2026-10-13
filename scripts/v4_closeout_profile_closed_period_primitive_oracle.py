"""Independent previously uncovered closed-week/month Profile primitive inputs."""
import json
from datetime import date
from collections import Counter
from scripts.v4_closeout_profile_rule_oracle import ROOT,OUT
from scripts.v4_closeout_core_uncovered_numeric_oracle import jsonlines,average
from workbench_analysis.r43_owner_replay import checked
from workbench_analysis.operational_daily_storage_v1 import atomic_json

def main():
    target=OUT/'PROFILE_CLOSED_PERIOD_PRIMITIVE_ORACLE_R6_R1.json'
    if target.exists():raise ValueError('PRESERVE_CLOSED_PERIOD_ORACLE')
    prep=json.loads((OUT/'SEALED_METADATA_CONSERVATION_R6_R3.json').read_bytes());candidate=json.loads(checked(ROOT,prep['candidate']).read_bytes());day=candidate['accepted_trade_date'];diagnostic=json.loads(checked(ROOT,candidate['owners'][day]['diagnostic']).read_bytes());manifest=json.loads(checked(ROOT,diagnostic['structure_manifest']).read_bytes());owner=manifest['owner_inputs'];profiles={r['security_id']:r for r in jsonlines(checked(ROOT,candidate['owners'][day]['profile']))};counts=Counter();error_count=0;errors=[]
    def check(sid,field,key,actual,expected):
        nonlocal error_count
        counts[field+'.'+key]+=1
        if actual!=expected:
            error_count+=1
            if len(errors)<100:errors.append(dict(security_id=sid,field=field,key=key,actual=actual,expected=expected))
    for history in jsonlines(checked(ROOT,owner['history'])):
        sid=history['security_id']
        for kind,n in (('weekly',5),('monthly',3)):
            groups={}
            for b in history['bars']:
                d=date.fromisoformat(b['trade_date']);key=d.isocalendar()[:2] if kind=='weekly' else (d.year,d.month);groups.setdefault(key,[]).append(b)
            keys=sorted(groups)[:-1];recent=[groups[k] for k in keys[-n-1:]];ready=len(recent)==n+1 and all(all(b['qfq_ohlc'] for b in group) for group in recent)
            field=kind+'_trend_state';key='ma5' if n==5 else 'ma3';e=profiles[sid]['states'][field]['evidence']
            expected={'period_view':'CLOSED_ONLY' if ready else 'UNKNOWN','close':recent[-1][-1]['qfq_ohlc'][3] if ready else None,key:average(group[-1]['qfq_ohlc'][3] for group in recent[-n:]) if ready else None,'previous_'+key:average(group[-1]['qfq_ohlc'][3] for group in recent[:-1]) if ready else None}
            for k,v in expected.items():check(sid,field,k,e.get(k),v)
    result=dict(contract_id='V4_PROFILE_CURRENT_CLOSED_PERIOD_PRIMITIVE_INDEPENDENT_ORACLE_R1',acceptance='PASS_CLOSED_PERIOD_PRIMITIVE_SCOPE' if not error_count else 'FAIL',T0=day,candidate=prep['candidate'],history=owner['history'],profile=candidate['owners'][day]['profile'],checks=dict(counts),check_count=sum(counts.values()),error_count=error_count,first_errors=errors,primary_period_builder_imported=False,previous_rule_and_large_period_pass_reexecuted=False,scope='Closed weekly/monthly primitive evidence only; exclusion of last forming bucket is preserved from versioned original adapter. No historical PIT grant.')
    atomic_json(OUT,target,result);print(json.dumps(dict(acceptance=result['acceptance'],checks=result['check_count'],errors=error_count)))
if __name__=='__main__':main()
