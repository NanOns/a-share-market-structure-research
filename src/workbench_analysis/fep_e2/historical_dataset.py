"""Real-source historical engineering replay. Never a historical PIT capture."""
from collections import Counter
from dataclasses import asdict
from functools import lru_cache
import gzip
import hashlib
import json
from pathlib import Path
import types

from workbench_analysis.fep_e1.contracts import digest

LINEAGE = dict(evidence_origin='RECONSTRUCTED_CORRECTED', execution_mode='HISTORICAL_SIMULATION',
               AS_RECORDED=False, FIRST_OBSERVED=False, REAL_OOS=False, production=False, shadow=False)


def admissible(row):
    if any(row.get(k) != v for k,v in LINEAGE.items()):
        raise ValueError('E2R1R1_RECONSTRUCTION_LINEAGE')
    if row.get('source_kind') != 'REAL_ACCEPTED_HISTORICAL_SOURCE':
        raise ValueError('E2R1R1_SYNTHETIC_ADMISSION_FORBIDDEN')


def feature_cutoff(rows, date):
    if any(r['date'] > date or r.get('is_synthetic_fill') for r in rows):
        raise ValueError('E2R1R1_FUTURE_OR_SYNTHETIC_FEATURE')


def freeze_window(discovery):
    permitted={'source_bindings','sessions','warmup_sessions','maximum_enabled_horizon','owner_capability'}
    if set(discovery)-permitted:
        raise ValueError('E2R1R1_WINDOW_OUTCOME_INPUT')
    sessions=discovery['sessions'];warmup=discovery['warmup_sessions']
    if sessions != sorted(set(sessions)) or len(sessions) <= warmup:
        raise ValueError('E2R1R1_NO_RECONSTRUCTIBLE_WINDOW')
    result=dict(start=sessions[warmup],end=sessions[-1],start_ordinal=warmup,
                end_ordinal=len(sessions)-1,warmup_sessions=warmup,
                right_edge_policy='RETAIN_RIGHT_CENSORED_DENOMINATOR',discovery_digest=digest(discovery))
    result['logical_digest']=digest(result)
    return result


def verify_window(window, discovery):
    if window != freeze_window(discovery):raise ValueError('E2R1R1_WINDOW_RESELECTED')


