"""Standalone stdlib oracle, no business import. Fixtures are not market observations."""
from decimal import Decimal
from pathlib import Path
import json,sys,os

def oracle(x):
    days=x['sessions'];end=days.index(x['target']);window=days[max(0,end-20):end+1];obs=x['observations']
    groups=[set(obs.get(d,{}).get('members',[])) for d in window]
    common=set.intersection(*groups);valid=[];fault=False
    for sid in common:
        usable=True
        for d in window:
            row=obs[d].get('amounts',{}).get(sid)
            try:
                value=Decimal(str(row['amount']))*{'CNY_YUAN':1,'CNY_WAN':10000,'CNY_YI':100000000}[row['unit']]
                usable &= value.is_finite() and value>=0 and ((row['state']=='ACTUAL_TRADED' and value>0) or (row['state']=='SUSPENDED_CONFIRMED' and value==0))
            except (KeyError,TypeError,ArithmeticError):usable=False
        if usable:valid.append(sid)
        else:fault=True
    blocked=len(window)!=21 or not common or fault or any(d not in obs or obs[d]['membership_basis']!='PIT_OBSERVED_ACCEPTED' for d in window)
    numerator=denominator=value=None
    if not blocked:
        totals=[sum((Decimal(str(obs[d]['amounts'][sid]['amount']))*{'CNY_YUAN':1,'CNY_WAN':10000,'CNY_YI':100000000}[obs[d]['amounts'][sid]['unit']] for sid in valid),Decimal(0)) for d in window]
        numerator=totals[-1];denominator=sum(totals[:-1])/20
        if denominator>0:value=numerator/denominator
    return dict(amount_a_value=str(value) if value is not None else None,
      amount_numerator_cny=str(numerator) if numerator is not None else None,
      amount_denominator_prior20_mean_cny=str(denominator) if denominator is not None else None,
      comparable_member_count=len(valid),target_member_count=len(groups[-1]),
      coverage=str(Decimal(len(valid))/len(groups[-1])) if groups[-1] else None,
      window_coverage=str(Decimal(len(valid))/max(map(len,groups))) if max(map(len,groups)) else None)

def main():
    p=Path(__file__).parent;data=json.loads((p/'AMOUNT_A_BOUNDARY_INPUT.json').read_text(encoding='utf8'));errors=[];checks=0
    for row in data['fixtures']:
        for k,v in oracle(row['input']).items():
            checks+=1
            if row['actual'][k]!=v:errors.append(dict(id=row['id'],field=k,expected=v,actual=row['actual'][k]))
        checks+=1
        if row['actual']['consumer_permission']['formal'] is not False:errors.append(dict(id=row['id'],field='formal_permission'))
    result=dict(checks=checks,errors=errors,fixtures=len(data['fixtures']),scope='FIXTURE_ONLY_ARITHMETIC_AND_NEGATIVES',actual_ledger=data['current_actual_scope'])
    tmp=p/'AMOUNT_A_BOUNDARY_RESULT.tmp';tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(tmp,p/'AMOUNT_A_BOUNDARY_RESULT.json')
    print(json.dumps(dict(checks=checks,errors=len(errors))));return bool(errors)
if __name__=='__main__':sys.exit(main())
