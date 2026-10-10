"""Export candidate actual Amount A warmup and independent boundary inputs."""
from immediate_r3_common import *
import sys
sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.amount_a_go_forward_r3 import calculate_sector_amount, compute_ledger_candidate
from copy import deepcopy
D=OUT/'11_DEEPENING'

def main():
    refs=[binding(p) for p in sorted((ROOT/'data/v4/a04_go_forward_r3/observations').glob('*.json'))]
    actual=compute_ledger_candidate(ROOT,refs,target='2026-09-30')
    write(D/'AMOUNT_A_ACTUAL_LEDGER_CANDIDATE.json',actual)
    observations=load(refs[0]);calendar=load(observations['calendar_binding'])['session_dates']
    idx=calendar.index('2026-09-30');sessions=calendar[idx-20:idx+1];target=sessions[-1]
    members=sorted(observations['amounts'])[:3]
    base=dict(sector_id='FIXTURE_ONLY',target=target,sessions=sessions,
      observations={d:dict(members=members,membership_basis='PIT_OBSERVED_ACCEPTED',
        amounts={m:dict(amount=100+i,unit='CNY_YUAN',state='ACTUAL_TRADED') for i,m in enumerate(members)}) for d in sessions},mode='SYNTHETIC_ENGINEERING_ONLY')
    cases=[]
    for name in ('baseline','unit_wan','unit_yi','membership_gap','not_pit','amount_gap','unknown_zero','suspended_zero','suspension_conflict','negative_amount','nonfinite','no_common','current_new_member','prior_zero'):
        x=deepcopy(base);r=x['observations'][target]['amounts'][members[0]]
        if name=='unit_wan':r.update(amount='.03',unit='CNY_WAN')
        elif name=='unit_yi':r.update(amount='.000003',unit='CNY_YI')
        elif name=='membership_gap':x['observations'].pop(sessions[4])
        elif name=='not_pit':x['observations'][sessions[4]]['membership_basis']='LATEST_MEMBER_RETRO'
        elif name=='amount_gap':x['observations'][sessions[4]]['amounts'].pop(members[0])
        elif name=='unknown_zero':r['amount']=0
        elif name=='suspended_zero':r.update(amount=0,state='SUSPENDED_CONFIRMED')
        elif name=='suspension_conflict':r.update(amount=1,state='SUSPENDED_CONFIRMED')
        elif name=='negative_amount':r['amount']=-1
        elif name=='nonfinite':r['amount']='NaN'
        elif name=='no_common':x['observations'][sessions[0]]['members']=[]
        elif name=='current_new_member':x['observations'][target]['members'].append('NEW_MEMBER_FIXTURE')
        elif name=='prior_zero':
            for d in sessions[:-1]:
                for row in x['observations'][d]['amounts'].values():row.update(amount=0,state='SUSPENDED_CONFIRMED')
        cases.append(dict(id=name,evidence_class='FIXTURE_ONLY',input=x,actual=calculate_sector_amount(**x)))
    write(D/'AMOUNT_A_BOUNDARY_INPUT.json',dict(contract='AMOUNT_A_INDEPENDENT_BOUNDARY_R3_V1',source_bindings=refs,
      actual_member_observation_date=observations['target_trade_date'],fixtures=cases,
      current_actual_scope=dict(rows=len(actual['rows']),quality_counts={s:sum(r['arithmetic_status']==s for r in actual['rows']) for s in ('KNOWN','UNKNOWN')},
      missing_sessions=actual['rows'][0]['missing_accepted_membership_sessions'],formal_consumer_enabled=False)))
    print('actual sectors',len(actual['rows']),'fixtures',len(cases))
if __name__=='__main__':main()
