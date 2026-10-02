"""Per-episode projections and display selection; no detector rules or authority grants."""
from copy import deepcopy
from decimal import Decimal,InvalidOperation
from .v4_12_ast_runtime import ASTEngine
from .v4_12_anchor_runtime import coordinate_view
from .v4_12_structure_io import digest

def validate_state_set(contract,row):
    if any(n not in row for n in contract['required_fields']) or 'anchor' in row or 'event' in row:raise ValueError('V2_STATE_SET_REQUIRED')
    states=row['anchor_states']
    if not isinstance(states,list) or len({s['anchor_id'] for s in states})!=len(states):raise ValueError('DUPLICATE_ANCHOR_ID')
    for s in states:
        if any(n not in s for n in contract['anchor_state_required']):raise ValueError('INCOMPLETE_ANCHOR_STATE')
        if s['anchor_id']!=s['anchor']['anchor_id'] or s['event']['anchor_id']!=s['anchor_id'] or s['owning_anchor_id']!=s['anchor_id']:raise ValueError('ANCHOR_EVENT_BINDING_MISMATCH')
        if s['owning_episode_id']!=s['event']['event_id'] or s['anchor']['source_event_id']!=s['event']['event_id']:raise ValueError('OWNING_EPISODE_MUTATION')
        if s['counter_state_digest']!=digest(s['counter_state']):raise ValueError('COUNTER_STATE_DIGEST_MISMATCH')
        if s['created_this_session'] and (any(s['counter_state'][n]!=0 for n in contract['counter_fields']) or s['state_observations']['support']['state']!='IDLE'):raise ValueError('NEW_ANCHOR_SELF_CONFIRMATION')
    if row['active_anchor_id'] is not None and row['active_anchor_id'] not in {s['anchor_id'] for s in states}:raise ValueError('ACTIVE_ANCHOR_NOT_IN_SET')

def project_state(contract,c,anchor,event,common,context_result=None,prior=None):
    """Only copies completed runtime inputs/derived outputs; no source reads."""
    fresh=context_result is None
    if fresh:
        counters={n:0 for n in contract['counter_fields']};outputs={}
        for machine in contract['per_anchor_machines']:
            state=contract['new_anchor']['state_observations'].get(machine)
            outputs[machine]=dict(value=state,state=state or 'UNKNOWN',quality='KNOWN' if state is not None else 'UNKNOWN',reason=[] if state else ['NEW_ANCHOR_NO_POST_CREATION_OBSERVATION'])
        envelope=dict(active_anchor_id=anchor['anchor_id'],anchor_view_asof_t=coordinate_view(anchor,common['price_basis']['value'],common['adjustment_source_revision']['value'],anchor['available_date'],'creation'),support_state='IDLE',acceptance_state=outputs['acceptance']['state'],retest_count=0,last_known_support_state='IDLE',invalidation_facts=[],basic_pullback_state=outputs['pullback']['state'],basic_recovery_state=outputs['recovery']['state'])
        derived={};bindings=common;last='IDLE';invalid=[];validity='VALID';overlay_digest=digest(common)
    else:
        obs=context_result['observation'];bindings=context_result['bindings']['fields'];derived=obs['derived'];outputs={n:obs['outputs'][n] for n in contract['per_anchor_machines']};envelope=obs['frozen_output_envelope'];last=envelope['last_known_support_state'];invalid=envelope['invalidation_facts'];overlay_digest=obs['input_digest']
        counters={n:derived.get('next_test_count' if n=='test_count' else n,bindings.get(n,{})).get('value') for n in contract['counter_fields']}
        for n,v in counters.items():
            if v is not None:
                number=Decimal(str(v))
                if number<0 or number!=number.to_integral_value():raise ValueError('INVALID_RUNTIME_COUNTER')
                counters[n]=int(number)
        hard=derived['hard_invalidated'];validity='INVALIDATED' if hard['value'] is True else 'VALID' if hard['quality']=='KNOWN' and hard['value'] is False else 'UNKNOWN'
    def fact(v=None,reason=None):return dict(value=v,quality='KNOWN' if v is not None and v!='UNKNOWN' else 'UNKNOWN',reason=reason or ([] if v is not None and v!='UNKNOWN' else ['MISSING_RUNTIME_PROJECTION']))
    def source(n):return derived.get(n,bindings.get(n,fact()))
    facts={}
    for spec in contract['fact_projections']:
        n,kind,src=spec['field'],spec['kind'],spec['source']
        if kind=='anchor':facts[n]=fact(anchor.get(src))
        elif kind=='counter':facts[n]=fact(counters[src],source('next_test_count' if src=='test_count' else src).get('reason'))
        elif kind=='support':facts[n]=fact(last,outputs['support']['reason'])
        elif kind=='event':facts[n]=fact(validity=='VALID') if n=='prior_valid_event' and validity!='UNKNOWN' else fact(reason=source('hard_invalidated').get('reason')) if n=='prior_valid_event' else fact(True)
        elif kind=='machine_flag':
            v=outputs.get(src)
            if v is None and context_result:v=context_result['observation']['outputs'][src]
            # Breakout is global; an Anchor stores its own event type and prior flag.
            if src=='breakout':
                spec=next(s for s in c.config['anchor_schema']['types'] if s['anchor_type']==anchor['anchor_type'])
                facts[n]=prior['facts'][n] if prior else fact(spec['creation_rule']=='breakout_trigger')
            else:facts[n]=fact(v['value'] in spec['states']) if v and v['quality']=='KNOWN' else fact(reason=v['reason'] if v else ['NO_POST_CREATION_OBSERVATION'])
        elif kind=='runtime':
            if n in ['anchor_original_atr','anchor_original_price']:facts[n]=prior['facts'][n] if prior else source(src)
            elif fresh and n=='prior_hard_invalidated':facts[n]=fact(False)
            elif fresh and n=='prior_adjacent_evaluable':facts[n]=fact(False)
            elif fresh and n=='prior_retest_qualified':facts[n]=fact(False)
            else:facts[n]=source(src)
    return dict(anchor_id=anchor['anchor_id'],anchor=deepcopy(anchor),event=deepcopy(event),facts=facts,counter_state=counters,counter_state_digest=digest(counters),counter_contract_id=c.config['time_counter_contract']['contract_id'],
        state_observations=outputs,last_known_support_state=last,invalidation_facts=invalid,validity=validity,stale=any(r['quality']=='UNKNOWN' for r in outputs.values()),created_this_session=fresh,owning_episode_id=event['event_id'],owning_anchor_id=anchor['anchor_id'],output_envelope=envelope,overlay_digest=overlay_digest)

