"""PIT-only sector primitives. Inputs are publication-bound member facts.

No current-membership replay, legacy aggregates, final stock states or TDX IO.
The caller supplies accepted records; absent endpoints remain unknown.
"""
from __future__ import annotations

import math
from statistics import median
from typing import Mapping

PRODUCER = 'V4_08_SECTOR_NATIVE_V1'
SEED_DEGRADED = 'DEGRADED_BY_UPSTREAM_BASE_SEED_SIGNAL'
NO_HISTORY = 'NO_PRIOR_ACCEPTED_PIT_HISTORY'


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def observed(record, field, target):
    if not record or record.get('trade_date') != target:
        return None
    item = record.get('fields', {}).get(field)
    if not isinstance(item, Mapping) or item.get('quality') != 'ACCEPTED':
        return None
    if item.get('max_source_date', target) > target:
        raise ValueError('FUTURE_MEMBER_FACT')
    return number(item.get('value'))


def retention(previous_set, current_truth):
    """Never delete unavailable members from a frozen denominator."""
    if previous_set is None:
        return None, 'UNKNOWN', NO_HISTORY
    if not previous_set:
        return None, 'NOT_APPLICABLE', 'EMPTY_FROZEN_DENOMINATOR'
    if any(current_truth.get(member) is None for member in previous_set):
        return None, 'UNKNOWN', 'INCOMPLETE_FROZEN_DENOMINATOR'
    return sum(current_truth[member] is True for member in previous_set) / len(previous_set), 'ACCEPTED', None


def common_delta(current_members, prior_members, current, prior, field, target, prior_date, predicate):
    common = set(current_members) & set(prior_members or ())
    endpoints = [(observed(current.get(m), field, target), observed(prior.get(m), field, prior_date)) for m in sorted(common)]
    known = [(a, b) for a, b in endpoints if a is not None and b is not None]
    meta = dict(current_member_count=len(current_members), prior_member_count=None if prior_members is None else len(prior_members),
                common_count=len(common), endpoint_known_count=len(known),
                coverage=len(known)/len(common) if common else None,
                membership_entered_count=None if prior_members is None else len(set(current_members)-set(prior_members)),
                membership_exited_count=None if prior_members is None else len(set(prior_members)-set(current_members)))
    if prior_members is None:
        return None, NO_HISTORY, meta
    if not known or len(known) != len(common):
        return None, 'INCOMPLETE_COMMON_MEMBER_ENDPOINTS', meta
    return sum(predicate(a)-predicate(b) for a, b in known)/len(known), None, meta


