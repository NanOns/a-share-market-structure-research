"""Independent arithmetic from exact accepted rows; calculation payload is evidence only."""
from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
import gzip
import json
import math
from pathlib import Path
from statistics import median, pstdev
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from scripts.next_round_bundle_r1 import bind, exact, read, write
from src.v4.confirmation import digest

DATA = 'data/v4/confirmation_candidates_r3/'
REPORT = 'reports/v4_11_r3a/INDEPENDENT_ORACLE.json'


def positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def arithmetic(window, liquidity_floor=20_000_000):
    """An independently expressed scalar oracle, never the tested factor function."""
    def segment(length, offset=0, fields=('close',), raw=False):
        end = len(window) - offset
        rows = window[end-length:end] if end >= length else []
        flag = 'raw_actual_bar' if raw else 'has_actual_bar'
        if len(rows) != length or any(r.get(flag) is not True or r.get('is_synthetic_fill') is True for r in rows):
            return None
        if any(not positive(r.get(('raw_' + field) if raw and field in ('open', 'high', 'low', 'close') else field)) for r in rows for field in fields):
            return None
        return rows
    def average(rows, field='close'):
        # Exact binary-float rational sum, rounded once: the accepted factor's
        # statistics.mean operation, independently expressed without that function.
        return float(sum((Fraction.from_float(float(r[field])) for r in rows), Fraction()) / len(rows)) if rows else None
    def ratio(left, right):
        return left / right if left is not None and right is not None and right > 0 else None
    target = segment(1, fields=('open', 'high', 'low', 'close', 'raw_open', 'raw_close', 'amount', 'volume'))
    raw_target = segment(1, fields=('open', 'high', 'low', 'close', 'raw_open', 'raw_close', 'amount', 'volume'), raw=True)
    prior = segment(20, 1, fields=('close', 'high', 'amount', 'volume'))
    raw_prior = segment(20, 1, fields=('close', 'high', 'amount', 'volume'), raw=True)
    c = target[0]['close'] if target else None
    h = target[0]['high'] if target else None
    low = target[0]['low'] if target else None
    ma5, ma20 = average(segment(5)), average(segment(20))
    pc = window[-2].get('close') if len(window) >= 2 and window[-2].get('has_actual_bar') is True and positive(window[-2].get('close')) else None
    ratio1 = ratio(c, pc)
    ret1 = ratio1 - 1 if ratio1 is not None else None
    amount_mean = average(raw_prior, 'amount')
    amount_median = median(r['amount'] for r in raw_prior) if raw_prior else None
    amr = ratio(raw_target[0]['amount'] if raw_target else None, amount_mean)
    phc = max(r['close'] for r in prior) if prior else None
    phh = max(r['high'] for r in prior) if prior else None
    clv = (c-low)/(h-low) if c is not None and h is not None and low is not None and h > low else None
    series = segment(20)
    slope = None
    if series:
        y = [math.log(r['close']) for r in series]
        slope = sum((i - 9.5) * y[i] for i in range(20)) / 665.0
    prior_sigma = segment(21, 1)
    sigma = None
    if prior_sigma:
        sigma = pstdev(math.log(b['close']/a['close']) for a, b in zip(prior_sigma, prior_sigma[1:]))
    absolute = ret1 <= -.08 if ret1 is not None else None
    relative = math.log(c/pc) <= -max(-math.log(.96), 2*sigma) if c is not None and pc is not None and sigma is not None else None
    severe = True if absolute is True or relative is True else None if absolute is None or relative is None else False
    prior5, prior20 = average(segment(5, 1)), average(segment(20, 1))
    count = []
    for offset in range(5, 0, -1):
        seq = segment(20, offset)
        # The frozen P12-03 projection explicitly uses left-to-right sum/N,
        # unlike calculate_today_facts' statistics.mean. Preserve both scopes.
        prior_mean = sum(r['close'] for r in seq)/20 if seq else None
        count.append(window[-1-offset]['close'] < prior_mean if seq else None)
    def ret(length):
        seq = segment(length + 1)
        return c / seq[0]['close'] - 1 if seq and c is not None else None
    margin = ratio(c, phc)
    prior_high = window[-2].get('high') if len(window) > 1 and window[-2].get('has_actual_bar') else None
    return dict(amr20_mean_prior=amr, liq20_amount=amount_median,
        liq20=amount_median >= liquidity_floor if amount_median is not None else None,
        ma5=ma5, ma20=ma20, slope20=slope, clv=clv, ret1_adj=ret1, ret5_adj=ret(5), ret20_adj=ret(20),
        phc20=phc, phh20=phh, break_margin_close20=margin-1 if margin is not None else None,
        break_high20=c > phh if c is not None and phh is not None else None,
        intraday_reject_high20=h > phh and c <= phh if h is not None and phh is not None and c is not None else None,
        close_to_ma5=ratio(c, ma5), close_to_ma20=ratio(c, ma20), ma5_to_ma20=ratio(ma5, ma20),
        first_day_damage=c/ma20 < .97 if c is not None and ma20 is not None else None,
        severe_drop=severe,
        reclaim_ma5=pc <= prior5 and c > ma5 if pc is not None and prior5 is not None and c is not None and ma5 is not None else None,
        reclaim_ma20=pc <= prior20 and c > ma20 if pc is not None and prior20 is not None and c is not None and ma20 is not None else None,
        close_above_prior_high=c > prior_high if c is not None and positive(prior_high) else None,
        prior5_below_ma20_count=sum(count) if all(v is not None for v in count) else None,
        window_valid=True if target and prior and prior_sigma else None)


