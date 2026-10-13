"""Independent current market arithmetic; no producer imports or publication."""
import gzip
import hashlib
import json
import os
from pathlib import Path
from statistics import fmean, median

ROOT = Path('G:/codex work/v4-production-20261012')
AUDIT = Path(__file__).resolve().parents[1] / 'docs/audits/v4_full_closeout_20261012/continuation_20261013/CURRENT_MARKET_ORACLE_R1'
CANDIDATE = 'data/v4/sealed_numeric_preparations_v1/412bb713abc87cd16cf2cb0bff5653971dcd97909609b6a7c574c616f18ca858/CANDIDATE.json'


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            yield json.loads(line)


def main():
    result_path = AUDIT / 'RESULT.json'
    if result_path.exists():
        raise ValueError('PRESERVE_CURRENT_MARKET_ORACLE')
    candidate = load(ROOT / CANDIDATE)
    day = candidate['accepted_trade_date']
    market_ref = candidate['owners'][day]['market']
    market = load(ROOT / market_ref['path'])
    bindings = market['input_bindings']
    sources = []
    for binding in bindings:
        path = ROOT / binding['path']
        if path.stat().st_size != binding['bytes'] or sha(path) != binding['sha256']:
            raise ValueError('MARKET_INPUT_SOURCE_DRIFT:' + binding['path'])
        sources.append(binding)
    dates = load(ROOT / 'docs/evidence/r4_3_four_session_closeout_20261009/owner_v3/FOCUS_CALENDAR.json')['session_dates']
    pos = dates.index(day)
    previous, comparison = dates[pos-1], dates[pos-3]
    core = {r['security_id']: r for r in rows(ROOT / bindings[0]['path'])}
    member_dates = {comparison, *(r['start_trade_date'] for r in market['index_successor_bridge'])}
    members = {d: set() for d in member_dates}
    # Read the normative dated-universe input once; do not rebuild any Owner.
    for row in rows(ROOT / bindings[2]['path']):
        if row['trade_date'] in members:
            members[row['trade_date']].add(row['security_id'])
    for date, owner in candidate['owners'].items():
        if date in members:
            members[date] = {r['security_id'] for r in rows(ROOT / owner['core']['path'])}
    needed = member_dates | {day, previous, comparison, dates[dates.index(comparison)-1]}
    history = {}
    for row in rows(ROOT / bindings[1]['path']):
        history[row['security_id']] = {b['trade_date']: b for b in row['bars'] if b['trade_date'] in needed}
    print('BOUND_MARKET_INPUTS_READ', flush=True)
    def daily_return(sid, date):
        bars = history.get(sid, {})
        current = bars.get(date, {}).get('qfq_ohlc')
        prior = bars.get(dates[dates.index(date)-1], {}).get('qfq_ohlc')
        return current[3] / prior[3] - 1 if current and prior and prior[3] > 0 else None
    pairs = [(daily_return(s, day), daily_return(s, comparison)) for s in set(core) & members[comparison]]
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    breadth = fmean(int(a > 0) - int(b > 0) for a, b in pairs) if pairs else None
    participation_values = [r['fields']['amount_ratio20']['value'] for r in core.values() if r['fields']['amount_ratio20']['value'] is not None]
    participation = median(participation_values) if participation_values else None
    known = ('LIMIT_UP', 'LIMIT_DOWN', 'NOT_LIMIT')
    limits = {r['security_id']: r['limit_state'] for r in rows(ROOT / bindings[4]['path']) if r['limit_state'] in known}
    prior_limits = {r['security_id']: r['limit_state'] for r in rows(ROOT / bindings[5]['path']) if r['limit_state'] in known}
    common = set(limits) & set(prior_limits)
    coverage = len(limits) / len(core)
    stress = sum(v == 'LIMIT_DOWN' for v in limits.values()) / len(limits) if limits else None
    prior_stress = sum(prior_limits[s] == 'LIMIT_DOWN' for s in common) / len(common) if common else None
    same_stress = sum(limits[s] == 'LIMIT_DOWN' for s in common) / len(common) if common else None
    params = load(ROOT / 'config/v4_03_parameter_set_v1.json')['engineering_candidate_thresholds']
    errors, checks = [], []
    def check(name, actual, expected):
        checks.append(name)
        if actual != expected:
            errors.append(dict(field=name, actual=actual, expected=expected))
    check('comparison_trade_date', market['comparison_trade_date'], comparison)
    check('breadth_common_count', market['breadth_common_count'], len(set(core) & members[comparison]))
    check('breadth_evaluable', market['breadth_evaluable'], len(pairs))
    check('daily_limit_coverage', market['daily_limit_coverage'], coverage)
    check('daily_limit_known', market['daily_limit_known'], len(limits))
    check('stress_same_member_count', market['stress_same_member_count'], len(common))
    expected_axes = dict(
        breadth_axis=('IMPROVING' if breadth > params['market_breadth_axis'] else 'DETERIORATING' if breadth < -params['market_breadth_axis'] else 'STABLE') if breadth is not None else None,
        participation_axis=('EXPANDING' if participation >= params['market_participation_expanding'] else 'THIN' if participation < params['market_participation_thin'] else 'NORMAL') if participation is not None else None,
        stress_level=('HIGH' if stress >= params['market_stress_high'] else 'ELEVATED' if stress >= params['market_stress_elevated'] else 'LOW') if stress is not None and coverage >= params['market_stress_min_limit_coverage'] else None,
        stress_change=('RISING' if same_stress > prior_stress else 'DECLINING' if same_stress < prior_stress else 'STABLE') if same_stress is not None and prior_stress is not None else None)
    for name, expected in expected_axes.items():
        check(name, market['axes'][name], expected)
        check(name + '.quality', market['axes']['field_quality'][name]['quality_state'], 'OBSERVED' if expected is not None else 'UNKNOWN')
    prefix = [r for r in rows(ROOT / bindings[3]['path']) if r['trade_date'] <= day]
    levels = [r['level'] for r in prefix]
    level = levels[-1]
    bridge_policy = load(ROOT / 'config/v4_market_path_successor_contract_v1.json')
    for entry in market['index_successor_bridge']:
        returns = [daily_return(s, entry['trade_date']) for s in sorted(members[entry['start_trade_date']])]
        returns = [v for v in returns if v is not None]
        count = len(members[entry['start_trade_date']])
        fraction = len(returns) / count if count else 0
        change = fmean(returns) if returns and fraction >= bridge_policy['minimum_bridge_coverage'] else None
        level = level * (1 + change) if level is not None and change is not None else None
        levels.append(level)
        for name, expected in dict(start_members=count, evaluable=len(returns), coverage=fraction, level=level).items():
            check('bridge.' + entry['trade_date'] + '.' + name, entry[name], expected)
    def ma(values):
        return fmean(values) if len(values) == 20 and all(v is not None for v in values) else None
    current_ma, prior_ma = ma(levels[-20:]), ma(levels[-25:-5])
    trend = 'UNKNOWN' if any(v is None for v in (level, current_ma, prior_ma)) else 'STRONG' if level > current_ma > prior_ma else 'WEAK' if level < current_ma < prior_ma else 'NEUTRAL'
    check('trend_axis', market['trend']['trend_axis'], trend)
    check('trend.quality', market['trend']['quality_state'], 'UNKNOWN' if trend == 'UNKNOWN' else 'OBSERVED')
    check('trend.unknown_reason', market['trend']['unknown_reason'], 'REQUIRED_TREND_INPUT_UNKNOWN' if trend == 'UNKNOWN' else None)
    report = dict(contract_id='V4_CURRENT_MARKET_BOUND_INPUT_INDEPENDENT_ORACLE_R1', acceptance='PASS_CURRENT_MARKET_ARITHMETIC_SCOPE' if not errors else 'FAIL', T0=day,
        candidate=dict(path=CANDIDATE, sha256=sha(ROOT/CANDIDATE), bytes=(ROOT/CANDIDATE).stat().st_size), market=market_ref,
        sources=sources, check_count=len(checks), checked_fields=checks, error_count=len(errors), errors=errors,
        primitives=dict(breadth=breadth, participation=participation, coverage=coverage, stress=stress, prior_stress=prior_stress, same_member_stress=same_stress, index_close=level, index_ma20=current_ma, index_ma20_t_minus_5=prior_ma),
        scope='Current market arithmetic and exact dated index bridge from bound Core/history/member/limit inputs; no producing module imported.',
        limitations=['Saved prior regime inputs and market source digest provenance require separate acceptance; this receipt does not grant full numeric or release admission.'], publication_ready=False, producer_reexecuted=False)
    AUDIT.mkdir(parents=True, exist_ok=True)
    temporary = result_path.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, indent=2), encoding='utf-8')
    os.replace(temporary, result_path)
    print(json.dumps(dict(acceptance=report['acceptance'], checks=len(checks), errors=len(errors))))
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
