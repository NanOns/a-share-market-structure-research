"""CONDITIONAL_EXPECTANCY_V1, fixed backoff and exact rational date weights."""
from collections import Counter
from fractions import Fraction
import math
from workbench_analysis.fep_e1.contracts import digest, instant
from .support import identity, gate, BASE
from .input import bind

LEVELS = (('L4', ('regime', 'trend', 'position', 'risk')),
          ('L3', ('regime', 'trend', 'risk')), ('L2', ('regime',)), ('L1', ()))


def weights(rows):
    counts = Counter(r['trade_date'] for r in rows)
    return [Fraction(1, len(counts)*counts[r['trade_date']]) for r in rows]


def quantile(values, mass, q):
    if not values or len(values) != len(mass) or not 0 < q <= 1 or any(w <= 0 for w in mass):
        raise ValueError('E2_INVALID_QUANTILE')
    total = sum(mass)
    cumulative = Fraction(0)
    for value, weight in sorted(zip(values, mass)):
        cumulative += weight/total
        if cumulative >= q:
            return value
    raise ValueError('E2_QUANTILE_UNREACHABLE')


def statistics(rows, kind, classes):
    mass = weights(rows)
    values = [r['outcome'] for r in rows]
    if not rows:
        return {}, digest([])
    if kind == 'CONTINUOUS':
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
            raise ValueError('E2_INVALID_CONTINUOUS')
        stats = dict(weighted_mean=sum(float(w)*v for w,v in zip(mass,values)),
                     positive_empirical_frequency=sum(float(w) for w,v in zip(mass,values) if v > 0),
                     p25=quantile(values,mass,Fraction(1,4)), p50=quantile(values,mass,Fraction(1,2)),
                     p75=quantile(values,mass,Fraction(3,4)), minimum=min(values), maximum=max(values),
                     dispersion_is_confidence_interval=False)
    elif kind == 'CATEGORICAL':
        if 'NONE' not in classes or any(v not in classes for v in values):
            raise ValueError('E2_INVALID_CATEGORY')
        stats = dict(observed_weighted_frequency={c:sum(float(w) for w,v in zip(mass,values) if v == c)
                                                 for c in classes})
    elif kind == 'ANY_EVENTS':
        if any(set(v) != set(classes) or any(type(x) is not bool for x in v.values()) for v in values):
            raise ValueError('E2_INVALID_EVENT')
        stats = dict(observed_weighted_frequency={c:sum(float(w) for w,v in zip(mass,values) if v[c])
                                                 for c in classes}, jointly_normalized=False)
    else:
        raise ValueError('E2_TARGET_KIND_DISABLED')
    binding = sorted((r['observation_id'], str(w)) for r,w in zip(rows,mass))
    return stats, digest(binding)


def validate_input(dataset):
    payload = {k:v for k,v in dataset.items() if k != 'digest'}
    if digest(payload) != dataset['digest']:
        raise ValueError('E2_DATASET_DIGEST')
    frozen = dataset['e1_frozen_payload']
    metadata = {k:v for k,v in dataset.items() if k not in
                ('digest','e1_dataset_digest','e1_frozen_payload','selections','denominator','rows')}
    projected = bind(frozen,metadata,{r['observation_id']:r for r in dataset['denominator']})
    if projected != dataset:
        raise ValueError('E2_E1_BINDING_MUTATION')
    for key in ('dataset_id','feature_contract_id','target_contract_id','fold_id','partition_name',
                'e1_dataset_digest','selections','denominator','rows','target_kind','classes'):
        if key not in dataset:
            raise ValueError('E2_INPUT_BINDING_MISSING')
    expected = dataset['denominator']
    if len({r['observation_id'] for r in expected}) != len(expected):
        raise ValueError('E2_DUPLICATE_DENOMINATOR')
    if len({identity(r) for r in expected}) != 1:
        raise ValueError('E2_CROSS_BASE')
    if any(r['observation_scope'] != 'FEP_STOCK_ENTRY_CORE' for r in expected):
        raise ValueError('E2_SCOPE_DISABLED')
    lookup = {r['observation_id']:r for r in expected}
    selected = {s['observation_id']:s for s in dataset['selections']}
    if set(selected) != set(lookup):
        raise ValueError('E2_INCOMPLETE_SELECTIONS')
    eligible = {k for k,s in selected.items() if s['eligibility'] == 'ELIGIBLE'}
    if {r['observation_id'] for r in dataset['rows']} != eligible or len(dataset['rows']) != len(eligible):
        raise ValueError('E2_ELIGIBILITY_MUTATION')
    for row in dataset['rows']:
        key = row['observation_id']
        if row != lookup[key] or row['status'] != 'ELIGIBLE':
            raise ValueError('E2_ROW_MUTATION')
        s = selected[key]
        if row['selected_label_revision'] != s['selected_label_revision'] or row['selected_label_digest'] != s['selected_label_digest']:
            raise ValueError('E2_REVISION_MUTATION')