def rps_delta(current, prior, sessions, sid):
    """Exact master t-3, revision gates, missing endpoints, then fraction arithmetic."""
    day = current['trade_date']
    idx = sessions.index(day)
    if prior is None or idx < 3:
        return None
    if prior['trade_date'] != sessions[idx-3]:
        raise ValueError('ORACLE_RPS_WRONG_PRIOR_SESSION')
    for key in ('calendar_identity', 'algorithm_identity'):
        if current[key] != prior[key]:
            return None
    identities = [p['universe_identity'] for p in (current, prior)]
    identities = [v.get('producer_sha') if isinstance(v, dict) else v for v in identities]
    if identities[0] != identities[1]:
        return None
    rows = [{r['security_id']: r for r in p['rows']} for p in (current, prior)]
    values = [r.get(sid, {}).get('rps5', {}).get('value') for r in rows]
    return (values[0]-values[1])/100 if all(v is not None for v in values) else None


def signal_arithmetic(window, cfg, rps20, rps5_delta3):
    """Independent scalar reconstruction of accepted feature gates and V3 predicates."""
    def all3(values):
        return False if any(v is False for v in values) else None if any(v is None for v in values) else True
    def ratio(a, b):
        return a/b if a is not None and b is not None and b > 0 else None
    def compare(value, predicate):
        return predicate(value) if value is not None else None
    observed = [r for r in window[-101:] if r['raw_actual_bar']]
    basis_valid = bool(observed) and all(r['has_actual_bar'] for r in observed)
    closes = [r.get('close') if basis_valid and r['raw_actual_bar'] else None for r in window]
    amounts = [r.get('amount') if r['raw_actual_bar'] else None for r in window]
    def interval(values, length, offset=0):
        end = len(values)-offset
        chosen = values[end-length:end] if end >= length else []
        return chosen if len(chosen) == length and all(v is not None and math.isfinite(float(v)) for v in chosen) else None
    # Accepted feature semantics specify pandas rolling IEEE operations. Reopen
    # source arrays and use only the numerical primitive, never the feature
    # builder/classifier/producer. Its strict boundary must remain byte-for-byte.
    import pandas as pd
    rolling_means = {length:pd.Series(closes,dtype=float).rolling(length,min_periods=length).mean() for length in (5,20)}
    def mean(length, offset=0):
        value = rolling_means[length].iloc[-1-offset]
        return float(value) if math.isfinite(value) else None
    c, previous = closes[-1], closes[-2]
    ma5, ma5p1 = mean(5), mean(5,1)
    ma20, ma20p1, ma20p3, ma20p5 = mean(20), mean(20,1), mean(20,3), mean(20,5)
    ratio20 = ratio(c,ma20)
    prior_closes = interval(closes,20,1)
    phc = max(prior_closes) if prior_closes else None
    dist = ratio(c,phc)
    dist = dist-1 if dist is not None else None
    prior_amounts = interval(amounts,20,1)
    liq = median(prior_amounts) >= cfg['risk']['liquidity20_amount_gte'] if prior_amounts else None
    prior_amount_mean = pd.Series(amounts,dtype=float).shift().rolling(20,min_periods=20).mean().iloc[-1]
    amr = ratio(amounts[-1],float(prior_amount_mean) if math.isfinite(prior_amount_mean) else None)
    close21 = interval(closes,21)
    sigma = pstdev(math.log(b/a) for a,b in zip(close21,close21[1:])) if close21 else None
    bias = ratio20-1 if ratio20 is not None else None
    extension = math.log(ratio20)/(sigma*math.sqrt(20)) if ratio20 is not None and sigma is not None and sigma>0 else None
    extended = all3([compare(bias,lambda x:x>=cfg['risk']['bias20_gte']),compare(extension,lambda x:x>=cfg['risk']['extension_z20_gte'])])
    not_extended = None if extended is None else not extended
    ranges = []
    for length in (5,20):
        chosen = interval(closes,length)
        ranges.append(max(chosen)/min(chosen)-1 if chosen and min(chosen)>0 else None)
    range5,range20 = ranges
    b,s,r,t,k = (cfg[key] for key in ('BREAKOUT','SETUP','RECOVERY','TREND_BACKGROUND','STRUCTURE_BREAK'))
    breakout = all3([liq if b['requires_liquidity'] else True,compare(dist,lambda x:x>0),
        compare(ratio20,lambda x:x>=1),compare(amr,lambda x:x>=b['amount_vs_prior20_gte']),not_extended if b['reject_extended'] else True])
    setup = all3([liq if s['requires_liquidity'] else True,
        compare(ratio20,lambda x:s['close_to_ma20_min']<=x<=s['close_to_ma20_max']),
        ma20-ma20p3>=s['ma20_delta3_gte'] if ma20 is not None and ma20p3 is not None else None,
        compare(dist,lambda x:s['dist_high20_min']<=x<=s['dist_high20_max']),
        range5<=s['range5_to_range20_lte']*range20 if range5 is not None and range20 is not None and range20>0 else None,
        compare(rps5_delta3,lambda x:x>=s['rps5_delta3_gte']),not_extended if s['reject_extended'] else True])
    recovery = all3([liq if r['requires_liquidity'] else True,
        ma20>=ma20p3 if ma20 is not None and ma20p3 is not None else None,
        previous<=ma5p1 if previous is not None and ma5p1 is not None else None,
        c>ma5 if c is not None and ma5 is not None else None,
        compare(ratio20,lambda x:x>=r['close_to_ma20_gte']),compare(rps5_delta3,lambda x:x>r['rps5_delta3_gt']),
        compare(amr,lambda x:x>=r['amount_vs_prior20_gte']),not_extended if r['reject_extended'] else True])
    trend = all3([compare(ratio20,lambda x:x>=1),ma20>ma20p5 if ma20 is not None and ma20p5 is not None else None,
        compare(rps20,lambda x:x>=t['rps20_gte'])])
    structure = all3([compare(ratio20,lambda x:x<k['close_to_ma20_lt']),compare(ratio(previous,ma20p1),lambda x:x<k['close_to_ma20_lt'])])
    factor_ma20 = arithmetic(window[-27:])['ma20']
    return dict(breakout_v3=breakout, setup_v3=setup, recovery_v3=recovery, trend_background_v3=trend,
        structure_break_v3=structure,extended_v3=extended,
        ma20_nondeclining_3=factor_ma20>=ma20p3 if factor_ma20 is not None and ma20p3 is not None else None)


