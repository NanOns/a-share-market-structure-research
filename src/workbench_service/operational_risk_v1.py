"""Daily risk transitions from accepted observations with explicit state order.

First visibility is a coverage event, not a worsening event. Incomparable or
unknown states remain visible and do not get forced into a direction.
"""
from collections import Counter

CONTRACT = 'V4_OPERATIONAL_RISK_CHANGE_R2'
FAMILIES = ('STOCK_STRUCTURE_RISK', 'SECTOR_ECOLOGY_RISK', 'MARKET_PRESSURE_RISK')

ORDERS = {
    FAMILIES[0]: {'NONE': 0, 'DAMAGED': 1},
    FAMILIES[1]: {'NONE': 0, 'WATCH': 1, 'WEAKENING': 2, 'DAMAGED': 3},
    FAMILIES[2]: {'NONE': 0, 'PRESSURE': 1},
}


def _value(row, key):
    cell = ((row or {}).get('fields') or {}).get(key) or {}
    return cell.get('value') if isinstance(cell, dict) else cell


def _cell(row, key):
    return ((row or {}).get('fields') or {}).get(key) or {}


def _family(name, rows, states, previous, source, day, *, reason=None):
    order = ORDERS[name]
    changes=[]; counts=Counter(); transition_denominators=Counter()
    total=len(rows); known=0; worsened=0; eased=0; uncomparable=0; newly=0
    for row in rows:
        identity=row.get('entity_id') or row.get('sector_id')
        state=states.get(identity)
        has_prior=identity in previous
        old=previous.get(identity)
        if state not in order:
            counts['UNKNOWN'] += 1
            continue
        known += 1
        if not has_prior:
            change='NEWLY_OBSERVABLE'; newly += 1
            transition_denominators[change] += 1
        elif old not in order:
            change='UNCOMPARABLE'; uncomparable += 1
            transition_denominators[change] += 1
        elif old == state:
            change='UNCHANGED'; transition_denominators[change] += 1
        elif order[state] > order[old]:
            change='WORSENED'; worsened += 1
            transition_denominators[change] += 1
        else:
            change='EASED'; eased += 1
            transition_denominators[change] += 1
        counts[state] += 1
        if change != 'UNCHANGED':
            changes.append(dict(entity_id=identity,display_name=row.get('display_name'),symbol=row.get('symbol'),
                prior_state=old if has_prior else None,current_state=state,change=change,
                reason_code=('NO_COMPARABLE_PRIOR' if change in ('NEWLY_OBSERVABLE','UNCOMPARABLE') else 'ACCEPTED_OWNER_STATE_CHANGE'),
                source=source,T0=day,
                evidence={k:_cell(row,k) for k in ('core_price_damage','health','maturity') if _cell(row,k)}))
    transition_total=sum(transition_denominators.values())
    return dict(contract_id=CONTRACT,family=name,T0=day,status='READY' if known else 'SOURCE_INCOMPLETE',
        numerator=known,denominator=total,coverage=known/total if total else 0.0,counts=dict(counts),
        transitions=dict(transition_denominators),transition_total=transition_total,
        newly_observable_count=newly,worsened_count=worsened,eased_count=eased,
        uncomparable_count=uncomparable,
        changes=changes[:30],change_total=len(changes),risk_worsening_total=worsened,
        source=source,prior_comparable_count=sum(v in order for v in previous.values()),
        reason=reason if known else 'NO_EVALUABLE_ACCEPTED_OWNER_FIELDS')


def build_stock_family(current, prior, source, day):
    states={}; previous={}
    for row in current:
        value=_value(row,'core_price_damage')
        states[row['entity_id']]=('DAMAGED' if value is True else 'NONE' if value is False else None)
    for row in prior:
        value=_value(row,'core_price_damage')
        previous[row['entity_id']]=('DAMAGED' if value is True else 'NONE' if value is False else None)
    return _family(FAMILIES[0],current,states,previous,source,day,
        reason='CORE_FACTOR_V1.core_price_damage; same security IDs compared with prior accepted session')


def build_sector_family(current, lifecycle, source, day):
    states={}; rows=[]; previous={}
    for row in current:
        sid=row.get('entity_id') or row.get('sector_id')
        life=lifecycle.get(sid)
        if not life:
            states[sid]=None; rows.append(row); continue
        cell=life.get('health',{}); value=cell.get('current')
        states[sid]=value if value in ORDERS[FAMILIES[1]] else None
        previous[sid]=cell.get('prior')
        rowcopy=dict(row); rowcopy['fields']=dict(row.get('fields') or {})
        rowcopy['fields']['health']={'value':value,'quality':'KNOWN' if value is not None else 'UNKNOWN'}
        rows.append(rowcopy)
    return _family(FAMILIES[1],rows,states,previous,source,day,
        reason='SECTOR_LIFECYCLE_RECONSTRUCTED_V1 health; reconstructed latest-membership research only')


def build_market_family(current, source, day):
    if not current:
        return dict(contract_id=CONTRACT,family=FAMILIES[2],T0=day,status='SOURCE_INCOMPLETE',numerator=0,
            denominator=0,coverage=0.0,counts={'UNKNOWN':1},transitions={'UNCOMPARABLE':1},
            changes=[],change_total=0,source=source,reason='ACCEPTED_MARKET_AXIS_OWNER_NOT_AVAILABLE')
    axes=current.get('row') or current.get('axes') or {}
    quality=current.get('field_quality') or (current.get('raw') or {}).get('axes',{}).get('field_quality',{})
    stress=axes.get('stress_level'); stress_change=axes.get('stress_change')
    valid=stress in ('LOW','NORMAL','ELEVATED','HIGH') and quality.get('stress_level',{}).get('quality_state','OBSERVED')=='OBSERVED'
    current_state=('PRESSURE' if stress in ('ELEVATED','HIGH') else 'NONE') if valid else None
    transition='UNKNOWN' if not valid else 'WORSENED' if stress_change=='INCREASING' else 'EASED' if stress_change=='DECLINING' else 'UNCHANGED'
    # Preserve stress_change as an observed source value. It is not projected
    # into another family's state machine or described as a universal signal.
    changes=[]
    if valid and transition in ('WORSENED','EASED'):
        changes=[dict(entity_id='MARKET',display_name='全市场',prior_state='OBSERVED_PRIOR',current_state=current_state,
            change=transition,reason_code='ACCEPTED_MARKET_STRESS_CHANGE',stress_level=stress,
            stress_change=stress_change,source=source,T0=day)]
    return dict(contract_id=CONTRACT,family=FAMILIES[2],T0=day,status='READY' if valid else 'SOURCE_INCOMPLETE',
        numerator=1 if valid else 0,denominator=1,coverage=1.0 if valid else 0.0,
        counts={current_state:1} if valid else {'UNKNOWN':1},
        transitions={transition:1},transition_total=1,
        newly_observable_count=0,worsened_count=int(transition=='WORSENED'),eased_count=int(transition=='EASED'),
        uncomparable_count=int(transition=='UNKNOWN'),changes=changes,change_total=len(changes),
        risk_worsening_total=int(transition=='WORSENED'),source=source,
        reason='Observed V4 market stress axes; source stress_change preserved as recorded' if valid else 'MARKET_STRESS_AXIS_NOT_EVALUABLE',
        axes=dict(stress_level=stress,stress_change=stress_change),composite_regime_status='CANDIDATE_UNACCEPTED')
