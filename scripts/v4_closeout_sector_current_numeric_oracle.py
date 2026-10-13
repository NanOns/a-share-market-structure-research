"""Uncovered current native Sector arithmetic; reuse prior width/breadth PASS."""
import json,math
from collections import defaultdict,Counter
from scripts.v4_closeout_profile_rule_oracle import ROOT,OUT
from scripts.v4_closeout_full_loo_numeric_oracle import middle
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.r43_operational_publication import rows
from workbench_analysis.operational_daily_storage_v1 import atomic_json

def main():
    report=OUT/'FULL_CURRENT_SECTOR_NUMERIC_ORACLE_R6_R1.json'
    if report.exists():raise ValueError('PRESERVE_CURRENT_SECTOR_ORACLE')
    preparation=json.loads((OUT/'SEALED_METADATA_CONSERVATION_R6_R3.json').read_bytes());candidate=json.loads(checked(ROOT,preparation['candidate']).read_bytes());day=candidate['accepted_trade_date'];receipt=json.loads(checked(ROOT,candidate['owners'][day]['sector_receipt']).read_bytes());dated={r['trade_date']:r for r in receipt['owners']};source=dated[day]
    if source['native']!=candidate['owners'][day]['sector'] or source['independent_native_width_breadth_checks']!=800:raise ValueError('EXACT_PRIOR_800_BREADTH_WIDTH_PASS_REQUIRED')
    snapshot=json.loads(checked(ROOT,source['source_bindings']['membership_snapshot']).read_bytes());members=rows(ROOT,snapshot['memberships']);calendar=json.loads((ROOT/'docs/evidence/r4_3_four_session_closeout_20261009/owner_v3/FOCUS_CALENDAR.json').read_bytes())['session_dates'];position=calendar.index(day);required=(day,calendar[position-1],calendar[position-3]);data={};groups={};native={};allgroups=defaultdict(list)
    for m in members:allgroups[m['sector_id']].append(m)
    core_receipt=json.loads(checked(ROOT,json.loads(checked(ROOT,candidate['day_receipt']).read_bytes())['numeric_core_oracle']).read_bytes());core_owners={r['trade_date']:r for r in core_receipt['owners']}
    for date in required:
        owner=dated[date];factors={r['security_id']:r for r in rows(ROOT,owner['source_bindings']['core'])};profile={r['security_id']:r for r in rows(ROOT,owner['source_bindings']['profiles'])};raw={r['security_id']:r for r in rows(ROOT,core_owners[date]['raw'])};adjusted={r['security_id']:r for r in rows(ROOT,core_owners[date]['adjusted'])};values={}
        for sid,row in factors.items():
            v={k:c['value'] if c['quality_state']=='OBSERVED' else None for k,c in row['fields'].items()};close=adjusted.get(sid,{}).get('close');ma=row['fields']['ma20']['value'];v.update(amount=raw.get(sid,{}).get('amount'),close=close,close_minus_ma20=close-ma if close is not None and ma is not None else None,mdd20=profile[sid]['derived_fields'].get('mdd20',{}).get('value'));values[sid]=v
        data[date]=values;group=defaultdict(set)
        for member in members:
            sid=member['security_id']
            if sid in factors and member['list_date'] and member['list_date']<=date and (not member['delist_date'] or member['delist_date']>date):group[member['sector_id']].add(sid)
        groups[date]=group;native[date]={r['sector_id']:r for r in rows(ROOT,owner['native'])}
        data[date,'seed']={r['security_id']:True if r['base_seed_state']=='TRUE' else False if r['base_seed_state']=='FALSE' else None for r in rows(ROOT,owner['seed'])}
    p={r['parameter_id']:r['value'] for r in json.loads((ROOT/'config/v4_08_algorithm_parameter_set_r5.json').read_bytes())['parameters']};checks=Counter();errors=[];count=0;computed={}
    def check(sector,field,key,actual,expected):
        nonlocal count
        checks[key]+=1
        if actual!=expected:
            count+=1
            if len(errors)<100:errors.append(dict(sector_id=sector,field=field,key=key,actual=actual,expected=expected))
    for sector,row in native[day].items():
        ids=groups[day][sector];fields={};reasons={};v=data[day];quoted=[v[s]['ret1'] for s in ids if v[s]['ret1'] is not None];coverage=len(quoted)/len(ids)
        expected_eligible=len(ids)>=p['V4_08_SECTOR_MIN_MEMBERS'] and coverage>=p['V4_08_SECTOR_MIN_QUOTE_COVERAGE'];check(sector,None,'member_ids',row['member_ids'],sorted(ids));check(sector,None,'rank_eligible',row['rank_eligible'],expected_eligible)
        fields.update(membership_ready=True,sector_member_count=len(ids),sector_quote_coverage=coverage)
        for n in (1,5,20,60):
            known=sorted(v[s].get('ret'+str(n)) for s in ids if v[s].get('ret'+str(n)) is not None);field='sector_rs'+str(n);fields[field]=middle(known);reasons[field]=None if known else 'NO_TARGET_ACCEPTED_CORE_FACTS'
        # Original producer already verified all400 of these exact values.
        fields['breadth_ret1']=row['fields']['breadth_ret1']['value'];fields['ma20_width']=row['fields']['ma20_width']['value']
        for n in (5,20):
            known=[v[s]['ret'+str(n)] for s in ids if v[s]['ret'+str(n)] is not None];field='breadth_ret'+str(n);fields[field]=sum(x>0 for x in known)/len(known) if known else None;reasons[field]=None if known else 'NO_TARGET_ACCEPTED_CORE_FACTS'
        for target,key in (('participation_proxy','amount_ratio20'),('pos60','pos60'),('mdd20','mdd20')):
            known=sorted(v[s][key] for s in ids if v[s][key] is not None);fields[target]=middle(known);reasons[target]=None if known else 'NO_TARGET_ACCEPTED_CORE_FACTS'
        amounts=[v[s]['amount'] for s in ids if v[s]['amount'] is not None and v[s]['amount']>=0];total=sum(amounts)
        for n in (1,3):fields['top'+str(n)+'_concentration']=sum(sorted(amounts,reverse=True)[:n])/total if total>0 else None;reasons['top'+str(n)+'_concentration']=None if total>0 else 'ZERO_OR_UNKNOWN_AMOUNT_DENOMINATOR'
        strong={s:None if v[s]['rps20'] is None else v[s]['rps20']>=80 for s in ids};fields['strong_member']=sorted(s for s,b in strong.items() if b) if all(b is not None for b in strong.values()) else None;reasons['strong_member']=None if fields['strong_member'] is not None else 'INCOMPLETE_STRONG_MEMBER_OBSERVATIONS'
        for lag in (1,3):
            date=calendar[position-lag];old_ids=groups[date].get(sector);common=ids&set(old_ids or ());before=data[date]
            for stem,key in (('breadth','ret1'),('ma20','close_minus_ma20')):
                pairs=[(v[s][key],before[s][key]) for s in sorted(common)];known=[(a,b) for a,b in pairs if a is not None and b is not None];field=stem+'_delta'+str(lag);valid=old_ids is not None and bool(known) and len(known)==len(common);fields[field]=sum(int(a>0)-int(b>0) for a,b in known)/len(known) if valid else None;reasons[field]=None if valid else 'NO_EFFECTIVE_DATED_MEMBERSHIP' if old_ids is None else 'INCOMPLETE_COMMON_MEMBER_ENDPOINTS'
                metadata=dict(current_member_count=len(ids),prior_member_count=len(old_ids) if old_ids is not None else None,common_count=len(common),endpoint_known_count=len(known),coverage=len(known)/len(common) if common else None,membership_entered_count=len(ids-old_ids) if old_ids is not None else None,membership_exited_count=len(old_ids-ids) if old_ids is not None else None);check(sector,field,'common_member_metadata',row['common_member_quality'][field],metadata)
        before_date=calendar[position-1];old_ids=groups[before_date].get(sector);common=ids&set(old_ids or ());old={s:data[before_date][s]['rps20'] for s in common};frozen=None if old_ids is None or any(x is None for x in old.values()) else {s for s,x in old.items() if x>=80}
        def retention(frozen,truth):
            return (None,'NO_PRIOR_ACCEPTED_PIT_HISTORY') if frozen is None else (None,'EMPTY_FROZEN_DENOMINATOR') if not frozen else (None,'INCOMPLETE_FROZEN_DENOMINATOR') if any(truth.get(s) is None for s in frozen) else (sum(truth[s] is True for s in frozen)/len(frozen),None)
        fields['strong_member_retention'],reasons['strong_member_retention']=retention(frozen,strong)
        ready=frozen is not None and all(strong[s] is not None for s in common);fields['entered_count']=sum(old[s]<80 and strong[s] for s in common) if ready else None;fields['net_entered_count']=sum(int(strong[s])-int(old[s]>=80) for s in common) if ready else None
        truths={s:data[day,'seed'].get(s) for s in ids};known=[x for x in truths.values() if isinstance(x,bool)];n=len(known);k=sum(known);z=p['V4_08_SEED_WILSON_Z'];ratio=k/n if n else None;fields['seed_width']=ratio;fields['base_seed_width_adjusted']=(ratio+z*z/(2*n)-z*math.sqrt(ratio*(1-ratio)/n+z*z/(4*n*n)))/(1+z*z/n) if n else None
        reasons['seed_width']=reasons['base_seed_width_adjusted']=None if n else 'NO_EVALUABLE_BASE_SEED';previous=data[before_date,'seed'];seed_frozen=None if old_ids is None or any(previous.get(s) is None for s in common) else {s for s in common if previous[s] is True};fields['seed_retention'],reasons['seed_retention']=retention(seed_frozen,truths)
        computed[sector]=dict(fields=fields,reasons=reasons,eligible=expected_eligible)
    for sector,row in native[day].items():
        result=computed[sector];fields=result['fields'];typ=row['sector_type'];parent=row['industry_level']=='PARENT_DERIVED'
        for n in (5,20,60):
            field='sector_rs'+str(n);value=fields[field];pool=[r['fields'][field] for s,r in computed.items() if native[day][s]['sector_type']==typ and (native[day][s]['industry_level']=='PARENT_DERIVED')==parent and r['eligible'] and r['fields'][field] is not None];rank=100*(sum(x<value for x in pool)+.5*(sum(x==value for x in pool)-1))/(len(pool)-1) if result['eligible'] and value is not None and len(pool)>=2 else None;fields[field+'_pct']=rank;result['reasons'][field+'_pct']=None if rank is not None else 'NO_QUALIFIED_RANK_INPUT';check(sector,field+'_pct','rank_denominator',row['fields'][field+'_pct']['rank_denominator'],len(pool))
        old=native[calendar[position-3]].get(sector)
        for field,n in (('dq5',5),('rank_velocity3',20)):
            prior=old['fields']['sector_rs'+str(n)+'_pct']['value'] if old else None;now=fields['sector_rs'+str(n)+'_pct'];fields[field]=now-prior if now is not None and prior is not None else None;result['reasons'][field]=None if fields[field] is not None else 'NO_PRIOR_OWNER_MATERIALIZED'
        if set(fields)!=set(row['fields']):raise ValueError('UNDECLARED_SECTOR_FIELD_SCOPE')
        for field,value in fields.items():
            cell=row['fields'][field]
            if field not in ('breadth_ret1','ma20_width'):check(sector,field,'value',cell['value'],value)
            check(sector,field,'quality',cell['quality'],'PROXY_RECONSTRUCTED' if value is not None else 'UNKNOWN');check(sector,field,'reason',cell['reason_code'],result['reasons'].get(field))
    result=dict(contract_id='V4_FULL_CURRENT_SECTOR_INDEPENDENT_PRIMITIVE_AND_DELTA_ORACLE_R1',acceptance='PASS_FULL_CURRENT_SECTOR_SCOPE' if not count else 'FAIL',candidate=preparation['candidate'],T0=day,sector=candidate['owners'][day]['sector'],source_bindings=source['source_bindings'],prior_dates=list(required[1:]),sectors=len(native[day]),checks=dict(checks),check_count=sum(checks.values()),previous_800_breadth_width_value_checks_reused=True,prior_receipt=candidate['owners'][day]['sector_receipt'],error_count=count,first_errors=errors,primary_sector_producer_called=False,scope='Current400 native sectors, all32 fields values/UNKNOWN reasons/quality, separate leaf/parent rank pools, prior common-set delta/retention and Wilson seed width; previous800 width/breadth value assertions reused, original producer not rerun')
    atomic_json(OUT,report,result);print(json.dumps(dict(acceptance=result['acceptance'],sectors=result['sectors'],checks=result['check_count'],errors=count)))

if __name__=='__main__':main()