def write_gzip(path, rows):
    """Stable ordered payload, deterministic gzip envelope and atomic publication."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp')
    with tmp.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0,compresslevel=1) as stream:
            for row in rows:
                stream.write((json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode())
    tmp.replace(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_gzip(path):
    with gzip.open(path,'rt',encoding='utf-8') as stream:
        for line in stream:yield json.loads(line)


def slots_for(sid, raw_rows, sessions, members, statuses):
    from src.v4.adjustment_basis_r4 import parent_bar,admission
    rows={r['trade_date']:r for r in raw_rows};result=[]
    first=min(members) if members else len(sessions)
    for i,date in enumerate(sessions):
        row=rows.get(int(date.replace('-','')))
        if row:
            slot=parent_bar(row)
            slot.update(raw_actual_bar=True,has_actual_bar=admission(slot) is None,
                        identity_verified=i in members,accepted_source_digest=digest(row),
                        accepted_trading_status=row['trading_status'])
        else:
            state=statuses.get(i,'PRE_LISTING' if i<first else 'UNKNOWN')
            slot=dict(date=date,security_id=sid,raw_actual_bar=False,has_actual_bar=False,
                      identity_verified=i in members,accepted_trading_status=state,quality='UNKNOWN',
                      price_basis=None,adjustment_source_revision=None,mul=None,add=None,
                      **{k:None for k in ('open','high','low','close','amount','volume')})
        result.append(slot)
    return result


def feature_worker(job):
    """Accepted numerical owners, complete date prefix, no outcome owner invocation."""
    sid,raw_rows,sessions,members,statuses,start,output=job
    from src.v4.adjustment_basis_r4 import observations
    from src.v4.factors.core import compute_core
    from src.v4.profile_primitives import derive_daily
    from src.v4.profile_core import compression,ma_structure,extension_risk,position,participation,severe_extension
    slots=slots_for(sid,raw_rows,sessions,set(members),statuses)
    states={(sid,r['date']):r['accepted_trading_status'] for r in slots}
    history=observations(slots,sid,states)
    bars=[];dated=[];outputs=[];previous_ma=None
    for i,(slot,observation) in enumerate(zip(slots,history)):
        # Identity is independently supplied by the dated universe; never guessed.
        if observation.bar and not slot['identity_verified']:
            from src.v4.factors.core import Observation
            history[i]=Observation(slot['date'],'IDENTITY_UNKNOWN');observation=history[i]
        dated.append((slot['date'],'ACTUAL_TRADED' if observation.state=='ACTUAL' else
                      'SUSPENDED' if observation.state=='CONFIRMED_SUSPENSION' else observation.state))
        if observation.bar:
            bars.append(dict(trade_date=slot['date'],adjusted_quality='READY',qfq_close=slot['close'],
                             qfq_high=slot['high'],qfq_low=slot['low'],amount=slot['amount']))
        if i<start-23:continue
        core=compute_core(history[:i+1],sid,asof=slot['date'])
        factors={k:dict(value=v.value,quality_state=v.quality_state) for k,v in core.items()}
        primitives=derive_daily(bars,factors,dated,slot['date'],sessions[:i+1])
        values={k:v.value for k,v in core.items()};values.update({k:v.value for k,v in primitives.items()})
        values.update(close=slot['close'] if observation.state=='ACTUAL' else None,previous_close=slots[i-1]['close'] if i else None,
                      previous_ma20=previous_ma)
        profiles={name:asdict(fn(values)) for name,fn in [('compression',compression),('trend',ma_structure),
                   ('risk',extension_risk),('position',position),('participation',participation)]}
        # severe_extension consumes the risk State, not the factor mapping.
        profiles['severe']=asdict(severe_extension(extension_risk(values)))
        outputs.append(dict(date=slot['date'],ordinal=i,values=values,profiles=profiles,
            actual=observation.state=='ACTUAL',identity_verified=slot['identity_verified'],
            core_output_digest=digest({k:v.output_digest for k,v in core.items()}),
            primitive_output_digest=digest({k:asdict(v) for k,v in primitives.items()}),
            source_window_digest=digest([(r['date'],r.get('accepted_source_digest'),r['accepted_trading_status']) for r in slots[:i+1]]),
            max_feature_source_trade_date=slot['date']))
        previous_ma=core['ma20'].value
    sha=write_gzip(Path(output)/(sid+'.jsonl.gz'),outputs)
    return dict(entity_id=sid,rows=len(outputs),sha256=sha)


@lru_cache(maxsize=1)
def owner_packages():
    from src.v4 import confirmation,base_seed,stock_prewatch
    root=Path(__file__).resolve().parents[3]
    seed=base_seed._parameter_values(json.loads((root/'config/v4_07_parameter_set_v1.json').read_bytes()))
    prewatch=stock_prewatch.load_package(root)
    confirmation_package=confirmation.package()
    return root,seed,prewatch,confirmation_package


def scoped_policy(discovery, applicability, frozen_at):
    """Independent repetition budgets, never a return/performance fit."""
    import math
    allowed={'dependence','coverage','class_counts','input_digest','excluded'}
    if set(discovery)!=allowed:raise ValueError('E2R1R1_POLICY_PERFORMANCE_INPUT')
    def forbidden_keys(value):
        if isinstance(value,dict):
            if any(k in {'outcome','mean','weighted_mean','positive_rate','positive_empirical_frequency','p25','p50','p75','quantile','Priority','best_backoff'} for k in value):
                raise ValueError('E2R1R1_POLICY_PERFORMANCE_INPUT')
            for child in value.values():forbidden_keys(child)
        elif isinstance(value,list):
            for child in value:forbidden_keys(child)
    forbidden_keys(discovery)
    counts=discovery['dependence']
    values={k:max(2,math.ceil(math.sqrt(counts[k]))) for k in ('rows','dates','blocks','entities','episodes')}
    class_budget=max(2,math.ceil(math.sqrt(counts['blocks'])))
    values.update(class_min=class_budget,max_missing_fraction=1/class_budget,max_total_variation=1/class_budget)
    return dict(policy_id='FEP_E2_ENTRY_CORE_ABS_RETURN_T1_RECONSTRUCTED_V1',
        applicability=applicability,freeze_before_statistics_at=frozen_at,values=values,
        required_classes=['POS','NEG'],representation_dimensions={
            k:('UNAVAILABLE_NOT_GATED' if k in ('sector','regime') else 'ASSESSED')
            for k in ('trade_date','sector','regime','risk','feature_support')},
        derivation=dict(contract='INDEPENDENT_REPETITION_SQRT_BUDGET_V1',support_discovery_digest=digest(discovery),
            count_rule='ceil(sqrt(available independent inventory)), lower bound 2; class budget from nonoverlap blocks',
            completeness_budget='Missingness and total variation each <=1/ceil(sqrt(independent blocks)); at most one repetition-budget unit can be unrepresented. Engineering quality budget, not predictive power',
            performance_inputs_used=False,limitations='Engineering descriptive capability only; no confidence or effectiveness claim'))


def verify_label(row, outcome):
    if row['selected_label_digest']!=digest(outcome['R_N']) or row['outcome_revision_id']!=outcome['outcome_revision_id']:
        raise ValueError('E2R1R1_LABEL_REVISION_DIGEST_MISMATCH')


def verify_stage_order(dataset_at, discovery_at, policy_at, statistics_at):
    from workbench_analysis.fep_e1.contracts import instant
    times=list(map(instant,(dataset_at,discovery_at,policy_at,statistics_at)))
    if not times[0]<times[1]<times[2]<times[3]:raise ValueError('E2R1R1_STAGE_ORDER')


def resolve_policy(registry, applicability):
    matches=[p for p in registry['policies'] if p['applicability']==applicability]
    if len(matches)!=1:raise ValueError('E2R1R1_POLICY_SCOPE_UNSET_OR_AMBIGUOUS')
    return matches[0]


def rank_worker(job):
    from src.v4.factors.core import rps_midrank
    horizon,ordinal,mapping,universe=job
    scores,coverage=rps_midrank(mapping,universe)
    return horizon,ordinal,scores,coverage