def build_native(memberships, current, *, target, snapshot_id, publication_id, parameter_set,
                 source_bindings, prior=None, prior_memberships=None, prior_date=None,
                 prior_sector_rows=None, seed=None, seed_capability=False, prior_seed=None, max_source_date=None):
    params = {p['parameter_id']:p['value'] for p in parameter_set['parameters']}
    required = ('V4_08_SECTOR_MIN_MEMBERS','V4_08_SECTOR_MIN_QUOTE_COVERAGE','V4_08_SEED_WILSON_Z')
    if any(number(params.get(p)) is None for p in required):
        raise ValueError('UNBOUND_NATIVE_PARAMETER')
    groups = {}
    for member in memberships:
        if member['snapshot_id'] != snapshot_id or member['target_trade_date'] != target or member['sector_type'] not in {'INDUSTRY','THEME'}:
            raise ValueError('INVALID_ACCEPTED_PIT_SCOPE')
        key=(member['sector_type'],member['sector_id'])
        ids=groups.setdefault(key,set())
        if member['security_id'] in ids:
            raise ValueError('DUPLICATE_MEMBERSHIP')
        ids.add(member['security_id'])
    prior=prior or {}; seed=seed or {}; rows=[]
    for (typ, sid), members in sorted(groups.items()):
        row=dict(publication_id=publication_id, sector_id=sid, sector_type=typ, target_trade_date=target,
                 membership_snapshot_id=snapshot_id, model_contract_id=PRODUCER,
                 parameter_set_id=parameter_set['parameter_set_id'], input_digests=source_bindings,
                 member_ids=sorted(members), fields={}, common_member_quality={})
        def put(field, value, reason=None, quality=None, **extra):
            row['fields'][field]=dict(value=value, quality=quality or ('ACCEPTED' if value is not None else 'UNKNOWN'),
                reason_code=reason, producer='V4_08_PIT_MEMBERSHIP' if field=='membership_ready' else PRODUCER,
                time_role='COMMON_EVALUABLE_MEMBER_SET' if field in {'entered_count','net_entered_count'} else 'TARGET_CUTOFF', target_trade_date=target, max_source_date=target if field in {'membership_ready','sector_member_count'} else max_source_date or target,
                source_publications=source_bindings, membership_snapshot_id=snapshot_id,
                model_contract_id=PRODUCER, parameter_set_id=parameter_set['parameter_set_id'], **extra)
        valid=sum(observed(current.get(m),'ret1',target) is not None for m in members)
        target_publication_available=any(r.get('trade_date')==target for r in current.values())
        coverage=valid/len(members) if target_publication_available else None
        put('membership_ready',True);put('sector_member_count',len(members));put('sector_quote_coverage',coverage,'NO_TARGET_ACCEPTED_CORE_FACTS' if coverage is None else None)
        eligible=len(members)>=params[required[0]] and coverage is not None and coverage>=params[required[1]]
        row['rank_eligible']=eligible
        for n in (1,5,20,60):
            values=[observed(current.get(m),f'ret{n}',target) for m in members]
            known=[v for v in values if v is not None]
            put(f'sector_rs{n}',median(known) if known else None,'NO_TARGET_ACCEPTED_CORE_FACTS' if not known else None,
                known_count=len(known),unknown_count=len(values)-len(known))
        for field, source, pred in [('breadth_ret1','ret1',lambda v:v>0),('ma20_width','close_minus_ma20',lambda v:v>0),
                                    ('breadth_ret5','ret5',lambda v:v>0),('breadth_ret20','ret20',lambda v:v>0)]:
            known=[v for m in members if (v:=observed(current.get(m),source,target)) is not None]
            put(field,sum(pred(v) for v in known)/len(known) if known else None,
                'NO_TARGET_ACCEPTED_CORE_FACTS' if not known else None, known_count=len(known))
        for field in ('amount_ratio20','pos60','mdd20'):
            known=[v for m in members if (v:=observed(current.get(m),field,target)) is not None]
            put('participation_proxy' if field=='amount_ratio20' else field,median(known) if known else None,
                'NO_TARGET_ACCEPTED_CORE_FACTS' if not known else None)
        amounts=[v for m in members if (v:=observed(current.get(m),'amount',target)) is not None and v>=0]
        total=sum(amounts)
        for k in (1,3):
            put(f'top{k}_concentration',sum(sorted(amounts,reverse=True)[:k])/total if total>0 else None,
                'ZERO_OR_UNKNOWN_AMOUNT_DENOMINATOR' if total<=0 else None,known_count=len(amounts))
        strong={m:None if (v:=observed(current.get(m),'rps20',target)) is None else v>=80 for m in members}
        put('strong_member',sorted(m for m,v in strong.items() if v is True) if all(v is not None for v in strong.values()) else None,
            'INCOMPLETE_STRONG_MEMBER_OBSERVATIONS' if any(v is None for v in strong.values()) else None)
        for k in (1,3):
            entry=(prior_memberships or {}).get(k,{}).get(sid)
            history=prior.get(k,{})
            date=(prior_date or {}).get(k)
            for stem,field,pred in [('breadth','ret1',lambda v:int(v>0)),('ma20','close_minus_ma20',lambda v:int(v>0))]:
                value,reason,meta=common_delta(members,entry,current,history,field,target,date,pred)
                put(f'{stem}_delta{k}',value,reason);row['common_member_quality'][f'{stem}_delta{k}']=meta
        entry=(prior_memberships or {}).get(1,{}).get(sid)
        common=set(members)&set(entry or ())
        history=prior.get(1,{}); date=(prior_date or {}).get(1)
        old={m:observed(history.get(m),'rps20',date) for m in common}
        old_set=None if entry is None or any(v is None for v in old.values()) else {m for m,v in old.items() if v>=80}
        value,quality,reason=retention(old_set,strong)
        put('strong_member_retention',value,reason,quality)
        put('entered_count',None if old_set is None or any(strong[m] is None for m in common) else sum(old[m]<80 and strong[m] for m in common),NO_HISTORY if entry is None else None)
        put('net_entered_count',None if old_set is None or any(strong[m] is None for m in common) else sum(int(strong[m])-int(old[m]>=80) for m in common),NO_HISTORY if entry is None else None)
        truths={m:seed.get(m) for m in members} if seed_capability else {m:None for m in members}
        known=[v for v in truths.values() if isinstance(v,bool)];n=len(known);k=sum(known);z=params[required[2]]
        p=k/n if n else None
        adjusted=(p+z*z/(2*n)-z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n) if n else None
        seed_reason=SEED_DEGRADED if not seed_capability else 'NO_EVALUABLE_BASE_SEED' if not n else None
        put('seed_width',p,seed_reason,k=k,n=n,unknown_count=len(members)-n)
        put('base_seed_width_adjusted',adjusted,seed_reason,k=k,n=n,unknown_count=len(members)-n)
        prior_truth=(prior_seed or {}).get(1)
        frozen=None if entry is None or prior_truth is None or any(prior_truth.get(m) is None for m in common) else {m for m in common if prior_truth[m] is True}
        value,quality,reason=retention(frozen,truths)
        if not seed_capability:value,quality,reason=None,'UNKNOWN',SEED_DEGRADED
        put('seed_retention',value,reason,quality)
        rows.append(row)
    for typ in ('INDUSTRY','THEME'):
        for n in (5,20,60):
            pool=[r for r in rows if r['sector_type']==typ and r['rank_eligible'] and r['fields'][f'sector_rs{n}']['value'] is not None]
            for row in [r for r in rows if r['sector_type']==typ]:
                field=row['fields'][f'sector_rs{n}'];value=field['value']
                rank=None
                if row in pool:
                    lower=sum(r['fields'][f'sector_rs{n}']['value']<value for r in pool)
                    tied=sum(r['fields'][f'sector_rs{n}']['value']==value for r in pool)
                    rank=100*(lower+(tied+1)/2)/len(pool)
                row['fields'][f'sector_rs{n}_pct']={**field,'value':rank,'quality':'ACCEPTED' if rank is not None else 'UNKNOWN',
                    'reason_code':None if rank is not None else 'NO_QUALIFIED_RANK_INPUT', 'rank_denominator':len(pool),'rank_membership_snapshot_id':snapshot_id}
    for row in rows:
        for field,n,k in [('dq5',5,3),('rank_velocity3',20,3)]:
            old=(prior_sector_rows or {}).get(k,{}).get(row['sector_id'])
            now=row['fields'][f'sector_rs{n}_pct']
            before=old.get('fields',{}).get(f'sector_rs{n}_pct',{}) if old else {}
            value=now['value']-before['value'] if now['value'] is not None and before.get('quality')=='ACCEPTED' and before.get('value') is not None else None
            row['fields'][field]={**now,'value':value,'quality':'ACCEPTED' if value is not None else 'UNKNOWN',
                'reason_code':None if value is not None else NO_HISTORY,'prior_membership_snapshot_id':old.get('membership_snapshot_id') if old else None}
    return rows
