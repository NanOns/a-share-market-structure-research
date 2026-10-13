"""Independent Core availability from dated bars and frozen status evidence."""
import gzip
import hashlib
import json
import math
import os
from collections import Counter
from pathlib import Path

ROOT = Path('G:/codex work/v4-production-20261012')
WORK = Path('G:/codex_tmp/v4_full_closeout_20261012')
OUT = Path(__file__).resolve().parents[1] / 'docs/audits/v4_full_closeout_20261012/continuation_20261013/CORE_AVAILABILITY_ORACLE_R1'


def load(path):
    return json.loads(path.read_bytes())


def rows(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            yield json.loads(line)


def inputs():
    prep = load(WORK / 'SEALED_METADATA_CONSERVATION_R6_R3.json')
    candidate = load(ROOT / prep['candidate']['path'])
    day = candidate['accepted_trade_date']
    receipt = load(ROOT / candidate['day_receipt']['path'])
    replay = load(ROOT / receipt['numeric_core_oracle']['path'])
    owner = next(row for row in replay['owners'] if row['trade_date'] == day)
    calendar = load(ROOT / 'docs/evidence/r4_3_four_session_closeout_20261009/owner_v3/FOCUS_CALENDAR.json')['session_dates']
    dates = [date for date in calendar if date <= day]
    histories, missing = {}, set()
    for row in rows(ROOT / owner['history']['path']):
        # A 70-actual-bar ledger covers every Core technical window. Preserve
        # the first observed date separately for fixed-session shortage rules.
        bars = row['bars']
        retained = bars[-80:]
        by_date = {bar['trade_date']: bar for bar in retained}
        ledger_dates = [date for date in dates if retained[0]['trade_date'] <= date]
        histories[row['security_id']] = (bars[0]['trade_date'], by_date, ledger_dates)
        missing.update((row['security_id'], date) for date in ledger_dates if date not in by_date)
    status_receipt = load(WORK / 'PROFILE_WINDOW_COMPLETENESS_ORACLE_R6_R1.json')
    status_refs = status_receipt['status_sources']
    suspended = set()
    for row in rows(ROOT / status_refs[1]['path']):
        key = (row['security_id'], row['trade_date'])
        if key in missing and row['status'] == 'SUSPENDED':
            suspended.add(key)
    identity = load(ROOT / owner['sources']['identity']['path'])['rows']
    ids = {row['source_security_key'].lower(): row['security_id'] for row in identity}
    for binding in status_refs[2:]:
        query = load(ROOT / binding['path'])
        for row in query.get('rows', []):
            sid = ids.get(row['code'].lower())
            key = (sid, row.get('date', query.get('params', {}).get('date', query.get('params', {}).get('day'))))
            if key in missing:
                if row.get('tradestatus') == '0': suspended.add(key)
                else: suspended.discard(key)
    print('INDEPENDENT_CORE_STATUS_LEDGER_READY', flush=True)
    return prep, candidate, day, owner, dates, histories, suspended, status_refs


def main():
    target = OUT / 'RESULT.json'
    if target.exists():
        raise ValueError('PRESERVE_CORE_AVAILABILITY_ORACLE')
    prep, candidate, day, owner, dates, histories, suspended, status_refs = inputs()
    counts, reasons, errors = Counter(), Counter(), []
    error_count = 0
    for row in rows(ROOT / owner['core']['path']):
        sid, fields = row['security_id'], row['fields']
        first, bars, ledger = histories[sid]
        def state(date):
            bar = bars.get(date)
            return 'ACTUAL' if bar and bar['qfq_ohlc'] else 'ADJUSTMENT_UNKNOWN' if bar else 'CONFIRMED_SUSPENSION' if (sid, date) in suspended else 'UNKNOWN'
        def valid(selected):
            if any(state(date) != 'ACTUAL' for date in selected): return 'MISSING_OR_SUSPENDED_ENDPOINT'
            for date in selected:
                bar = bars[date]
                values = [*bar['qfq_ohlc'], bar['amount'], bar['volume']]
                if not all(math.isfinite(v) for v in values): return 'NONFINITE_INPUT'
                o, h, l, c = bar['qfq_ohlc']
                if min(o, h, l, c) <= 0 or h < l: return 'INVALID_PRICE'
            return None
        def technical(n, prior=False):
            available = ledger[:-1] if prior else ledger
            if not available: return [], 'INSUFFICIENT_HISTORY'
            if not prior and state(available[-1]) in ('UNKNOWN', 'ADJUSTMENT_UNKNOWN'):
                return [available[-1]], 'ADJUSTMENT_UNKNOWN' if state(available[-1]) == 'ADJUSTMENT_UNKNOWN' else 'CURRENT_BAR_UNAVAILABLE'
            selected = []
            for date in reversed(available):
                st = state(date)
                if st in ('UNKNOWN', 'ADJUSTMENT_UNKNOWN'):
                    return [], 'ADJUSTMENT_UNKNOWN' if st == 'ADJUSTMENT_UNKNOWN' else 'UNEXPLAINED_DATA_GAP'
                if st == 'ACTUAL':
                    selected.append(date)
                    if len(selected) == n:
                        return list(reversed(selected)), valid(selected)
            return selected, 'INSUFFICIENT_HISTORY'
        def endpoint_error():
            return 'ADJUSTMENT_UNKNOWN' if state(day) == 'ADJUSTMENT_UNKNOWN' else 'CURRENT_BAR_UNAVAILABLE' if state(day) != 'ACTUAL' else valid([day])
        expected = {}
        for n in (5, 20, 60):
            _, expected['ma'+str(n)] = technical(n)
            expected['hhv'+str(n)] = expected['llv'+str(n)] = expected['ma'+str(n)]
            _, expected['prior_high'+str(n)] = technical(n, True)
            expected['prior_low'+str(n)] = expected['prior_high'+str(n)]
        for n in (5, 20):
            selected, reason = technical(n, True)
            reason = reason or endpoint_error()
            for source in ('amount', 'volume'):
                expected[source+'_ratio'+str(n)] = reason or ('ZERO_DENOMINATOR' if sum(bars[date][source] for date in selected) == 0 else None)
        for n in (1, 3, 5, 20):
            session_dates = dates[-n-1:]
            if len([d for d in dates if first <= d]) < n+1:
                reason = 'INSUFFICIENT_SESSION_HISTORY'
            elif state(session_dates[0]) != 'ACTUAL' or state(day) != 'ACTUAL':
                reason = 'ADJUSTMENT_UNKNOWN' if any(state(d) == 'ADJUSTMENT_UNKNOWN' for d in (session_dates[0], day)) else 'MISSING_OR_SUSPENDED_ENDPOINT'
            elif any(state(d) in ('UNKNOWN', 'ADJUSTMENT_UNKNOWN') for d in session_dates):
                reason = 'ADJUSTMENT_UNKNOWN' if any(state(d) == 'ADJUSTMENT_UNKNOWN' for d in session_dates) else 'UNEXPLAINED_DATA_GAP'
            else: reason = valid([session_dates[0], day])
            expected['ret'+str(n)] = reason
            if n in (5, 20): expected['vol'+str(n)] = reason or valid(session_dates)
        _, expected['tr'] = technical(2)
        expected['tr'] = expected['tr'] or endpoint_error()
        for n in (5, 20): _, expected['atr'+str(n)] = technical(n+1)
        for n, size in ((20, 25), (60, 70)):
            _, reason = technical(size)
            expected['slope'+str(n)] = reason or expected['atr20'] or ('ZERO_ATR' if fields['atr20']['value'] <= 0 else None)
        _, expected['hh_progress'] = technical(10)
        expected['ll_progress'] = expected['hh_progress']
        _, reason = technical(1)
        reason = reason or endpoint_error()
        expected['clv'] = reason or ('ZERO_DENOMINATOR' if bars[day]['qfq_ohlc'][1] == bars[day]['qfq_ohlc'][2] else None)
        _, reason = technical(60, True)
        expected['prior60_percentile'] = reason or valid([day])
        dependencies = {'pos60':['llv60','hhv60','llv60','hhv60'], 'range_ratio':['hhv5','hhv20','llv5','llv20'], 'atr_ratio':['atr5','atr20'], 'vol_ratio':['vol5','vol20'], 'core_price_damage':['prior_low20','atr20','ret1']}
        for name, deps in dependencies.items():
            reason = next((expected[k] for k in deps if expected[k]), None)
            if reason is None and name == 'pos60':
                reason = endpoint_error() or ('ZERO_DENOMINATOR' if fields['hhv60']['value'] == fields['llv60']['value'] else None)
            elif reason is None and name == 'range_ratio':
                reason = 'ZERO_DENOMINATOR' if fields['hhv20']['value'] == fields['llv20']['value'] else None
            elif reason is None and name in ('atr_ratio', 'vol_ratio'):
                reason = 'ZERO_DENOMINATOR' if fields[deps[1]]['value'] <= 0 else None
            expected[name] = reason
        for name, reason in expected.items():
            cell = fields[name]
            reasons[name, reason or 'OBSERVED'] += 1
            wanted = dict(quality_state='UNKNOWN' if reason else 'OBSERVED', unknown_reason=reason, value_available=reason is None)
            actual = dict(quality_state=cell['quality_state'], unknown_reason=cell['unknown_reason'], value_available=cell['value'] is not None)
            for key in wanted:
                counts[key] += 1
                if actual[key] != wanted[key]:
                    error_count += 1
                    if len(errors) < 100: errors.append(dict(security_id=sid, field=name, key=key, actual=actual[key], expected=wanted[key]))
    report = dict(contract_id='V4_CORE_CURRENT_ALL_FIELD_AVAILABILITY_INDEPENDENT_ORACLE_R1', acceptance='PASS_CORE_AVAILABILITY_SCOPE' if not error_count else 'FAIL', candidate=prep['candidate'], T0=day, core=owner['core'], history=owner['history'], status_sources=status_refs,
        normative_window_contract='config/v4_03_field_window_mapping_v1.json', checks=dict(counts), check_count=sum(counts.values()), error_count=error_count, first_errors=errors,
        reason_counts=[dict(field=k[0], reason=k[1], count=v) for k,v in sorted(reasons.items())], known_numerical_arithmetic_reexecuted=False, primary_core_module_imported=False, publication_ready=False,
        scope='All 39 primitive/derived Core field availability and UNKNOWN reasons from dated actual bars and frozen suspension queries. RPS and relative-reference gates are separately conserved. Window digest metadata and arithmetic are separate evidence.')
    OUT.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, indent=2), encoding='utf-8')
    os.replace(temporary, target)
    print(json.dumps(dict(acceptance=report['acceptance'], checks=report['check_count'], errors=error_count)))
    return bool(error_count)


if __name__ == '__main__':
    raise SystemExit(main())
