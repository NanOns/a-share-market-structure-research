"""Publication-bound B0/B1 runtime using the unchanged R3 four-state evaluator."""
from __future__ import annotations
import copy
import hashlib
import json
from sector.machine_ast_r3 import evaluate_ast_explain, validate_ast, ast_digest
from sector.native_r5 import observed, retention, NO_HISTORY, SEED_DEGRADED


def resolve_package(contract, parameter_set, parameter_bytes, registry):
    if contract['parameter_set_id'] != parameter_set['parameter_set_id'] or hashlib.sha256(parameter_bytes).hexdigest()!=contract['parameter_set_sha256']:
        raise ValueError('PARAMETER_INSTANCE_DIGEST_MISMATCH')
    if ast_digest(contract['rules']) != contract['ast_digest']:
        raise ValueError('FROZEN_AST_DIGEST_MISMATCH')
    if ast_digest(registry)!=contract['field_registry_digest']:
        raise ValueError('FIELD_REGISTRY_DIGEST_MISMATCH')
    parameters={p['parameter_id']:p['value'] for p in parameter_set['parameters']}
    if len(parameters)!=len(parameter_set['parameters']) or any(v is None for v in parameters.values()):
        raise ValueError('MISSING_OR_DUPLICATED_RUNTIME_PARAMETER')
    fields={f['field_id']:f for f in registry['fields']}
    validate_ast(contract['rules'],fields,parameters)
    return parameters,fields


def truth_table(contract, facts, parameters):
    results={key:evaluate_ast_explain(key,contract['rules'],facts,parameters) for key in contract['rules']}
    return {key:dict(state='TRUE' if v.state is True else 'FALSE' if v.state is False else 'UNKNOWN' if v.state is None else v.state,
                     reason_code=v.reason_code) for key,v in results.items()}


def evaluate_b0(native,contract,parameters):
    table=truth_table(contract,native['fields'],parameters)
    missing=[f for f in ('dq5','base_seed_width_adjusted','breadth_delta3','ma20_delta3') if native['fields'].get(f,{}).get('value') is None]
    # R5 explicitly makes missing history/seed a capability gate even when a
    # separate safety predicate is known false. Preserve AST truth separately.
    return dict(model_contract_id=contract['model_contract_id'],output_state='UNKNOWN' if missing else table['prewatch_raw']['state'],
                predicates=table,quality='UNKNOWN' if missing else 'ACCEPTED',
                reason_codes=sorted({native['fields'].get(f,{}).get('reason_code') or 'MISSING_REQUIRED_INPUT' for f in missing}))


