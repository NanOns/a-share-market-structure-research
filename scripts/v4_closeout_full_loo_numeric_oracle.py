"""Uncovered current full membership LOO arithmetic and relative-state topology."""
import bisect,json,math
from collections import defaultdict,Counter
from scripts.v4_closeout_profile_rule_oracle import ROOT,OUT
from scripts.v4_04_machine_executor_r4 import execute_rule
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.r43_operational_publication import rows
from workbench_analysis.operational_daily_storage_v1 import atomic_json

def middle(values):
    n=len(values)
    return None if not n else values[n//2] if n%2 else (values[n//2-1]+values[n//2])/2

def main():
    target=OUT/'FULL_CURRENT_LOO_NUMERIC_ORACLE_R6_R1.json'
    if target.exists():raise ValueError('PRESERVE_FULL_LOO_ORACLE')
    preparation=json.loads((OUT/'SEALED_METADATA_CONSERVATION_R6_R3.json').read_bytes());candidate=json.loads(checked(ROOT,preparation['candidate']).read_bytes());day=candidate['accepted_trade_date'];owner=candidate['owners'][day];snapshot=json.loads(checked(ROOT,candidate['membership_snapshot']).read_bytes())
    members=rows(ROOT,snapshot['memberships']);core={r['security_id']:r for r in rows(ROOT,owner['core'])};profiles={r['security_id']:r for r in rows(ROOT,owner['profile'])};actual=rows(ROOT,owner['relative_sector'])
    p={r['parameter_id']:r['value'] for r in json.loads((ROOT/'config/v4_08_algorithm_parameter_set_r5.json').read_bytes())['parameters']};parameters={r['parameter_id']:r['value'] for r in json.loads((ROOT/'config/v4_04_parameter_set_v1.json').read_bytes())['parameters']};contract=json.loads((ROOT/'config/v4_04_algorithm_contracts_v3.json').read_bytes())
    allgroups=defaultdict(list);groups=defaultdict(set);bystock=defaultdict(set)
    for member in members:
        sector=member['sector_id'];allgroups[sector].append(member);sid=member['security_id']
        if sid is None or not member['list_date'] or member['list_date']>day or (member['delist_date'] and member['delist_date']<=day) or sid not in core:continue
        groups[sector].add(sid);bystock[sid].add(sector)
    eligible_sector={s for s,rs in allgroups.items() if not all('DERIVED_PARENT' in r['source'] for r in rs)}
    def value(sid,field):
        cell=core[sid]['fields'][field];v=cell['value']
        return v if cell['quality_state']=='OBSERVED' and v is not None and isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) else None
    ordered={(s,n):sorted(v for sid in ids if (v:=value(sid,'ret'+str(n))) is not None) for s,ids in groups.items() for n in (1,5)}
    def excluding(sector,n,sid):
        original=ordered[sector,n];stock=value(sid,'ret'+str(n))
        if stock is None:return original
        i=bisect.bisect_left(original,stock)
        if i==len(original) or original[i]!=stock:raise ValueError('LOO_TARGET_NOT_IN_KNOWN_MULTISET')
        return original[:i]+original[i+1:]
    counts=Counter();errors=[];error_count=0;contexts=0
    def check(sid,sector,key,actual,expected):
        nonlocal error_count
        counts[key]+=1
        if actual!=expected:
            error_count+=1
            if len(errors)<100:errors.append(dict(security_id=sid,sector_id=sector,field=key,actual=actual,expected=expected))
    order={s:i for i,s in enumerate(('ACTIVE_EMERGENCE','LEADING_ACCELERATING','LEADING_STABLE','IMPROVING','PASSIVE_RESILIENCE','NEUTRAL','WEAKENING','LAGGING'))}
    for row in actual:
        sid=row['security_id'];expected_sectors=sorted(bystock[sid]&eligible_sector);observed={r['sector_id']:r for r in row['memberships']};check(sid,None,'membership_scope',sorted(observed),expected_sectors);computed=[]
        for sector in expected_sectors:
            context=observed[sector];others=len(groups[sector])-1;ret1=excluding(sector,1,sid);ret5=excluding(sector,5,sid);ready=others>=p['V4_08_SECTOR_MIN_MEMBERS'] and bool(others) and len(ret1)/others>=p['V4_08_SECTOR_MIN_QUOTE_COVERAGE'];contexts+=1
            check(sid,sector,'excluded_target_id',context['excluded_target_id'],sid);check(sid,sector,'non_target_count',context['non_target_member_count'],others)
            if not ready:state=None;quality='UNKNOWN';reason='UNKNOWN_INSUFFICIENT_LOO_MEMBERS_OR_COVERAGE';substitution=None
            else:
                f=core[sid]['fields'];substitution={k:f[k]['value'] for k in ('rps5','rps20','rps20_delta3')}
                for n,values in ((1,ret1),(5,ret5)):
                    stock=value(sid,'ret'+str(n));median=middle(values);substitution['rel_market_'+str(n)]=stock-median if stock is not None and median is not None else None
                evidence=dict(substitution,compression_state=profiles[sid]['states']['compression_state']['value'],ma_structure_state=profiles[sid]['states']['ma_structure_state']['value'])
                result=execute_rule(contract['rules'],'RELATIVE_STATE_V1',evidence,parameters);state=None if result=='UNKNOWN' else result;quality='UNKNOWN' if state is None else 'KNOWN';reason='REQUIRED_INPUT_UNKNOWN' if state is None else None
            for key,expected in (('value',state),('quality',quality),('reason',reason)):
                check(sid,sector,key,context[key],expected)
            if substitution is not None:
                check(sid,sector,'relative_substitutions',context.get('relative_substitutions'),substitution)
            else:check(sid,sector,'no_unqualified_substitution','relative_substitutions' in context,False)
            computed.append(dict(sector_id=sector,value=state,quality=quality))
        all_known=bool(computed) and all(c['quality']=='KNOWN' for c in computed);chosen=min(computed,key=lambda c:(order.get(c['value'],99),c['sector_id'])) if all_known else None
        for key,expected in (('value',chosen['value'] if chosen else None),('selected_sector_id',chosen['sector_id'] if chosen else None),('quality','KNOWN' if all_known else 'UNKNOWN'),('reason',None if all_known else 'REQUIRED_TDX_LOO_CONTEXT_UNKNOWN')):check(sid,None,'aggregate_'+key,row[key],expected)
    result=dict(contract_id='V4_CURRENT_FULL_LOO_INDEPENDENT_MULTIMEMBERSHIP_ORACLE_R1',acceptance='PASS_FULL_CURRENT_LOO_SCOPE' if not error_count else 'FAIL',candidate=preparation['candidate'],T0=day,relative_owner=owner['relative_sector'],membership=snapshot['memberships'],stock_count=len(actual),context_count=contexts,checks=dict(counts),check_count=sum(counts.values()),error_count=error_count,first_errors=errors,primary_sector_or_relative_producer_called=False,previous_passed_core_formulas_reexecuted=False,scope='All 50214 current leaf-industry/concept target-excluded contexts, coverage, relative substitutions, complete known/UNKNOWN rule branches and deterministic all-membership selection; no original period or Focus recomputation')
    atomic_json(OUT,target,result);print(json.dumps(dict(acceptance=result['acceptance'],contexts=contexts,checks=result['check_count'],errors=error_count)))

if __name__=='__main__':main()
