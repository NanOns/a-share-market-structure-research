"""Daily risk-change facts derived only from accepted V4 observations.

These are descriptive changes in three separate domains. They do not infer
trading intent, predict returns, or use Focus membership as a universe.
"""
from collections import Counter

CONTRACT='V4_OPERATIONAL_RISK_CHANGE_R1'
FAMILIES=('STOCK_STRUCTURE_RISK','SECTOR_ECOLOGY_RISK','MARKET_PRESSURE_RISK')


def _value(row,key):
    return ((row or {}).get('fields') or {}).get(key,{}).get('value')


def _cell(row,key):
    return ((row or {}).get('fields') or {}).get(key) or {}


def _family(name, rows, states, previous, source, day, *, reason=None):
    total=len(rows);known=sum(state is not None for state in states.values())
    changes=[];counts=Counter()
    for row in rows:
        identity=row.get('entity_id') or row.get('sector_id')
        state=states.get(identity)
        old=previous.get(identity)
        if state is None:counts['UNKNOWN']+=1;continue
        counts[state]+=1
        old_state=old
        change='NEW' if old_state is None else 'UNCHANGED' if old_state==state else 'WORSENED' if state in ('DAMAGED','WEAKENING','PRESSURE') else 'EASED'
        if change!='UNCHANGED':
            changes.append(dict(entity_id=identity,display_name=row.get('display_name'),symbol=row.get('symbol'),
                prior_state=old_state,current_state=state,change=change,
                reason_code='ACCEPTED_OWNER_STATE_CHANGE',source=source,T0=day,
                evidence={k:_cell(row,k) for k in ('core_price_damage','health','maturity') if _cell(row,k)}))
    return dict(contract_id=CONTRACT,family=name,T0=day,status='READY' if known else 'SOURCE_INCOMPLETE',
        numerator=known,denominator=total,coverage=known/total if total else 0.0,counts=dict(counts),
        changes=changes[:30],change_total=len(changes),source=source,prior_comparable_count=sum(x is not None for x in previous.values()),
        reason=reason if known else 'NO_EVALUABLE_ACCEPTED_OWNER_FIELDS')


def build_stock_family(current, prior, source, day):
    states={};previous={}
    for row in current:
        val=_value(row,'core_price_damage')
        states[row['entity_id']]=('DAMAGED' if val is True else 'NONE' if val is False else None)
    for row in prior:
        val=_value(row,'core_price_damage')
        previous[row['entity_id']]=('DAMAGED' if val is True else 'NONE' if val is False else None)
    return _family(FAMILIES[0],current,states,previous,source,day,
        reason='CORE_FACTOR_V1.core_price_damage; same security IDs compared with prior accepted session')


def build_sector_family(current, lifecycle, source, day):
    states={};rows=[];previous={}
    for row in current:
        sid=row.get('entity_id')
        life=lifecycle.get(sid)
        if not life:states[sid]=None;rows.append(row);continue
        cell=life.get('health',{});value=cell.get('current')
        states[sid]=value if value in ('DAMAGED','WEAKENING','WATCH','NONE') else None
        prior=cell.get('prior')
        previous[sid]=prior if prior in ('DAMAGED','WEAKENING','WATCH','NONE') else None
        rowcopy=dict(row);rowcopy['fields']=dict(row.get('fields') or {});rowcopy['fields']['health']={'value':value,'quality':'KNOWN' if value is not None else 'UNKNOWN'};rows.append(rowcopy)
    return _family(FAMILIES[1],rows,states,previous,source,day,
        reason='SECTOR_LIFECYCLE_RECONSTRUCTED_V1 health; reconstructed latest-membership research only')


def build_market_family(current, source, day):
    if not current:
        return dict(contract_id=CONTRACT,family=FAMILIES[2],T0=day,status='SOURCE_INCOMPLETE',numerator=0,
            denominator=0,coverage=0.0,counts={},changes=[],change_total=0,source=source,
            reason='ACCEPTED_MARKET_AXIS_OWNER_NOT_AVAILABLE')
    axes=current.get('row') or current.get('axes') or {}
    quality=current.get('field_quality') or (current.get('raw') or {}).get('axes',{}).get('field_quality',{})
    stress=axes.get('stress_level')
    change=axes.get('stress_change')
    valid=stress in ('LOW','NORMAL','ELEVATED','HIGH') and quality.get('stress_level',{}).get('quality_state','OBSERVED')=='OBSERVED'
    status='READY' if valid else 'SOURCE_INCOMPLETE'
    current_state=('PRESSURE' if stress in ('ELEVATED','HIGH') else 'NONE') if valid else None
    changes=[]
    if valid and change in ('INCREASING','DECLINING'):
        changes=[dict(entity_id='MARKET',display_name='全市场',prior_state='OBSERVED_PRIOR',current_state=current_state,
            change='WORSENED' if change=='INCREASING' else 'EASED',reason_code='ACCEPTED_MARKET_STRESS_CHANGE',
            stress_level=stress,stress_change=change,source=source,T0=day)]
    return dict(contract_id=CONTRACT,family=FAMILIES[2],T0=day,status=status,numerator=1 if valid else 0,
        denominator=1,coverage=1.0 if valid else 0.0,counts={current_state:1} if valid else {'UNKNOWN':1},
        changes=changes,change_total=len(changes),source=source,
        reason='Observed V4 market stress axes; composite regime remains candidate unless separately accepted'
        if valid else 'MARKET_STRESS_AXIS_NOT_EVALUABLE',axes=dict(stress_level=stress,stress_change=change),
        composite_regime_status='CANDIDATE_UNACCEPTED')