def baseline(dataset, query, policy, contract, created_at):
    validate_input(dataset)
    applicability = dict({k:query[k] for k in BASE}, target_kind=dataset['target_kind'])
    # Historical R1 UNSET input remains readable but can never support a bucket.
    historical_unset = policy.get('status') == 'UNSET_DIAGNOSTIC_ONLY' and all(
        v == 'UNSET' for v in policy['values'].values())
    if not historical_unset and policy.get('applicability') != applicability:
        raise ValueError('E2_POLICY_APPLICABILITY_MISMATCH')
    if instant(created_at) <= instant(policy['freeze_before_statistics_at']):
        raise ValueError('E2_POLICY_NOT_FROZEN_BEFORE_STATISTICS')
    if contract['levels'] != [[n,list(keys)] for n,keys in LEVELS]:
        raise ValueError('E2_BACKOFF_CONTRACT')
    if (contract['contract_id'],contract['weighting'],contract['quantile']) != (
            'CONDITIONAL_EXPECTANCY_V1','BUCKET_EQUAL_DATE_RATIONAL_V1','INVERSE_EMPIRICAL_CDF_V1'):
        raise ValueError('E2_METHOD_CONTRACT')
    if any(r[k] != query[k] for r in dataset['denominator'] for k in
           ('entity_type','observation_scope','signal_type','target','horizon','feature_variant',
            'evidence_origin','label_quality_policy','contract_versions')):
        raise ValueError('E2_CROSS_BASE_QUERY')
    trace = []
    for level,keys in LEVELS:
        expected = [r for r in dataset['denominator'] if all(r[k] == query[k] for k in keys)]
        rows = [r for r in dataset['rows'] if all(r[k] == query[k] for k in keys)]
        state,counts,diagnostic = gate(rows,expected,policy)
        if any(policy.get('representation_dimensions', {}).get(k) == 'UNAVAILABLE_NOT_GATED' for k in keys):
            state = 'NOT_EVALUABLE_CONDITION_UNAVAILABLE'
        trace.append(dict(level=level,state=state,counts=counts,diagnostic=diagnostic))
        if state == 'SUPPORTED':
            break
    stats, weight_digest = statistics(rows,dataset['target_kind'],dataset['classes'])
    result = dict(artifact_type='CONDITIONAL_STATISTICS_BASELINE', contract_id=contract['contract_id'],
                  contract_digest=digest(contract), dataset_id=dataset['dataset_id'], dataset_digest=dataset['digest'],
                  e1_dataset_digest=dataset['e1_dataset_digest'], feature_contract_id=dataset['feature_contract_id'],
                  target_contract_id=dataset['target_contract_id'], fold_id=dataset['fold_id'],
                  partition_name=dataset['partition_name'], label_revision_selections=dataset['selections'],
                  complete_denominator_digest=digest(dataset['denominator']), scope='FEP_STOCK_ENTRY_CORE',
                  base_identity=identity(query), base_partition={k:query[k] for k in BASE},
                  support_policy_id=policy['policy_id'], support_policy_digest=digest(policy),
                  selected_level=level if state == 'SUPPORTED' else None, condition_tuple={k:query[k] for k in keys},
                  support_state=state, counts=counts, statistics=stats, weight_digest=weight_digest,
                  denominator_summary=diagnostic, backoff_trace=trace, diagnostic_only=state != 'SUPPORTED',
                  full_population_claim=False, production=False, MODEL_DISPLAY='UNGRANTED', PRIORITY_USE='UNGRANTED')
    result['logical_digest'] = digest(result)
    result['artifact_id'] = 'FEP_E2:'+result['logical_digest']
    result['created_at'] = created_at
    return result