def source_windows(day):
    """Read accepted source chain independently; no producer/builder imports."""
    import pyarrow.parquet as pq
    head = read('data/v4/V4_DATA_ACCEPTED_HEAD.json')
    chain = json.loads(exact(head['accepted_chain']).read_bytes())
    context = json.loads(exact(chain['source_context']).read_bytes())
    sessions = context['calendar']['session_dates']
    end = sessions.index(day)
    dates = sessions[max(0, end-129):end+1]
    parent = json.loads(exact(context['parent']['components']['ADJUSTED_DAILY']).read_bytes())
    history_ref = parent['accepted_source_bindings'][0]
    columns = ['canonical_security_id', 'source_security_key', 'trade_date', 'raw_open', 'raw_high', 'raw_low', 'raw_close',
        'qfq_open', 'qfq_high', 'qfq_low', 'qfq_close', 'qfq_mul', 'qfq_add', 'amount', 'volume', 'adjusted_quality']
    rows = pq.read_table(exact(history_ref), columns=columns, filters=[('trade_date', '>=', int(dates[0].replace('-', ''))), ('trade_date', '<=', 20260924)]).to_pylist()
    bars = {}
    for row in rows:
        date = str(row['trade_date'])
        date = date[:4]+'-'+date[4:6]+'-'+date[6:]
        bars[row['canonical_security_id'], date] = dict(
            source_security_key=row['source_security_key'],
            **{field:float(row['qfq_'+field]) if row['qfq_'+field] is not None else None for field in ('open','high','low','close')},
            **{'raw_'+field:float(row['raw_'+field]) if row['raw_'+field] is not None else None for field in ('open','high','low','close')},
            amount=row['amount'], volume=row['volume'], quality=row['adjusted_quality'], mul=str(row['qfq_mul']), add=str(row['qfq_add']))
    evidence = [bind('data/v4/V4_DATA_ACCEPTED_HEAD.json'), head['accepted_chain'], chain['source_context'], history_ref]
    universe = None
    identities = {}
    target_status = {}
    for node in chain['nodes']:
        if node['trade_date'] > day:
            continue
        d = node['trade_date']
        for capability in ('RAW_DAILY', 'ADJUSTED_DAILY', 'IDENTITY_UNIVERSE', 'TRADING_STATUS'):
            component = node['components'][capability]
            ref = dict(path=component['artifact_path'], sha256=component['artifact_sha256'], bytes=component['artifact_bytes'])
            evidence.append(ref)
            records = json.loads(exact(ref).read_bytes())['rows']
            if capability == 'IDENTITY_UNIVERSE':
                if d == day:
                    universe = sorted(r['security_id'] for r in records)
                    identities = {r['security_id']:r for r in records}
                continue
            if capability == 'TRADING_STATUS':
                if d == day:
                    target_status = {r['security_id']:r for r in records}
                continue
            for r in records:
                original = bars.setdefault((r['security_id'], d), {})
                if capability == 'RAW_DAILY':
                    original.update(source_security_key=r['source_security_key'], amount=r['amount'], volume=r['volume'],
                                    **{'raw_'+field:float(r[field]) for field in ('open','high','low','close')})
                else:
                    original.update(quality=r['adjustment_readiness'], mul=r['qfq_mul'], add=r['qfq_add'],
                                    **{field:float(r[field]) if r[field] is not None else None for field in ('open','high','low','close')})
    result = {}
    for sid in universe:
        target = bars.get((sid, day), {})
        def coordinate(row):
            return tuple(Decimal(str(row[key])) if row.get(key) is not None else None for key in ('mul','add'))
        target_coordinate = coordinate(target)
        result[sid] = []
        for d in dates:
            original = bars.get((sid, d), {})
            ready = original.get('quality') == 'READY' and target_coordinate == coordinate(original) and all(original.get(field) is not None for field in ('open','high','low','close'))
            result[sid].append(dict(original, date=d, has_actual_bar=ready,
                raw_actual_bar=all(original.get('raw_'+field) is not None for field in ('open','high','low','close')),
                is_synthetic_fill=False, session_index=sessions.index(d)))
    return result, sessions, evidence, dict(identity=identities, status=target_status, history_source=history_ref)