def active_selector(contract,c,states,common,date,revision):
    selector=contract['selector'];unknown=dict(active_anchor_id=None,quality='UNKNOWN',reason='ACTIVE_ANCHOR_SELECTION_UNKNOWN')
    if selector['active_anchor_sort']!=c.config['output_schema']['active_anchor_sort'] or selector['first_item_fallback'] is not False:raise ValueError('SELECTOR_CONTRACT_MISMATCH')
    if any(s['validity']=='UNKNOWN' for s in states):return unknown
    eligible=[s for s in states if s['validity']=='VALID']
    if not eligible:return dict(active_anchor_id=None,quality='KNOWN',reason='NO_ACTIVE_ANCHOR')
    if len(eligible)==1:return dict(active_anchor_id=next(iter(eligible))['anchor_id'],quality='KNOWN',reason='SOLE_ELIGIBLE_ANCHOR')
    ranking=[]
    for s in eligible:
        try:
            view=coordinate_view(s['anchor'],common['price_basis']['value'],common['adjustment_source_revision']['value'],date,revision)
            close=common['C'];atr=common['atr_prior_view']
            if view['quality']!='KNOWN' or close['quality']!='KNOWN' or atr['quality']!='KNOWN':return unknown
            lower,upper,value,scale=map(lambda v:Decimal(str(v)),[view['lower'],view['upper'],close['value'],atr['value']])
            if any(not v.is_finite() for v in [lower,upper,value,scale]) or scale<=0:return unknown
            distance=max(lower-value,value-upper,Decimal(0))/scale
            from datetime import date as Date
            day=Date.fromisoformat(s['anchor']['anchor_trade_date']).toordinal()
            ranking.append((distance,-day,s['anchor_id']))
        except (InvalidOperation,ValueError,TypeError):return unknown
    winner=min(ranking)[2]
    return dict(active_anchor_id=winner,quality='KNOWN',reason='FROZEN_ACTIVE_ANCHOR_SORT',ranking_keys=[dict(anchor_id=i,distance=str(d),date_desc=n) for d,n,i in sorted(ranking)])
