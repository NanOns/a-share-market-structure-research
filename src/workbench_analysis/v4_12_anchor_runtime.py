"""Contract-scoped immutable Anchor/Event construction and observation views."""
import copy
from decimal import Decimal
from .v4_12_structure_io import digest

def coordinate_view(anchor,price_basis,adjustment_source_revision,observation_date,revision):
    original=copy.deepcopy(anchor)
    same=(anchor['anchor_price_basis'],anchor['adjustment_source_revision'])==(price_basis,adjustment_source_revision)
    coefficients=anchor.get('frozen_transform_coefficients')
    ready=same and coefficients is not None
    lower=upper=None
    if ready:
        lower=str(Decimal(str(anchor['anchor_raw_lower']))*Decimal(coefficients['mul'])+Decimal(coefficients['add']))
        upper=str(Decimal(str(anchor['anchor_raw_upper']))*Decimal(coefficients['mul'])+Decimal(coefficients['add']))
    view=dict(anchor_id=anchor['anchor_id'],observation_trade_date=observation_date,observation_revision=revision,
        original_anchor_digest=digest(anchor),creation_coordinate=anchor['creation_coordinate'],
        current_comparison_coordinate=dict(price_basis=price_basis,adjustment_source_revision=adjustment_source_revision),
        rebase_lineage=[],quality='KNOWN' if ready else 'UNKNOWN',reason=None if ready else 'PRICE_BASIS_MISMATCH' if not same else 'UNKNOWN_ACCEPTED_RAW_ANCHOR_COORDINATE_UNAVAILABLE',
        lower=lower,upper=upper)
    assert anchor==original
    return view

def create_anchor(contracts,anchor_type,security_id,trade_date,available_at,values,source_event_id,source_fact_digest,raw_bounds=None,raw_source_ref=None,frozen_coefficients=None):
    spec=next(r for r in contracts.config['anchor_schema']['types'] if r['anchor_type']==anchor_type)
    if spec.get('blocked_reason'):raise ValueError('BLOCKED_ANCHOR_CAPABILITY:'+spec['blocked_reason'])
    if raw_bounds is None or raw_source_ref is None or frozen_coefficients is None:raise ValueError('UNKNOWN_ACCEPTED_RAW_ANCHOR_COORDINATE_UNAVAILABLE')
    if Decimal(frozen_coefficients['mul'])<=0:raise ValueError('INVALID_FROZEN_TRANSFORM')
    numeric_bounds=tuple(float(x) for x in raw_bounds)
    if any(Decimal(str(n))!=Decimal(str(v)) for n,v in zip(numeric_bounds,raw_bounds)):
        raise ValueError('UNKNOWN_ACCEPTED_RAW_ANCHOR_PRECISION_UNAVAILABLE')
    if numeric_bounds[0]>numeric_bounds[1]:raise ValueError('INVALID_RAW_ANCHOR_BOUNDS')
    coordinate=dict(price_basis=values['price_basis'],adjustment_source_revision=values['adjustment_source_revision'])
    identity=dict(contract_id=contracts.config['structure_event_contract']['contract_id'],security_id=security_id,source_event_id=source_event_id,
        anchor_type=anchor_type,anchor_trade_date=trade_date,source_fact_digest=source_fact_digest,**coordinate)
    anchor=dict(anchor_id=digest(identity),security_id=security_id,anchor_trade_date=trade_date,available_date=trade_date,available_at=available_at,
        anchor_type=anchor_type,anchor_raw_lower=numeric_bounds[0],anchor_raw_upper=numeric_bounds[1],anchor_price_basis=values['price_basis'],
        adjustment_contract_id=contracts.config['anchor_coordinate_contract']['historical_adjustment_contract']['path'],
        adjustment_source_identity=raw_source_ref.get('sha256',digest(raw_source_ref)),adjustment_source_revision=values['adjustment_source_revision'],adjustment_asof=available_at,
        anchor_basis_trade_date=trade_date,frozen_transform_coefficients=copy.deepcopy(frozen_coefficients),source_event_id=source_event_id,source_fact_digest=source_fact_digest,
        creation_coordinate=coordinate,current_comparison_coordinate=coordinate,rebase_lineage=[],corporate_action_transition=[],quality='KNOWN',reason=None,
        raw_source_binding=copy.deepcopy(raw_source_ref))
    from jsonschema import Draft202012Validator
    schema=contracts.config['anchor_schema']['schema']
    Draft202012Validator(schema).validate({key:anchor[key] for key in schema['required']})
    return anchor

def create_event(contracts,anchor,revision,prior_session_event_id=None):
    row=dict(event_id=anchor['source_event_id'],security_id=anchor['security_id'],event_type=next(r['source_event'] for r in contracts.config['anchor_schema']['types'] if r['anchor_type']==anchor['anchor_type']),
        created_trade_date=anchor['anchor_trade_date'],available_at=anchor['available_at'],contract_id=contracts.config['structure_event_contract']['contract_id'],
        parameter_set_digest=contracts.refs['parameter_set']['sha256'],source_fact_digest=anchor['source_fact_digest'],anchor_id=anchor['anchor_id'],
        prior_session_event_id=prior_session_event_id,frozen_invalidation_ast=copy.deepcopy(contracts.config['machine_ast']['definitions']['episode_invalidated']),
        observation_revision=revision,quality='KNOWN',candidate_only=True)
    return row
