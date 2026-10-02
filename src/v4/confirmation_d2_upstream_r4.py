"""Target-date candidate D2 facts, reusing accepted owner pure rules.

Old 9/28 Seed/PREWATCH rows cannot be dated 9/30. This explicit adapter
derives new source-bound candidates and retains unknown episode authorities.
"""
from dataclasses import asdict
from statistics import fmean
from .factors.core import Bar,Observation,compute_core
from .profile_primitives import derive_daily
from .profile_core import compression,ma_structure,extension_risk,severe_extension,participation
from .base_seed import _eval,_parameter_values
from .stock_prewatch import evaluate,load_package
from .confirmation import digest
from decimal import Decimal
from .state_identity import canonical
from .adjustment_basis_r4 import observations as accepted_observations
from functools import lru_cache
import json

@lru_cache(maxsize=1)
def owner_packages(root):
    """Read immutable owner contracts once per batch, never cache outputs."""
    return _parameter_values(json.loads((root/'config/v4_07_parameter_set_v1.json').read_bytes())),load_package(root)

def derive(calculation,root,accepted_states=None):
    sid=calculation['security_id'];day=calculation['trade_date'];slots=calculation['window'];observations=[];bars=[];statuses=[]
    accepted_states=accepted_states or {}
    enriched=[dict(r,accepted_source_digest=digest(r)) for r in slots]
    source_states=dict(accepted_states)
    for r in slots:
        if r.get('accepted_trading_status') is not None:source_states.setdefault((sid,r['date']),r['accepted_trading_status'])
    observations=accepted_observations(enriched,sid,source_states)
    for r,o in zip(slots,observations):
        state=o.state;bar=o.bar
        statuses.append((r['date'],'ACTUAL_TRADED' if state=='ACTUAL' else 'SUSPENDED' if state=='CONFIRMED_SUSPENSION' else state))
        if bar:bars.append(dict(trade_date=r['date'],adjusted_quality='READY',qfq_close=r['close'],qfq_high=r['high'],qfq_low=r['low'],amount=r['amount']))
    factors={k:asdict(v) for k,v in compute_core(observations,sid,asof=day).items()}
    previous_factors=compute_core(observations[:-1],sid,asof=slots[-2]['date'])
    previous_close=observations[-2].bar.close if observations[-2].state=='ACTUAL' else None
    primitives=derive_daily(bars,factors,statuses,day,[r['date'] for r in slots]);values={k:r['value'] for k,r in factors.items()}
    values.update({k:v.value for k,v in primitives.items()});values['close']=slots[-1].get('close') if slots[-1]['has_actual_bar'] else None
    comp=compression(values);ma=ma_structure(values);risk=extension_risk(values);severe=severe_extension(risk);part=participation(values)
    delta=calculation['values'].get('rps5_delta3');delta=delta*100 if delta is not None else None
    def fact(value,reason='REAL_UPSTREAM_INPUT_UNKNOWN'):return dict(value=value,reason=reason if value is None else None)
    def enum(s):return fact(None if s.value=='UNKNOWN' else s.value,s.unknown_reason or 'UPSTREAM_ENUM_UNKNOWN')
    seedfacts=dict(research_universe=fact(True),actual_bar=fact(slots[-1]['raw_actual_bar']),price_identity_READY=fact(True if slots[-1]['has_actual_bar'] else None),
        minimum_liquidity=fact(primitives['minimum_liquidity'].value),core_price_damage=fact(values['core_price_damage']),severe_extension=fact(severe.value),
        bias20_atr=fact(values['bias20_atr']),compression_state=enum(comp),delta3=fact(delta),ma_structure_state=enum(ma),
        close_t=fact(values['close']),ma20_t=fact(values['ma20']),
        close_t_minus_1=fact(previous_close),ma20_t_minus_1=fact(previous_factors['ma20'].value,previous_factors['ma20'].unknown_reason or 'REAL_UPSTREAM_INPUT_UNKNOWN'),
        core_participation_result=enum(part))
    seed_parameters,prewatch_package=owner_packages(root)
    seed=_eval(seedfacts,seed_parameters)
    quality='TRUE' if values['core_price_damage'] is not None and seed['base_seed_state']!='UNKNOWN' and seed['quality']=='COMPLETE' else 'UNKNOWN'
    stockfacts=dict(base_seed_state=seed['base_seed_state'],mandatory_core_quality_ready=quality,delta3=delta,
        compression_state=comp.value,ma_structure_state=ma.value,core_extension_risk=risk.value)
    stock=evaluate(stockfacts,prewatch_package)
    out=dict(SEED=seed['base_seed_state'],PREWATCH=stock['raw_qualification'],core_price_damage='UNKNOWN' if values['core_price_damage'] is None else 'TRUE' if values['core_price_damage'] else 'FALSE',
        risk=risk.value,delta3='UNKNOWN' if delta is None else delta)
    return out,dict(observation_states=[dict(trade_date=r.trade_date,state=r.state,accepted_trading_status=accepted_states.get((sid,r.trade_date))) for r in observations],
        core_factors=factors,primitives={k:asdict(v) for k,v in primitives.items()},profile=dict(compression=asdict(comp),ma=asdict(ma),risk=asdict(risk)),
        seed_facts=seedfacts,seed=seed,prewatch_facts=stockfacts,prewatch=stock)