def universe_source_class(windows, sources, day):
    """Qualification FALSE is proved by observed eligibility, never provider guessing."""
    import pyarrow.parquet as pq
    dates = {sid:{r['date'] for r in window if r.get('raw_close') is not None} for sid,window in windows.items()}
    # The entire 130-slot accepted window proves >=120 lifetime sessions for most
    # securities. Only ambiguous shorter histories need their full accepted rows.
    ambiguous = [sid for sid,observed in dates.items() if len(observed) < 120]
    if ambiguous:
        older = pq.read_table(exact(sources['history_source']), columns=['canonical_security_id','trade_date','raw_close'],
            filters=[('canonical_security_id','in',ambiguous),('trade_date','<=',20260924)]).to_pylist()
        for row in older:
            if row['raw_close'] is not None:
                d = str(row['trade_date'])
                dates[row['canonical_security_id']].add(d[:4]+'-'+d[4:6]+'-'+d[6:])
    result = {}
    reasons = Counter()
    suspended = 0
    for sid, window in windows.items():
        observed = dates[sid]
        recent = [r['date'] for r in window[-120:]]
        coverage = sum(d in observed for d in recent)/len(recent) if recent else 0
        current_member = sources['identity'][sid]['identity_status'] == 'IDENTITY_BOUND'
        latest = bool(recent) and recent[-1] in observed
        predicates = dict(accepted_current_member=current_member, source_has_real_observations=bool(observed),
            historical_observed_sessions_gte_120=len(observed)>=120, recent120_coverage_gte_075=coverage>=.75,
            latest_raw_bar_observed=latest)
        if not latest:
            status = sources['status'][sid].get('trading_status')
            # Status naming is persisted in the accepted row; no provider guess.
            status = status or sources['status'][sid].get('status')
            if status != 'SUSPENDED':
                raise ValueError('ORACLE_RAW_ABSENCE_WITHOUT_ACCEPTED_SUSPENSION')
            suspended += 1
        value = all(predicates.values())
        reasons.update(k for k,v in predicates.items() if not v)
        result[sid] = value
    return result, dict(contract_id='V4_11_R3A_UNIVERSE_SOURCE_CLASS_AUDIT_V1',
        complete_accepted_identity_universe=len(windows), accepted_suspended_no_raw_rows=suspended,
        short_history_full_source_reopens=len(ambiguous), qualification_false_reasons=dict(reasons),
        missing_fact_cast_to_false=False, source_class='ACCEPTED_RAW_AND_DATED_STATUS; PROVIDER_NOT_QUERIED',
        provider_unavailable_claim=False, current_local_file_absence_used_as_provider_evidence=False)


