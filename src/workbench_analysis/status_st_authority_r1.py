"""A12 sole versioned status/ST producers. Provider fields are cross-checks only."""
from __future__ import annotations
from datetime import date,datetime
import hashlib,json
from pathlib import Path

ST_MAPPING={'NORMAL':'0','ST':'1','STAR_ST':'1','RISK_WARNING':'1','UNKNOWN':None}

def load_accepted_dated_evidence(root:Path,contract:dict):
    facts=[]
    for binding in contract['accepted_dated_evidence']:
        p=(root/binding['path']).resolve()
        if not p.is_relative_to(root.resolve()) or hashlib.sha256(p.read_bytes()).hexdigest()!=binding['sha256']:
            raise ValueError('DATED_AUTHORITY_BINDING_INVALID')
        source=json.loads(p.read_text(encoding='utf8'))
        if source.get('external_acceptance')!='EXTERNALLY_ACCEPTED' or source.get('source_role')!='FIELD_AUTHORITY' or source.get('owner_kind') not in ('LOCAL_DATED_IDENTITY','OFFICIAL_EXCHANGE_NOTICE'):
            raise ValueError('DATED_AUTHORITY_NOT_ACCEPTED_LOCAL_OR_OFFICIAL')
        for fact in source['facts']:
            f={**fact,'authority_binding':binding}
            date.fromisoformat(f['effective_from'])
            if f.get('effective_to'):date.fromisoformat(f['effective_to'])
            stamp=datetime.fromisoformat(source['observed_at'].replace('Z','+00:00'))
            if stamp.tzinfo is None:raise ValueError('AUTHORITY_OBSERVATION_TIMEZONE_REQUIRED')
            f['observed_at']=source['observed_at'];facts.append(f)
    return tuple(facts)

def applicable(member,facts,field):
    day=member['trade_date'];date.fromisoformat(day)
    out=[]
    for f in facts:
        if f.get('security_id')!=member['security_id'] or f.get('field')!=field:continue
        if f.get('source_security_key') and f['source_security_key']!=member['source_security_key']:continue
        if f['effective_from']<=day and (not f.get('effective_to') or day<=f['effective_to']):out.append(f)
    values={f['value'] for f in out}
    if len(values)>1:return None,'CONFLICTING_DATED_FORMAL_AUTHORITY'
    return out[0] if out else None,'NO_ACCEPTED_DATED_FORMAL_AUTHORITY'

def produce_trading_status(member,facts=(),provider_tradestatus=None):
    fact,reason=applicable(member,facts,'trading_status')
    if member.get('source_bar_present') is True:status,owner='ACTUAL_TRADED','LOCAL_TDX_ACTUAL_BAR'
    elif fact and fact['value']=='SUSPENDED':status,owner='SUSPENDED','ACCEPTED_LOCAL_OR_OFFICIAL_DATED_NOTICE'
    elif fact and fact['value']=='SHOULD_TRADE':status,owner='DATA_GAP','ACCEPTED_EXPLICIT_DATED_SHOULD_TRADE'
    else:status,owner='UNKNOWN',reason
    return dict(security_id=member['security_id'],source_security_key=member['source_security_key'],trade_date=member['trade_date'],
        contract_id='LOCAL_DATED_TRADING_STATUS_V2',status=status,status_source=owner,
        authority_binding=fact.get('authority_binding') if fact and status!='ACTUAL_TRADED' else None,
        provider_tradestatus=provider_tradestatus,provider_role='SUPPLEMENTAL_CROSSCHECK',
        provider_conflict=provider_tradestatus in ('0','1') and status=='ACTUAL_TRADED' and provider_tradestatus!='1',
        lineage='RECONSTRUCTED_CORRECTED',first_availability_at_target_proven=False)

def produce_st(member,facts=(),provider_is_st=None):
    fact,reason=applicable(member,facts,'st_state')
    value=fact['value'] if fact and fact['value'] in ST_MAPPING else 'UNKNOWN'
    return dict(security_id=member['security_id'],source_security_key=member['source_security_key'],trade_date=member['trade_date'],
        contract_id='LOCAL_DATED_ST_IDENTITY_V2',is_st=ST_MAPPING[value],st_state=value,
        risk_status='NORMAL' if value=='NORMAL' else 'RISK_WARNING' if ST_MAPPING[value]=='1' else 'UNKNOWN',
        source_owner='ACCEPTED_LOCAL_DATED_ST_IDENTITY' if fact else reason,authority_binding=fact.get('authority_binding') if fact else None,
        provider_is_st=provider_is_st,provider_role='SUPPLEMENTAL_CROSSCHECK',provider_conflict=fact is not None and provider_is_st in ('0','1') and ST_MAPPING[value]!=provider_is_st,
        lineage='RECONSTRUCTED_CORRECTED',first_availability_at_target_proven=False)