def advance_rotation(native, current, *, prior_publication, prior_members, prior_core,
                     calendar_sessions, contract, registry, parameters, seed_truth=None,
                     seed_capability=False, prior_maturity=None):
    target=native['target_trade_date'];sid=native['sector_id'];facts=copy.deepcopy(native['fields'])
    fields={f['field_id']:f for f in registry['fields']}
    def put(field,value,reason=None,quality=None):
        spec=fields[field]
        facts[field]=dict(value=value,quality=quality or ('ACCEPTED' if value is not None else 'UNKNOWN'),reason_code=reason,
            producer=spec['producer'],time_role=spec['time_role'],target_trade_date=target,
            max_source_date=target,membership_snapshot_id=native['membership_snapshot_id'])
    # Normalize registered native roles, including common-member counters.
    for field,item in facts.items():
        if field in fields:item['time_role']=fields[field]['time_role']
    prior=prior_publication
    if prior is not None and (prior.get('acceptance')!='ACCEPTED' or prior['target_trade_date']>=target):
        raise ValueError('PRIOR_ROTATION_PUBLICATION_NOT_ACCEPTED_OR_NOT_PRIOR')
    episode=copy.deepcopy(prior.get('episode')) if prior else None
    put('prior_rotation_state',prior.get('output_state') if prior else None,NO_HISTORY if not prior else None)
    put('prior_maturity_state',prior_maturity,NO_HISTORY if prior_maturity is None else None)
    put('yesterday_dq5',prior.get('native_fields',{}).get('dq5',{}).get('value') if prior else None,NO_HISTORY if not prior else None)
    put('pulse_active',bool(episode and not episode.get('terminated')),NO_HISTORY if prior is None else None, 'UNKNOWN' if prior is None else 'ACCEPTED')
    put('episode_accepted',episode.get('accepted') if episode else False,NO_HISTORY if prior is None else None, 'UNKNOWN' if prior is None else 'ACCEPTED')
    put('episode_terminated',episode.get('terminated') if episode else False,NO_HISTORY if prior is None else None, 'UNKNOWN' if prior is None else 'ACCEPTED')
    sessions=sorted(set(calendar_sessions))
    if target not in sessions:raise ValueError('TARGET_NOT_IN_ACCEPTED_CALENDAR')
    age=None
    if episode:
        if episode['pulse_date'] not in sessions:raise ValueError('PULSE_NOT_IN_ACCEPTED_CALENDAR')
        age=sessions.index(target)-sessions.index(episode['pulse_date'])
    put('pulse_age_sessions',age,NO_HISTORY if age is None else None)
    basket=episode.get('frozen_basket',[]) if episode else []
    ratios=[];price_truth={}
    for member in basket:
        now=observed(current.get(member),'close',target)
        base=episode['pulse_baseline'].get(member)
        pulse=episode['pulse_closes'].get(member)
        frozen_basis=episode.get('price_basis_ids',{}).get(member)
        if frozen_basis is None or (current.get(member) or {}).get('price_basis_id')!=frozen_basis:
            now=None
        if now is not None and base is not None and base>0:ratios.append(now/base-1)
        price_truth[member]=None if now is None or pulse is None else now>=pulse
    cumulative=sum(ratios)/len(basket) if basket and len(ratios)==len(basket) else None
    put('basket_cumulative_return',cumulative,NO_HISTORY if not episode else 'INCOMPLETE_FROZEN_BASKET' if cumulative is None else None)
    pulse_return=episode.get('pulse_basket_return') if episode else None
    price_retention=cumulative/pulse_return if cumulative is not None and pulse_return is not None and pulse_return>0 else None
    price_quality='NOT_APPLICABLE' if pulse_return is not None and pulse_return<=0 else 'ACCEPTED' if price_retention is not None else 'UNKNOWN'
    put('sector_price_retention_core',price_retention, 'NONPOSITIVE_PULSE_RETURN' if price_quality=='NOT_APPLICABLE' else NO_HISTORY if not episode else 'INCOMPLETE_FROZEN_BASKET' if price_retention is None else None,price_quality)
    seed_value,seed_quality,seed_reason=retention(episode.get('base_seed_set') if episode else None,seed_truth or {})
    if not seed_capability:seed_value,seed_quality,seed_reason=None,'UNKNOWN',SEED_DEGRADED
    put('base_seed_retention',seed_value,seed_reason,seed_quality)
    value,quality,reason=retention(episode.get('breadth_positive_set') if episode else None,price_truth)
    put('breadth_retention',value,reason,quality)
    common=set(native['member_ids'])&set(prior_members or ())
    prior_date=prior.get('target_trade_date') if prior else None
    old={m:observed((prior_core or {}).get(m),'rps20',prior_date) for m in common}
    old_set=None if prior_members is None or any(v is None for v in old.values()) else {m for m,v in old.items() if v>=80}
    now={m:None if (v:=observed(current.get(m),'rps20',target)) is None else v>=80 for m in common}
    put('strong_prev',len(old_set) if old_set is not None else None,NO_HISTORY if old_set is None else None)
    value,quality,reason=retention(old_set,now);put('strong_member_retention_1',value,reason,quality)
    dq=facts.get('dq5',{}).get('value');breadth=facts.get('breadth_delta1',{}).get('value')
    prev_count=prior.get('negative_out_count',0) if prior else 0
    negative_count=prev_count if dq is None or breadth is None else prev_count+1 if dq<0 and breadth<0 else 0
    put('negative_out_consecutive_evaluable_sessions',negative_count,NO_HISTORY if prior is None else None,'UNKNOWN' if prior is None else 'ACCEPTED')
    table=truth_table(contract,facts,parameters)
    output='UNKNOWN';reasons=[]
    if prior is None:
        reasons=[NO_HISTORY]
    else:
        output='NONE'
        for rule in contract['ordered_reduction']:
            if rule not in table:continue
            state=table[rule]['state']
            if state=='UNKNOWN':
                # Mature-only unknown cannot poison early IN/ACCEPTED.
                if rule in {'ROTATION_EXPANDING','ROTATION_REACCELERATING'}:continue
                output='UNKNOWN';reasons=[table[rule]['reason_code'] or 'REQUIRED_BRANCH_UNKNOWN'];break
            if state=='TRUE':
                output=contract.get('fallback_outputs',{}).get(rule,rule)
                if output=='PRIOR_ROTATION_STATE':output=prior['output_state']
                break
    if output=='ROTATION_PULSE':
        # Pulse basket membership was already known at the previous session.
        basket=sorted(set(prior_members or ()))
        baseline={m:observed((prior_core or {}).get(m),'close',prior_date) for m in basket}
        pulse_closes={m:observed(current.get(m),'close',target) for m in basket}
        basis={m:(prior_core or {}).get(m,{}).get('price_basis_id') for m in basket}
        basis_ready=all(basis[m] is not None and basis[m]==current.get(m,{}).get('price_basis_id') for m in basket)
        if not basket or not basis_ready or any(v is None or v<=0 for v in baseline.values()) or any(v is None for v in pulse_closes.values()):
            output='UNKNOWN';reasons=['PULSE_BASELINE_UNAVAILABLE']
        else:
            seed_set=None if not seed_capability or any((seed_truth or {}).get(m) is None for m in basket) else sorted(m for m in basket if seed_truth[m] is True)
            positive=None if any(observed(current.get(m),'ret1',target) is None for m in basket) else sorted(m for m in basket if observed(current[m],'ret1',target)>0)
            episode=dict(rotation_episode_id=ast_digest({'sector_id':sid,'pulse_date':target,'basket':basket,'membership_snapshot_id':prior['membership_snapshot_id']}),
                pulse_date=target,frozen_basket=basket,base_seed_set=seed_set,breadth_positive_set=positive,
                pulse_baseline=baseline,pulse_closes=pulse_closes,price_basis_ids=basis,pulse_basket_return=sum(pulse_closes[m]/baseline[m]-1 for m in basket)/len(basket),accepted=False,terminated=False)
    if episode:
        if output in {'ROTATION_ACCEPTED','ROTATION_EXPANDING','ROTATION_REACCELERATING'}:episode['accepted']=True
        if output in {'ROTATION_OUT','ROTATION_FAILED'}:episode['terminated']=True
    return dict(model_contract_id=contract['model_contract_id'],output_state=output,quality='UNKNOWN' if output=='UNKNOWN' else 'ACCEPTED',
        reason_codes=reasons,episode=episode,episode_age_sessions=age,prior_rotation_state=prior.get('output_state') if prior else None,
        predicates=table,fields=facts,negative_out_count=negative_count,native_fields=native['fields'])
