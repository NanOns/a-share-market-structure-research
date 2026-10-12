"""Independent rational/path, lifecycle and settlement review of paused Focus.

Reads existing PG Series and immutable D2; never reruns five-day Core math.
Does not import the Focus projection, classification or adjustment builders.
"""
import csv
import gzip
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction as F
from pathlib import Path

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
WORK = Path('G:/codex_tmp/r4_r3_pg_publication_v2')
OUT = ROOT / 'docs/audits/r4_r3_local_delivery_20261012/S1_ORACLE'


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def checked(binding):
    path = (WORK / binding['path']).resolve()
    assert path.is_relative_to(WORK.resolve())
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == binding['sha256']
    return raw


def load(binding):
    raw = checked(binding)
    return json.loads(gzip.decompress(raw) if binding['path'].endswith('.gz') else raw)


def main():
    global OUT
    receipt_path = ROOT / 'docs/audits/r4_r3_consumers_20261011/FOCUS_RESUME_R1/RESULT.json'
    if len(sys.argv) > 1:
        receipt_path = Path(sys.argv[1]).resolve()
        assert receipt_path.is_relative_to(ROOT / 'docs/audits/r4_r3_local_delivery_20261012')
        OUT = OUT.with_name('S1_ORACLE_REPAIRED')
    if len(sys.argv) > 2:
        assert sys.argv[2] == 'FULL'
        OUT = OUT.with_name('S1_ORACLE_FULL')
    OUT.mkdir(parents=True, exist_ok=False)
    receipt = json.loads(receipt_path.read_bytes())
    projection = load(receipt['result']['focus'])
    bindings = projection['source_bindings']
    calendar = load(bindings['calendar'])['session_dates']
    days = {owner['trade_date']: {r['entity_id']: r for r in load(owner['D2'])['rows']} for owner in receipt['result']['owners']}
    status = {d: {r['security_id']: r for r in load(b)['rows']} for d, b in bindings['status'].items()}
    descriptor = load(bindings['series'])
    symbols = None
    if bindings.get('security_identity'):
        identity_rows = load(bindings['security_identity'])['rows']
        symbols = {r['security_id']: r['source_security_key'] for r in identity_rows}
        assert len(symbols) == len(identity_rows) and len(set(symbols.values())) == len(symbols)
    bars = defaultdict(dict)
    with psycopg.connect(host='127.0.0.1', port=55791, user='r4_isolated_admin', dbname='postgres', options='-c default_transaction_read_only=on') as pg:
        pg.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        assert pg.execute('select system_identifier::text from pg_control_system()').fetchone()[0] == '7695278778933357404'
        for sid, day, payload in pg.execute(sql.SQL('SELECT security,day::text,payload FROM {}.bars ORDER BY security,day').format(sql.Identifier(descriptor['schema']))):
            bars[sid][day] = json.loads(payload)
            if symbols is not None:
                assert bars[sid][day]['symbol'] == symbols[sid], 'INDEPENDENT_SOURCE_IDENTITY_MISMATCH'
    # The already audited binary parser is reused only to decode source records.
    from tdx.gbbq_reader import read_gbbq
    checked(bindings['gbbq'])
    actions = defaultdict(list)
    for event in read_gbbq(WORK / bindings['gbbq']['path']):
        actions[event.security_id].append(event)
    dispositions = load(bindings['classification'])['dispositions']
    failures, gaps, seen = [], [], set()
    comparisons = action_paths = lifecycle_checks = settlement_checks = priority_checks = 0

    def equal(actual, expected, scope):
        if actual != expected:
            failures.append(dict(scope=scope, actual=actual, expected=expected))

    native = {}
    if len(sys.argv) > 2:
        for day, owner in bindings['native_core'].items():
            native[day] = {}
            for kind in ('factors', 'profiles'):
                raw = checked(owner[kind])
                for line in gzip.decompress(raw).splitlines():
                    row = json.loads(line)
                    assert row['trade_date'] == day
                    values = native[day].setdefault(row['security_id'], {})
                    cells = row['fields'] if kind == 'factors' else row['states']
                    for name in (('ma20', 'ret5') if kind == 'factors' else ('severe_extension',)):
                        cell = cells[name]
                        values[name] = cell['value'] if not cell.get('unknown_reason') else None

    def truth(value):
        return 'UNKNOWN' if value is None else 'TRUE' if value else 'FALSE'

    def conjunction(*values):
        return 'FALSE' if 'FALSE' in values else 'UNKNOWN' if 'UNKNOWN' in values else 'TRUE'

    def disjunction(*values):
        return 'TRUE' if 'TRUE' in values else 'UNKNOWN' if 'UNKNOWN' in values else 'FALSE'

    predicate_checks = 0

    for episode in projection['episodes']:
        sid, start = episode['entity_id'], episode['start_date']
        equal(episode['episode_id'], identity(['FP08_V4_FOCUS_LIFECYCLE_V1', sid, start]), ['episode_identity', sid, start])
        equal([o['trade_date'] for o in episode['observations']], [d for d in sorted(days) if d >= start], ['observation_calendar', sid, start])
        for obs in episode['observations']:
            day = obs['trade_date']
            evidence = obs['predicate_evidence']
            if native and obs['price_path']['quality'] == 'READY':
                source_row = days[day].get(sid, {})
                source_native = native[day].get(sid, {})
                native_bound = sid in native[day] and day in bars[sid]
                facts = dict(ma20=source_native.get('ma20'), r5=source_native.get('ret5'), source_extended=source_native.get('severe_extension')) if native_bound else {}
                equal(obs['native_core_evidence']['facts'], facts, ['native_input_binding', sid, day])
                value = lambda key: Decimal(str(facts[key])) if facts.get(key) is not None else None
                close = Decimal(obs['price_path']['close'])
                dd = Decimal(obs['price_path']['metrics']['drawdown_current'])
                ma20, r5 = value('ma20'), value('r5')
                inv = {'INVALID': 'TRUE', 'VALID': 'FALSE'}.get(source_row.get('validity'), 'UNKNOWN')
                valid = {'INVALID': 'FALSE', 'VALID': 'TRUE'}.get(source_row.get('validity'), 'UNKNOWN')
                pullback = truth(Decimal('-.12') <= dd <= Decimal('-.03'))
                below = truth(close < ma20 if ma20 is not None else None)
                expected_evidence = dict(STRUCTURE_DAMAGED=inv,
                    TOO_EXTENDED=truth(facts.get('source_extended')),
                    PULLBACK_HEALTHY=conjunction(pullback, truth(close >= ma20 if ma20 is not None else None), 'UNKNOWN', valid),
                    PULLBACK_UNCONFIRMED=conjunction(pullback, disjunction(below, 'UNKNOWN'), valid),
                    BREAKOUT_CONFIRMED=source_row.get('raw_qualification', {}).get('CONFIRMED', 'UNKNOWN'),
                    TREND_ACCELERATING=conjunction('UNKNOWN', truth(r5 > 0 if r5 is not None else None), 'UNKNOWN', 'UNKNOWN'),
                    SECTOR_DIVERGENCE='UNKNOWN',
                    WEAKENING=conjunction(disjunction(below, 'UNKNOWN'), valid),
                    WAIT_CONFIRMATION=truth(obs.get('membership') == 'EARLY' and bool(source_row)),
                    EXITED_FOLLOW_UP=truth(episode['end_date'] is not None and day >= episode['end_date']))
                equal(evidence, expected_evidence, ['independent_full_predicates', sid, day])
                predicate_checks += len(expected_evidence)
            if evidence == {'actual_bar': 'UNKNOWN'}:
                equal(obs['path_resolution'], 'UNAVAILABLE', ['priority_no_bar', sid, day])
                equal(obs['path_state'], None, ['priority_no_bar_state', sid, day])
            else:
                order = ['STRUCTURE_DAMAGED', 'TOO_EXTENDED', 'PULLBACK_HEALTHY', 'PULLBACK_UNCONFIRMED', 'BREAKOUT_CONFIRMED', 'TREND_ACCELERATING', 'SECTOR_DIVERGENCE', 'WEAKENING', 'WAIT_CONFIRMATION', 'EXITED_FOLLOW_UP']
                unknown, best = [], None
                for name in order:
                    if evidence[name] == 'TRUE':
                        best = name
                        break
                    if evidence[name] == 'UNKNOWN':
                        unknown.append(name)
                resolution = ('PARTIAL' if unknown else 'READY') if best else ('UNAVAILABLE' if unknown else 'READY')
                equal([obs['path_resolution'], obs['best_confirmed_state'], obs['path_state'], obs['higher_priority_unresolved']], [resolution, best, best if resolution == 'READY' else None, unknown], ['priority', sid, day])
            priority_checks += 1
            equal(obs['PIT_ELIGIBLE'], False, ['PIT', sid, day])
            equal(obs['AS_RECORDED'], False, ['AS_RECORDED', sid, day])
            key = sid, start, day
            if key in seen:
                continue
            seen.add(key)
            fact = obs['price_path']
            sessions = [d for d in calendar if start <= d <= day]
            missing, suspended = [], []
            for d in sessions:
                st = status.get(d, {}).get(sid, {})
                if d in bars[sid]:
                    if st.get('status_conflict') or st.get('actual_bar_present') is False:
                        missing.append(d)
                elif st.get('status') == 'SUSPENDED' and st.get('actual_bar_present') is False and not st.get('status_conflict'):
                    suspended.append(d)
                else:
                    missing.append(d)
            equal(fact['missing_dates'], missing, ['missing', *key])
            equal(fact['suspended_dates'], suspended, ['suspended', *key])
            equal(fact['anchor_actual_bar'], start in bars[sid], ['anchor', *key])
            target = 'BAR' if day in bars[sid] else 'SUSPENDED' if day in suspended else None
            equal(fact['target_state'], target, ['target', *key])
            ordered = [(d, r) for d, r in sorted(bars[sid].items()) if start <= d <= day]
            relevant = [e for e in actions.get(ordered[-1][1]['symbol'], []) if int(start.replace('-', '')) < e.event_date <= int(day.replace('-', ''))] if ordered else []
            blocked = any(dispositions.get(str(e.category), {}).get('formal_disposition', 'UNKNOWN_PRICE_IMPACT') in ('PRICE_AFFECTING_UNSUPPORTED', 'UNKNOWN_PRICE_IMPACT') for e in relevant)
            ready = not missing and start in bars[sid] and day in bars[sid] and not blocked
            equal(fact['quality'], 'READY' if ready else 'DATA_UNAVAILABLE', ['quality', *key])
            if not ready:
                equal(fact['metrics'], None, ['unknown_metrics', *key])
                gaps.append(dict(security=sid, start=start, end=day, missing=missing, suspended=suspended, target=target, blocked_action=blocked, source_status={d: status.get(d, {}).get(sid) for d in sessions}, acceptance='UNKNOWN_PRESERVED_NO_FILL'))
                continue
            action_paths += bool(relevant)
            values = []
            for d, row in ordered:
                vector = [F(str(x)) for x in row['raw_ohlc']]
                for e in sorted((e for e in relevant if e.category == 1 and e.event_date > int(d.replace('-', ''))), key=lambda e: (e.event_date, e.source_record_index)):
                    cash, price, bonus, rights = [F(Decimal(str(x)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)) for x in (e.c1, e.c2, e.c3, e.c4)]
                    vector = [(v - (cash - rights * price) / 10) / ((10 + bonus + rights) / 10) for v in vector]
                # Round exact rational values only once after all actions.
                vector = [F((2 * (v * 100).numerator + (v * 100).denominator) // (2 * (v * 100).denominator), 100) for v in vector]
                values.append(vector)
            closes = [v[3] for v in values]
            peak, worst = closes[0], F(0)
            for close in closes:
                peak = max(peak, close)
                worst = min(worst, close / peak - 1)
            metrics = dict(return_close=closes[-1] / closes[0] - 1, mfe=max(v[1] for v in values) / closes[0] - 1, mae=min(v[2] for v in values) / closes[0] - 1, peak_close=max(closes), drawdown_current=closes[-1] / max(closes) - 1, mdd_close=worst)
            for name, expected in metrics.items():
                actual = F(Decimal(fact['metrics'][name]))
                comparisons += 1
                if abs(actual - expected) > F(1, 10**24):
                    failures.append(dict(scope=['numeric', *key, name], expected=str(expected), actual=str(actual)))
        for outcome in episode['outcomes']:
            anchor = next(a for a in episode['anchors'] if a['anchor_id'] == outcome['anchor_id'])
            pos = calendar.index(anchor['trade_date']) + outcome['horizon']
            target = calendar[pos] if pos < len(calendar) else None
            equal(outcome['target_trade_date'], target if target and target <= max(days) else None, ['settlement_target', sid, outcome['anchor_id'], outcome['horizon']])
            expected = 'PENDING'
            if target in days:
                # Outcome paths start at each anchor, not necessarily episode genesis.
                # Existing observed facts must bind complete actual target prices.
                sessions = [d for d in calendar if anchor['trade_date'] <= d <= target]
                usable = all(d in bars[sid] or (status.get(d, {}).get(sid, {}).get('status') == 'SUSPENDED' and status[d][sid].get('actual_bar_present') is False and not status[d][sid].get('status_conflict')) for d in sessions)
                if target not in bars[sid] and status.get(target, {}).get(sid, {}).get('status') == 'SUSPENDED':
                    expected = 'SUSPENDED'
                elif usable and anchor['trade_date'] in bars[sid] and target in bars[sid]:
                    expected = 'OBSERVED'
            equal(outcome['outcome_status'], expected, ['settlement_status', sid, outcome['anchor_id'], outcome['horizon']])
            equal(outcome['terminal'], expected in ('OBSERVED', 'SUSPENDED', 'DELISTED', 'DATA_GAP'), ['terminal', sid, outcome['anchor_id'], outcome['horizon']])
            equal(outcome['metrics'] is not None, expected == 'OBSERVED', ['settlement_metrics', sid, outcome['anchor_id'], outcome['horizon']])
            settlement_checks += 1
    # Independent membership state machine checks events against frozen D2 inputs.
    active, previous = {}, {}
    actual_events = {(e['entity_id'], e['trade_date']): e for e in projection['events']}
    for day, rows in sorted(days.items()):
        for sid, row in rows.items():
            q = row['raw_qualification']
            member = 'CURRENT' if q.get('CONFIRMED') == 'TRUE' else 'EARLY' if q.get('PREWATCH') == 'TRUE' else 'NONE' if q.get('CONFIRMED') == q.get('PREWATCH') == 'FALSE' else 'UNKNOWN'
            prior = active.get(sid)
            if prior is None and member not in ('EARLY', 'CURRENT'):
                continue
            eid = prior['id'] if prior else identity(['FP08_V4_FOCUS_LIFECYCLE_V1', sid, day])
            if prior is None:
                event = 'REENTERED' if sid in previous else 'NEW'
            else:
                event = 'DATA_UNAVAILABLE' if member == 'UNKNOWN' else 'EXITED' if member == 'NONE' else 'UPGRADED' if prior['member'] == 'EARLY' and member == 'CURRENT' else 'WEAKENED' if prior['member'] == 'CURRENT' and member == 'EARLY' else 'PERSISTENT'
                if row.get('validity') == 'INVALID':
                    event = 'INVALIDATED'
            actual = actual_events.get((sid, day), {})
            equal([actual.get('event'), actual.get('episode_id'), actual.get('membership')], [event, eid, member], ['lifecycle', sid, day])
            if member == 'NONE' or event == 'INVALIDATED':
                active.pop(sid, None)
            else:
                active[sid] = dict(id=eid, member=member if member != 'UNKNOWN' else prior['member'])
            previous[sid] = eid
            lifecycle_checks += 1
    result = dict(contract='R4_R3_FOCUS_FULL_CHECKPOINT_ORACLE_S1_V1', status='PASS_SCOPED' if not failures else 'FAIL', episodes=len(projection['episodes']), unique_observation_paths=len(seen), numerical_comparisons=comparisons, actual_company_action_paths=action_paths, unavailable_paths=len(gaps), lifecycle_checks=lifecycle_checks, priority_checks=priority_checks, predicate_input_formula_checks=predicate_checks, settlement_checks=settlement_checks, failures=failures, quality_counts=dict(Counter(o['price_path']['quality'] for e in projection['episodes'] for o in e['observations'])), source_projection=receipt['result']['focus'], limitations=['Full predicates are independently checked against bound Core/Profile values only when FULL mode is enabled.', 'Actual company-action count is reported; zero does not establish company-action coverage.', 'No historical PIT, external acceptance or production permission granted.'], production_changed=False)
    for name, value in [('RESULT.json', result), ('UNAVAILABLE_PATHS.json', gaps)]:
        temp = OUT / (name + '.tmp')
        temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
        os.replace(temp, OUT / name)
    print(json.dumps({k: result[k] for k in ('status', 'episodes', 'numerical_comparisons', 'actual_company_action_paths', 'unavailable_paths', 'lifecycle_checks', 'priority_checks', 'settlement_checks')}))
    print(json.dumps(failures[:8]))
    return 0 if not failures else 1


if __name__ == '__main__':
    raise SystemExit(main())