def same(expected, observed):
    if expected is None or isinstance(expected, bool):
        return expected is observed
    return isinstance(observed, (int,float)) and not isinstance(observed, bool) and math.isclose(expected, observed, rel_tol=2e-11, abs_tol=2e-13)


def run(day='2026-09-30', suffix='_R3A_R2'):
    pub_path = DATA+'TARGET_FACTS_'+day+suffix+'.json.gz'
    calc_path = DATA+'CALCULATIONS_'+day+suffix+'.json.gz'
    publication = json.loads(gzip.decompress((ROOT/pub_path).read_bytes()))
    calculations = {r['security_id']:r for r in json.loads(gzip.decompress((ROOT/calc_path).read_bytes()))}
    for ref in publication['source_bindings']:
        exact(ref)
    if publication['source_digest'] != digest(publication['source_bindings']):
        raise ValueError('ORACLE_WRONG_SOURCE_DIGEST')
    windows, sessions, sources, source_classes = source_windows(day)
    normal, source_class_audit = universe_source_class(windows, source_classes, day)
    if sorted(windows) != [r['security_id'] for r in publication['rows']] or sorted(calculations) != sorted(windows):
        raise ValueError('ORACLE_UNIVERSE_COVERAGE')
    # Accepted reader proves published RPS bindings; arithmetic below ignores its deltas.
    from src.v4.a02_a05_external_acceptance_r1 import read_accepted_rps
    rps = read_accepted_rps(ROOT, day)
    current, prior = rps['publication'], rps['prior_publications'][3]
    rps_rows = {r['security_id']:r for r in current['rows']}
    cfg = read('config/research_attention_v3.yaml')['thresholds']['stock_signals']
    threshold = cfg['risk']['liquidity20_amount_gte']
    mismatch = []
    checks = Counter()
    examples = defaultdict(list)
    source_slot_checks = 0
    for row in publication['rows']:
        sid = row['security_id']
        actual = windows[sid][-27:]
        recorded = calculations[sid]['window']
        if [r['date'] for r in actual] != [r['date'] for r in recorded]:
            raise ValueError('ORACLE_MASTER_WINDOW_MISMATCH')
        for source, slot in zip(actual, recorded):
            for field in ('source_security_key','quality','mul','add','has_actual_bar','raw_actual_bar','session_index','open','high','low','close','raw_open','raw_high','raw_low','raw_close','amount','volume'):
                if source.get(field) != slot.get(field):
                    raise ValueError('ORACLE_WINDOW_NOT_ACCEPTED_SOURCE_ROW:'+field)
            source_slot_checks += 1
        expected = arithmetic(actual, threshold)
        expected['rps20'] = rps_rows.get(sid, {}).get('rps20', {}).get('value')
        if expected['rps20'] is not None:
            expected['rps20'] /= 100
        expected['rps5_delta3'] = rps_delta(current, prior, rps['sessions'], sid)
        expected.update(signal_arithmetic(windows[sid], cfg, expected['rps20'], expected['rps5_delta3']))
        expected['actual_bar'] = actual[-1]['raw_actual_bar']
        expected['normal_universe'] = normal[sid]
        for field, value in expected.items():
            observed = row['facts'].get(field, {}).get('value', calculations[sid]['values'].get(field))
            checks[field] += 1
            if not same(value, observed):
                mismatch.append(dict(security_id=sid, field=field, expected=value, observed=observed))
            if len(examples[field]) < 2 and value is not None:
                example = dict(security_id=sid, source_window_digest=digest(recorded), independently_calculated=value, published=observed)
                if field in ('amr20_mean_prior', 'liq20_amount'):
                    example.update(target_amount_cny=actual[-1].get('amount'),
                        prior20_amounts_cny=[r.get('amount') for r in actual[-21:-1]],
                        prior20_master_dates=[r['date'] for r in actual[-21:-1]],
                        target_date=actual[-1]['date'], target_excluded_from_denominator=True)
                examples[field].append(example)
        for field, fact in row['facts'].items():
            if fact['source_digest'] != publication['source_digest'] or fact['window_identity'] != digest(recorded):
                raise ValueError('ORACLE_FACT_SOURCE_WINDOW_BINDING')
    report = dict(contract_id='V4_11_R3A_INDEPENDENT_ACCEPTED_SOURCE_ARITHMETIC_ORACLE_V1',
        status='PASS' if not mismatch else 'FAIL', trade_date=day, universe_coverage=len(windows),
        producer_invoked_for_arithmetic=False, calculation_payload_role='WINDOW_EXHIBIT_ONLY; ALL_SLOTS_REOPENED_FROM_ACCEPTED_ROWS',
        source_slot_checks=source_slot_checks, fields_checked=dict(checks), mismatches=mismatch,
        universe_source_class_audit=source_class_audit,
        sample_arithmetic=dict(examples), accepted_source_bindings=sources,
        source_digest=publication['source_digest'], publication_digest=publication['logical_digest'],
        publication=bind(pub_path), calculation_window_evidence=bind(calc_path),
        rps_current_binding=rps['head']['publications'][day],
        rps_exact_prior_binding=rps['head']['publications'][prior['trade_date']] if prior else None,
        knowledge_lineage='RECONSTRUCTED_CORRECTED', AS_RECORDED=False,
        synthetic_vector_scope='ORACLE_ONLY; NO_REAL_TRUE_CLAIM',
        independent_verifier_source=bind('scripts/verify_v4_11_target_facts_r3a.py'),
        meaningful_tests_source=bind('tests/v4_11_r3a/test_target_fact_oracle.py'),
        arithmetic_execution=dict(factor_mean='INDEPENDENT_FRACTION_FROM_BINARY_FLOAT_EXACT_SUM_ROUND_ONCE',
            feature_mean='INDEPENDENT_ACCEPTED_SOURCE_ARRAY_PANDAS_ROLLING_IEEE_PRIMITIVE',
            prior5_count_mean='FROZEN_P12_03_LEFT_TO_RIGHT_SUM_DIVIDED_BY_20',
            strict_business_predicates='LEGACY_OPERATORS_UNCHANGED; NO_EPSILON_OR_THRESHOLD_TUNING'),
        permissions=dict(production=False, shadow=False, focus=False, global_mandatory_adoption=False))
    write(REPORT, report, immutable=False)
    if mismatch:
        raise ValueError('INDEPENDENT_ARITHMETIC_MISMATCH:'+json.dumps(mismatch[:5]))
    return report


if __name__ == '__main__':
    result = run()
    print(json.dumps(dict(status=result['status'], coverage=result['universe_coverage'], source_slots=result['source_slot_checks'])))
