"""Reconstructed sector maturity/health from the accepted V4 sector Owner."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

CONTRACT='SECTOR_LIFECYCLE_RECONSTRUCTED_V1'
PARAMETERS='config/sector_lifecycle_reconstructed_v1.json'


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')


def _value(row,name):
    cell=(row.get('fields') or {}).get(name)
    if not isinstance(cell,dict) or cell.get('quality') in ('UNKNOWN','SOURCE_INCOMPLETE','DATA_UNAVAILABLE'):
        return None
    value=cell.get('value')
    return value if isinstance(value,(int,float)) and not isinstance(value,bool) else None


def _quality(row,name):
    return ((row.get('fields') or {}).get(name) or {}).get('quality')


def _evaluate_maturity(row,parameters):
    names=parameters['maturity']['required_inputs']
    values={name:_value(row,name) for name in names}
    unknown=[name for name,value in values.items() if value is None]
    coverage=values.get('sector_quote_coverage')
    if unknown:
        return 'UNKNOWN',['REQUIRED_INPUT_MISSING'],[],unknown
    if coverage<parameters['maturity']['minimum_quote_coverage']:
        return 'UNKNOWN',['QUOTE_COVERAGE_BELOW_MINIMUM'],[],[]
    predicates={}
    for name,spec in parameters['maturity']['predicates'].items():
        value=values[spec['field']]
        predicates[name]=(value>spec['value'] if spec['operator']=='gt' else value>=spec['value'])
    matched=[name for name,value in predicates.items() if value]
    if len(matched)>=parameters['maturity']['mature']['minimum_matched_predicates']:
        state='MATURE'
    elif len(matched)>=parameters['maturity']['developing']['minimum_matched_predicates']:
        state='DEVELOPING'
    elif predicates['RS5_POSITIVE'] and predicates['BREADTH5_BROAD']:
        state='EARLY'
    else:
        state='NONE'
    return state,[],matched,[]


def _evaluate_health(current,prior,prior_prior,parameters):
    required=parameters['health']['required_inputs']
    values={name:_value(current,name) for name in required}
    unknown=[name for name,value in values.items() if value is None]
    if prior is None:
        unknown.append('prior_sector_owner')
    if unknown:
        return 'UNKNOWN',['REQUIRED_INPUT_OR_PRIOR_MISSING'],[],unknown
    if values['sector_quote_coverage']<parameters['health']['minimum_quote_coverage']:
        return 'UNKNOWN',['QUOTE_COVERAGE_BELOW_MINIMUM'],[],[]
    previous={name:_value(prior,name) for name in ('sector_rs5','breadth_ret1','seed_retention')}
    unknown_prior=[name for name,value in previous.items() if value is None]
    if unknown_prior:
        return 'UNKNOWN',['PRIOR_INPUT_MISSING'],[],unknown_prior
    prior_snapshot=current.get('membership_snapshot_id')
    previous_snapshot=prior.get('membership_snapshot_id')
    if prior_snapshot and previous_snapshot and prior_snapshot!=previous_snapshot:
        return 'UNKNOWN',['MEMBERSHIP_SNAPSHOT_NOT_COMPARABLE'],[],['membership_snapshot_id']
    earlier={name:_value(prior_prior,name) if prior_prior else None for name in ('sector_rs5','breadth_ret1','seed_retention')}
    names=('sector_rs5','breadth_ret1','seed_retention')
    current_values={name:_value(current,name) for name in names}
    # Compare the T/T-1 change to the preceding daily change; a single negative
    # close or return is not treated as an outflow or a risk event.
    matched=[];unknown_predicates=[]
    for name,label in zip(names,parameters['health']['weakening_predicates']):
        if earlier[name] is None:unknown_predicates.append(label)
        elif current_values[name]-previous[name] < previous[name]-earlier[name]:matched.append(label)
    if values['sector_rs5']<0 and values['breadth_ret5']<0.25:
        state='DAMAGED'
    elif len(matched)>=parameters['health']['weakening_minimum_matches']:
        state='WEAKENING'
    elif matched:
        state='WATCH'
    elif unknown_predicates:
        # NONE means all three comparisons were evaluated and none weakened.
        # Missing earlier values cannot be treated as evidence of stability.
        state='UNKNOWN'
    else:
        state='NONE'
    reasons=['WEAKENING_COMPARISON_INPUT_MISSING'] if state=='UNKNOWN' else []
    return state,reasons,matched,unknown_predicates


def evaluate_sector(sector_id,history,session_dates,source_bindings,parameter_document,*,producer_sha256):
    """Produce one dated state; caller provides only accepted, non-future rows."""
    params=parameter_document
    if params.get('contract_id')!=CONTRACT:
        raise ValueError('SECTOR_LIFECYCLE_PARAMETER_CONTRACT_MISMATCH')
    ordered=sorted((row for row in history if row.get('sector_id')==sector_id),key=lambda row:row.get('trade_date',''))
    if not ordered:raise ValueError('SECTOR_LIFECYCLE_CURRENT_SECTOR_NOT_FOUND')
    current=ordered[-1];as_of=current.get('trade_date') or current.get('target_trade_date')
    if not as_of or as_of not in session_dates:raise ValueError('SECTOR_LIFECYCLE_DATE_NOT_ACCEPTED')
    if any((row.get('trade_date') or row.get('target_trade_date'))>as_of for row in ordered):
        raise ValueError('SECTOR_LIFECYCLE_FUTURE_INPUT')
    expected=[day for day in session_dates if day<=as_of][-params['historical_window_sessions']:]
    by_date={(row.get('trade_date') or row.get('target_trade_date')):row for row in ordered}
    matched_sessions=[day for day in expected if day in by_date]
    window_complete=len(expected)==params['historical_window_sessions'] and matched_sessions==expected
    prior=by_date.get(expected[-2]) if len(expected)>=2 else None
    prior_prior=by_date.get(expected[-3]) if len(expected)>=3 else None
    if not window_complete:
        maturity='UNKNOWN';maturity_reasons=['LESS_THAN_5_ACCEPTED_SESSIONS'];maturity_matched=[];maturity_unknown=['historical_window']
        health='UNKNOWN';health_reasons=['LESS_THAN_5_ACCEPTED_SESSIONS'];health_matched=[];health_unknown=['historical_window']
    else:
        readiness=((current.get('fields') or {}).get('membership_ready') or {}).get('value')
        if readiness is not True:
            maturity='UNKNOWN';maturity_reasons=['MEMBERSHIP_NOT_READY'];maturity_matched=[];maturity_unknown=['membership_ready']
            health='UNKNOWN';health_reasons=['MEMBERSHIP_NOT_READY'];health_matched=[];health_unknown=['membership_ready']
        else:
            maturity,maturity_reasons,maturity_matched,maturity_unknown=_evaluate_maturity(current,params)
            health,health_reasons,health_matched,health_unknown=_evaluate_health(current,prior,prior_prior,params)
    if window_complete and prior is not None:
        prior_readiness=((prior.get('fields') or {}).get('membership_ready') or {}).get('value')
        if prior_readiness is True:
            prior_maturity,prior_maturity_reasons,prior_maturity_matched,prior_maturity_unknown=_evaluate_maturity(prior,params)
            prior_health,prior_health_reasons,prior_health_matched,prior_health_unknown=_evaluate_health(prior,prior_prior,by_date.get(expected[-4]),params)
        else:
            prior_maturity='UNKNOWN';prior_maturity_reasons=['MEMBERSHIP_NOT_READY'];prior_maturity_matched=[];prior_maturity_unknown=['membership_ready']
            prior_health='UNKNOWN';prior_health_reasons=['MEMBERSHIP_NOT_READY'];prior_health_matched=[];prior_health_unknown=['membership_ready']
    else:
        prior_maturity='UNKNOWN';prior_maturity_reasons=['PRIOR_SESSION_NOT_AVAILABLE'];prior_maturity_matched=[];prior_maturity_unknown=['prior_session']
        prior_health='UNKNOWN';prior_health_reasons=['PRIOR_SESSION_NOT_AVAILABLE'];prior_health_matched=[];prior_health_unknown=['prior_session']
    psha=hashlib.sha256(canonical(params)).hexdigest()
    inputs={name:_value(current,name) for name in set(params['maturity']['required_inputs'])|set(params['health']['required_inputs'])}
    inputs['membership_ready']=((current.get('fields') or {}).get('membership_ready') or {}).get('value')
    prior_inputs={name:_value(prior,name) if prior else None for name in ('sector_rs5','breadth_ret1','seed_retention')}
    rotation_state=current.get('rotation_state')
    prior_rotation_state=prior.get('rotation_state') if prior else None
    input_digest=hashlib.sha256(canonical(dict(sector_id=sector_id,T0=as_of,inputs=inputs,prior=prior_inputs,
        rotation_state=rotation_state,prior_rotation_state=prior_rotation_state,
        source_bindings=source_bindings,sessions=matched_sessions))).hexdigest()
    completeness=dict(required_sessions=params['historical_window_sessions'],observed_sessions=len(matched_sessions),
        window_complete=window_complete,unknown_maturity_inputs=maturity_unknown,unknown_health_inputs=health_unknown,
        quality_counts={name:_quality(current,name) for name in inputs})
    return dict(contract_id=CONTRACT,version='1.0.0',T0=as_of,sector_id=sector_id,
        evidence_scope='CURRENT_RECONSTRUCTED_RESEARCH_ONLY',AS_RECORDED=False,PIT_ELIGIBLE=False,
        maturity=dict(value=maturity,current=maturity,prior=prior_maturity,matches=maturity_matched,
            unknown_predicates=maturity_unknown,reason_codes=maturity_reasons),
        health=dict(value=health,current=health,prior=prior_health,matches=health_matched,
            unknown_predicates=health_unknown,reason_codes=health_reasons),
        prior_state_reason=dict(maturity=prior_maturity_reasons or prior_maturity_matched,health=prior_health_reasons or prior_health_matched),
        state_reason=dict(maturity=maturity_reasons or maturity_matched,health=health_reasons or health_matched),
        rotation_context=dict(current=rotation_state,prior=prior_rotation_state,
            source=(source_bindings.get(as_of,{}) or {}).get('rotation')),
        failure_boundary='INCOMPLETE_OR_LOW_COVERAGE_INPUTS_REMAIN_UNKNOWN; NONE_MEANS_COMPLETE_INPUTS_WITH_NO_MATCH',
        input_completeness=completeness,session_window=matched_sessions,
        producer_sha256=producer_sha256,parameter_digest=psha,input_digest=input_digest,
        source_bindings=source_bindings)


def load_parameters(root):
    raw=(Path(root)/PARAMETERS).read_bytes();document=json.loads(raw)
    if document.get('contract_id')!=CONTRACT:raise ValueError('SECTOR_LIFECYCLE_PARAMETER_CONTRACT_MISMATCH')
    return document,hashlib.sha256(raw).hexdigest()
