"""Versioned target owner projection; accepted unavailable t-1 stays unavailable.

Source computations construct candidate Core records only. BASE_SEED and
PREWATCH use the unchanged accepted projections and evaluators on those records.
"""
from copy import deepcopy
from dataclasses import asdict
from functools import lru_cache
import json
from . import base_seed, stock_prewatch, profile_core
from .profile_primitives import derive_daily
from .factors.core import compute_core
from .adjustment_basis_r4 import observations
from .confirmation import digest

CONTRACT='V4_11_R5A_OWNER_INPUT_ADAPTER_V1'
UNAVAILABLE='ACCEPTED_T_MINUS_1_CORE_FIELD_UNAVAILABLE'

@lru_cache(maxsize=1)
def packages(root):
    return base_seed._parameter_values(json.loads((root/'config/v4_07_parameter_set_v1.json').read_bytes())),stock_prewatch.load_package(root)

def project_seed(core,factor,context):
    """Same projection at parity and target dates; membership must be verified."""
    facts=base_seed._normalize_facts(core,factor,context)
    if core['security_id'] not in context['identity_ids']:
        facts['research_universe']=base_seed._unknown('TARGET_SEALED_UNIVERSE_MEMBERSHIP_INVALID')
        facts['price_identity_READY']=base_seed._unknown('TARGET_IDENTITY_BINDING_INVALID')
    return facts

def project_owners(core,factor,seed_context,stock_context,root):
    parameters,package=packages(root)
    facts=project_seed(core,factor,seed_context)
    seed=base_seed._eval(facts,parameters)
    seed_record=dict(security_id=core['security_id'],trade_date=core['trade_date'],publication_id=stock_context['source_publication_id'],source_publication_id=core['publication_id'],source_core_logical_digest=stock_context['core_logical_digest'],model_contract_id='BASE_SEED_V1',**seed)
    prewatch_facts,reasons,provenance=stock_prewatch.project(core,factor,seed_record,stock_context,package)
    prewatch=stock_prewatch.evaluate(prewatch_facts,package)
    waiting=[dict(field_id=p['predicate'],reason='UPSTREAM_PRIORITY_OR_REQUIRED_UNKNOWN') for p in prewatch['unknown_predicates']]
    waiting += [dict(field_id='mandatory_core_quality_ready',reason=r) for r in reasons]
    waiting += prewatch_facts['priority_lineage_failures']
    stock_output=dict(**prewatch,base_seed_state=prewatch_facts['base_seed_state'],mandatory_core_quality_ready=prewatch_facts['mandatory_core_quality_ready'],waiting_for=waiting,quality='COMPLETE' if not waiting else 'PARTIAL_UNKNOWN')
    return dict(seed_facts=facts,seed=seed,prewatch_facts=prewatch_facts,prewatch=stock_output,prewatch_source_projection=provenance,prewatch_required_reasons=reasons)

def target_records(calculation,identity,status,delta,context):
    sid=calculation['security_id'];day=calculation['trade_date'];slots=calculation['window']
    enriched=[dict(r,accepted_source_digest=digest(r)) for r in slots]
    states={(sid,r['date']):r['accepted_trading_status'] for r in slots if r.get('accepted_trading_status')}
    obs=observations(enriched,sid,states)
    fields={k:asdict(v) for k,v in compute_core(obs,sid,asof=day).items()}
    bars=[dict(trade_date=r['date'],adjusted_quality='READY',qfq_close=r['close'],qfq_high=r['high'],qfq_low=r['low'],amount=r['amount']) for r,o in zip(slots,obs) if o.bar]
    statuses=[(r['date'],'ACTUAL_TRADED' if o.state=='ACTUAL' else 'SUSPENDED' if o.state=='CONFIRMED_SUSPENSION' else o.state) for r,o in zip(slots,obs)]
    derived={k:asdict(v) for k,v in derive_daily(bars,fields,statuses,day,[r['date'] for r in slots]).items()}
    values={k:v['value'] for k,v in fields.items()};values.update({k:v['value'] for k,v in derived.items()})
    values['close']=slots[-1].get('close') if slots[-1].get('has_actual_bar') else None
    risk=profile_core.extension_risk(values)
    states_out={k:asdict(fn(values)) for k,fn in dict(trend_state=profile_core.trend,compression_state=profile_core.compression,ma_structure_state=profile_core.ma_structure,core_extension_risk=profile_core.extension_risk,core_participation_result=profile_core.participation).items()}
    states_out['severe_extension']=asdict(profile_core.severe_extension(risk))
    for item in states_out.values():item['parameter_set_id']='V4_04_CORE_PROFILE_PARAMETER_SET_V1'
    for item in fields.values():item.update(target_trade_date=day,source_asof=day,max_source_trade_date=day.replace('-',''),available_at=context['knowledge_cutoff'])
    # The accepted A02 Core amendment retains this accepted relative contract.
    # Never relabel it CORE_FACTOR_V1 to evade PREWATCH's provenance predicate.
    relative=dict(delta,contract_id='V4_03_RELATIVE_FACTOR_V1',parameter_set_id='V4_03_CORE_FACTOR_PARAMETER_SET_V1',input_digest=digest(delta),output_digest=digest(delta),window_identity=digest(delta),target_trade_date=day,source_asof=day,max_source_trade_date=day.replace('-',''),available_at=context['knowledge_cutoff'])
    fields['rps5_delta3']=relative
    primitive={k:deepcopy(v) for k,v in fields.items()}
    status_value=status.get('status',status.get('trading_status'))
    if status.get('status_conflict') or status.get('provider_conflicts'):status_value='UNKNOWN'
    symbol=identity.get('source_security_key')
    identity_valid=identity.get('identity_status')=='IDENTITY_BOUND' and identity.get('security_id')==sid and identity.get('trade_date')==day and identity.get('security_type')=='A_STOCK' and symbol==slots[-1].get('source_security_key')
    core=dict(security_id=sid,symbol=symbol if identity_valid else None,board=identity.get('board_scope'),trade_date=day,publication_id=context['profile_row_publication_id'],historical_as_recorded_claim=False,coordinate_basis='T0_CURRENT_COORDINATE',formal_publication_at=context['knowledge_cutoff'],max_source_trade_date=day.replace('-',''),trading_status=status_value,states=states_out,derived_fields=derived,primitive_quality=primitive)
    factor=dict(security_id=sid,trade_date=day,publication_id=context['profile_row_publication_id'],historical_as_recorded_claim=False,coordinate_basis='T0_CURRENT_COORDINATE',formal_publication_at=context['knowledge_cutoff'],max_source_trade_date=day.replace('-',''),fields=fields)
    return core,factor
