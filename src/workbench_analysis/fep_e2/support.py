"""Outcome-performance-free support inventories and fail-closed policy gates."""
from collections import Counter
from workbench_analysis.fep_e1.contracts import digest

DIMENSIONS = ('rows', 'dates', 'blocks', 'entities', 'episodes')
BASE = ('entity_type', 'observation_scope', 'signal_type', 'target', 'horizon',
        'feature_variant', 'evidence_origin', 'label_quality_policy', 'contract_versions')
REPRESENTATION = ('trade_date', 'sector', 'regime', 'risk', 'feature_support')


def identity(row):
    return digest({k: row[k] for k in BASE})


def inventory(rows):
    """Intervals use frozen E1 calendar ordinals, never calendar-day arithmetic."""
    intervals = sorted({(r['date_ordinal'], r['label_end_ordinal']) for r in rows})
    end = -1
    blocks = 0
    for start, stop in sorted(intervals, key=lambda x: (x[1], x[0])):
        if stop < start:
            raise ValueError('E2_INVALID_INTERVAL')
        if start > end:
            blocks += 1
            end = stop
    episodes = 0
    for entity in sorted({r['entity_id'] for r in rows}):
        end = -1
        for start, stop in sorted({(r['episode_start'], r['episode_end']) for r in rows
                                  if r['entity_id'] == entity}):
            if stop < start:
                raise ValueError('E2_INVALID_EPISODE')
            if start > end:
                episodes += 1
            end = max(end, stop)
    return dict(rows=len(rows), dates=len({r['trade_date'] for r in rows}), blocks=blocks,
                entities=len({r['entity_id'] for r in rows}), episodes=episodes)


def diagnostics(expected, observed):
    counts = dict(sorted(Counter(r['status'] for r in expected).items()))
    tv = {}
    for key in REPRESENTATION:
        # Sector absence is explicit, not inferred from current membership.
        a = Counter(str(r.get(key, 'UNAVAILABLE')) for r in expected)
        b = Counter(str(r.get(key, 'UNAVAILABLE')) for r in observed)
        tv[key] = (sum(abs(a[k]/len(expected)-b[k]/len(observed))
                       for k in a.keys() | b.keys())/2 if expected and observed else None)
    return dict(expected=len(expected), eligible=len(observed), statuses=counts,
                missing_fraction=1-len(observed)/len(expected) if expected else None,
                representativeness_total_variation=tv, estimand='COMPLETE_CASE_DESCRIPTIVE')


def discover(expected, rows):
    """No numeric outcomes, empirical rates, quantiles, or level search consumed."""
    return dict(dependence=inventory(rows), coverage=diagnostics(expected, rows),
                class_counts=dict(sorted(Counter(r['support_class'] for r in rows).items())),
                input_digest=digest([ {k:v for k,v in r.items() if k not in ('outcome', 'weight')}
                                      for r in expected]),
                excluded=['outcome', 'mean', 'positive_rate', 'quantile', 'best_backoff', 'Priority'])


def gate(rows, expected, policy):
    counts = inventory(rows)
    diagnostic = diagnostics(expected, rows)
    values = policy['values']
    if any(values.get(k) in (None, 'UNSET') for k in
           (*DIMENSIONS, 'class_min', 'max_missing_fraction', 'max_total_variation')):
        return 'NOT_EVALUABLE', counts, diagnostic
    if any(type(values[k]) is not int or values[k] < 1 for k in (*DIMENSIONS,'class_min')) or any(
            not isinstance(values[k], (int,float)) or not 0 <= values[k] <= 1
            for k in ('max_missing_fraction','max_total_variation')):
        raise ValueError('E2_POLICY_RANGE')
    for key in DIMENSIONS:
        if counts[key] < values[key]:
            return 'THIN_'+key.upper(), counts, diagnostic
    classes = Counter(r['support_class'] for r in rows)
    if any(classes[c] < values['class_min'] for c in policy['required_classes']):
        return 'THIN_CLASS', counts, diagnostic
    if diagnostic['missing_fraction'] is None or diagnostic['missing_fraction'] > values['max_missing_fraction']:
        return 'MISSINGNESS_FAIL', counts, diagnostic
    if any(v is None or v > values['max_total_variation']
           for v in diagnostic['representativeness_total_variation'].values()):
        return 'REPRESENTATIVENESS_FAIL', counts, diagnostic
    return 'SUPPORTED', counts, diagnostic
