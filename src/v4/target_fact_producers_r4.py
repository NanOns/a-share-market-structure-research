"""Exact legacy target facts from explicitly bound accepted source windows.

Derived outputs are sealed candidates, never external acceptance. Price windows
retain master-session gaps and require the accepted price basis and source revision.
"""
from datetime import datetime,timezone
from collections import Counter
from pathlib import Path
import json,math
from .confirmation import digest
from workbench_analysis.today_research_factors_v3_3 import calculate_today_facts
from workbench_analysis.stock_attention import classify_stock_attention

CONTRACT='V4_11_TARGET_FACT_PRODUCERS_R4A_V1'
PARAMETERS='V4_11_TARGET_FACT_PARAMETERS_R4A_V1'
DIAGNOSTIC={'pullback_episode_confirmed':'EXACT_FROZEN_PRIOR_EPISODE_SOURCE_UNAVAILABLE',
            'current_with_loo_breadth_support':'VERSIONED_TARGET_LOO_ADMISSION_NOT_SEALED'}

def finite(value):
    return value is not None and type(value) in (int,float) and math.isfinite(value)

def produce(window,feature,*,normal_universe,identity_compatible,parameters):
    """No source lookup or downstream dependency; legacy functions stay intact."""
    if not window:raise ValueError('EMPTY_MASTER_WINDOW')
    f=calculate_today_facts(window,liquidity20_amount_gte=parameters['thresholds']['stock_signals']['risk']['liquidity20_amount_gte'])
    # Amount facts use raw observations in an explicit identity affine coordinate.
    # Only the amount outputs are consumed; this cannot supply any adjusted price.
    raw_window=[]
    for r in window:
        raw_window.append(dict(r,has_actual_bar=r.get('raw_actual_bar') is True,
            **{k:r.get('raw_'+k) for k in ('open','high','low','close')}))
    raw_f=calculate_today_facts(raw_window,liquidity20_amount_gte=parameters['thresholds']['stock_signals']['risk']['liquidity20_amount_gte'])
    signals=classify_stock_attention(feature,parameters)
    current=window[-1].get('close') if window[-1].get('has_actual_bar') else None
    previous=window[-2].get('high') if len(window)>1 and window[-2].get('has_actual_bar') else None
    def ratio(a,b):return a/b if finite(a) and finite(b) and b>0 else None
    prior=[]
    for i in range(len(window)-6,len(window)-1):
        seq=window[i-19:i+1] if i>=19 else []
        valid=len(seq)==20 and all(r.get('has_actual_bar') and finite(r.get('close')) for r in seq)
        prior.append(window[i]['close']<sum(r['close'] for r in seq)/20 if valid else None)
    ma20p3=feature.get('ma20_prior3')
    result=dict(f,amr20_mean_prior=raw_f['amr20_mean_prior'],liq20=raw_f['liq20'],liq20_amount=raw_f['liq20_amount'],
        normal_universe=normal_universe,actual_bar=window[-1].get('raw_actual_bar') is True,
        input_identity_compatible=identity_compatible,window_valid=True if f['quality']=='READY' else None,
        breakout_v3=signals['breakout'],setup_v3=signals['setup'],recovery_v3=signals['recovery'],
        trend_background_v3=signals['trend_background'],structure_break_v3=signals['structure_break'],extended_v3=signals['extended'],
        close_to_ma5=ratio(current,f['ma5']),close_to_ma20=ratio(current,f['ma20']),ma5_to_ma20=ratio(f['ma5'],f['ma20']),
        ma20_nondeclining_3=f['ma20']>=ma20p3 if finite(f['ma20']) and finite(ma20p3) else None,
        prior5_below_ma20_count=sum(prior) if len(prior)==5 and all(x is not None for x in prior) else None,
        close_above_prior_high=current>previous if finite(current) and finite(previous) else None,
        rps20=feature.get('rps20'),rps5_delta3=feature.get('rps5_delta3'),
        pullback_episode_confirmed=None,current_with_loo_breadth_support=None)
    return result,signals

def seal(publication):
    material={k:v for k,v in publication.items() if k not in ('publication_id','logical_digest')}
    checksum=digest(material)
    return dict(material,logical_digest=checksum,publication_id='V4_11_R4_FACTS:'+checksum)

def validate(publication,root,*,expected_sources=None):
    from scripts.next_round_bundle_r1 import exact
    if publication.get('producer_contract_id')!=CONTRACT:raise ValueError('WRONG_PRODUCER')
    if publication.get('parameter_set_id')!=PARAMETERS:raise ValueError('WRONG_PARAMETER_SET')
    if publication.get('scope')!='REAL_ACCEPTED_SOURCE_CANDIDATE' or publication.get('accepted') is not False:raise ValueError('CANDIDATE_SCOPE_REQUIRED')
    if publication.get('AS_RECORDED') is not False:raise ValueError('AS_RECORDED_OVERCLAIM')
    cutoff=datetime.fromisoformat(publication['knowledge_cutoff'])
    if cutoff.tzinfo is None or cutoff>datetime.now(timezone.utc):raise ValueError('FUTURE_TIMESTAMP')
    for ref in publication['source_bindings']:exact(ref)
    if expected_sources is not None and publication['source_bindings']!=expected_sources:raise ValueError('WRONG_SOURCE_DIGEST')
    source_digest=digest(publication['source_bindings'])
    if publication.get('source_digest')!=source_digest:raise ValueError('WRONG_SOURCE_DIGEST')
    ids=[r['security_id'] for r in publication['rows']]
    if ids!=sorted(set(ids)):raise ValueError('DUPLICATE_OR_UNORDERED_ENTITY')
    for row in publication['rows']:
        if row['trade_date']!=publication['trade_date']:raise ValueError('TARGET_DATE_MISMATCH')
        for field,fact in row['facts'].items():
            if fact.get('time_role') in ('FINAL_STATE','FOCUS','SAME_DAY_DOWNSTREAM','FUTURE_OUTCOME','ONLINE_SUPPLEMENTAL'):raise ValueError('SAME_DAY_FEEDBACK_REJECTED')
            if fact.get('source_digest')!=source_digest:raise ValueError('WRONG_SOURCE_DIGEST')
            if datetime.fromisoformat(fact['system_available_at'])>cutoff:raise ValueError('FUTURE_TIMESTAMP')
            if fact['value'] is None and (fact['quality']!='UNKNOWN' or not fact['reason']):raise ValueError('MISSING_FACT_REASON_REQUIRED')
            if fact['value'] is not None and fact['quality']!='KNOWN':raise ValueError('FACT_QUALITY_CONFLICT')
            if field in DIAGNOSTIC and fact['value'] is not None:raise ValueError('DIAGNOSTIC_FACT_IN_FORMAL_D0')
    if seal(publication)!=publication:raise ValueError('PUBLICATION_DIGEST_MISMATCH')
    if expected_sources is None:
        import gzip
        active=json.loads((Path(root)/'reports/v4_11_r4a/R4A_SEALED_PRODUCER_SET.json').read_bytes())
        ref=active['publications'].get(publication['trade_date'])
        if ref is None or json.loads(gzip.decompress(exact(ref).read_bytes()))!=publication:raise ValueError('NOT_IN_SEALED_PRODUCER_SET')
    return publication
