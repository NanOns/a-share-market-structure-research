"""Oracle-only vectors; no vector is a real stock or a business TRUE claim."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import gzip
import json
from pathlib import Path
import re
import pytest
from scripts.verify_v4_11_target_facts_r3a import arithmetic, same, rps_delta, universe_source_class, DATA, REPORT
from scripts.next_round_bundle_r1 import bind, read
from src.v4.target_fact_producers_r3 import produce, seal, validate, CONTRACT, PARAMETERS
from src.v4.rps_pit_history_a02_v1 import delta
from src.v4.confirmation import digest

ROOT = Path(__file__).resolve().parents[2]
CFG = read('config/research_attention_v3.yaml')


def oracle_only_window(kind='boundary'):
    prices = [10 * (1.015**i if kind == 'positive' else .985**i if kind == 'negative' else 1) for i in range(27)]
    dates = [(datetime(2026, 1, 1) + timedelta(days=i)).date().isoformat() for i in range(27)]
    rows = [dict(date=d, anchor_cutoff=dates[-1], session_index=i, price_basis='TDX_NATIVE_AFFINE_QFQ',
        open=c, high=c*1.01, low=c*.99, close=c, raw_open=c, raw_high=c*1.01, raw_low=c*.99, raw_close=c,
        amount=20_000_000, volume=1000, has_actual_bar=True, raw_actual_bar=True, is_synthetic_fill=False)
        for i, (d, c) in enumerate(zip(dates, prices))]
    if kind == 'missing':
        rows[-3]['has_actual_bar'] = rows[-3]['raw_actual_bar'] = False
    return rows


def production(rows):
    feature = dict(ma20_prior3=arithmetic(rows[:-3])['ma20'], rps20=.7, rps5_delta3=0)
    return produce(rows, feature, normal_universe=True, identity_compatible=True, parameters=CFG)[0]


@pytest.mark.parametrize('kind', ['positive', 'negative', 'boundary', 'missing'])
def test_price_ma_return_slope_and_damage_families_against_independent_arithmetic(kind):
    rows = oracle_only_window(kind)
    expected = arithmetic(rows)
    observed = production(rows)
    for field in expected:
        assert same(expected[field], observed[field]), field
    if kind == 'positive':
        assert expected['slope20'] > 0 and expected['ret5_adj'] > 0 and expected['ret20_adj'] > 0
    elif kind == 'negative':
        assert expected['slope20'] < 0 and expected['ret5_adj'] < 0 and expected['ret20_adj'] < 0
    elif kind == 'boundary':
        assert abs(expected['slope20']) < 1e-13 and expected['ret1_adj'] == 0
        assert expected['ma5'] == expected['ma20'] == 10
        assert expected['first_day_damage'] is False
    else:
        assert expected['ma5'] is expected['ma20'] is expected['slope20'] is None
        assert expected['window_valid'] is None


@pytest.mark.parametrize('target_amount', [24_000_000, 16_000_000, 20_000_000, None])
def test_amr_amount_fraction_positive_negative_boundary_missing(target_amount):
    rows = oracle_only_window()
    rows[-1]['amount'] = target_amount
    expected = arithmetic(rows)
    observed = production(rows)
    assert same(expected['amr20_mean_prior'], observed['amr20_mean_prior'])
    assert expected['amr20_mean_prior'] == (target_amount / 20_000_000 if target_amount is not None else None)


def test_twenty_prior_master_sessions_and_target_exclusion_mean_vs_median():
    rows = oracle_only_window()
    for i, row in enumerate(rows[-21:-1], 1):
        row['amount'] = i * 1_000_000
    rows[-2]['amount'] = 100_000_000
    rows[-1]['amount'] = 145_000_000
    assert production(rows)['amr20_mean_prior'] == pytest.approx(10)
    assert production(rows)['liq20_amount'] == 10_500_000
    changed = deepcopy(rows)
    changed[-1]['amount'] *= 100
    assert production(changed)['liq20_amount'] == production(rows)['liq20_amount']
    assert production(changed)['amr20_mean_prior'] == pytest.approx(production(rows)['amr20_mean_prior'] * 100)
    too_short = rows[-20:]
    assert production(too_short)['amr20_mean_prior'] is None


@pytest.mark.parametrize('prior_amount, expected', [(20_000_001, True), (19_999_999, False), (20_000_000, True), (None, None)])
def test_liquidity_prior_median_threshold_and_missing_session(prior_amount, expected):
    rows = oracle_only_window()
    for row in rows[-21:-1]:
        row['amount'] = prior_amount
    rows[-1]['amount'] = 900_000_000
    assert production(rows)['liq20'] is expected
    assert arithmetic(rows)['liq20'] is expected


@pytest.mark.parametrize('close, high, low, expected', [(10.8,11,10,.8),(10.2,11,10,.2),(10,11,10,0),(11,11,10,1),(10,10,10,None)])
def test_clv_positive_negative_lower_upper_and_zero_denominator(close, high, low, expected):
    rows = oracle_only_window()
    rows[-1].update(open=close, high=high, low=low, close=close)
    actual = production(rows)['clv']
    assert actual == pytest.approx(expected) if expected is not None else actual is None
    assert same(arithmetic(rows)['clv'], actual)


def test_missing_raw_master_slot_does_not_compress_window_or_become_false():
    rows = oracle_only_window()
    rows[-10]['raw_actual_bar'] = rows[-10]['has_actual_bar'] = False
    result = production(rows)
    assert result['amr20_mean_prior'] is None and result['liq20'] is None
    assert result['window_valid'] is None
    assert result['ma20'] is None and result['slope20'] is None


def test_compressed_master_calendar_gap_is_rejected():
    rows = oracle_only_window()
    del rows[-10]
    with pytest.raises(ValueError, match='MASTER_SESSION_GAP'):
        production(rows)


@pytest.mark.parametrize('amount', [0, -1])
def test_nonpositive_required_amount_is_unknown_not_numeric_zero(amount):
    rows = oracle_only_window()
    rows[-1]['amount'] = amount
    assert production(rows)['amr20_mean_prior'] is None
    assert production(rows)['window_valid'] is None
    assert arithmetic(rows)['amr20_mean_prior'] is None


def test_first_candidate_decimal_coordinate_defect_is_preserved_as_fail_evidence():
    failure = read('reports/v4_11_r3a/INDEPENDENT_ORACLE_R1_DECIMAL_COORDINATE_FAILURE.json')
    assert failure['status'] == 'FAIL_INITIAL_CANDIDATE_COORDINATE_REPRESENTATION'
    assert failure['admission'] == 'NOT_ACCEPTED'
    assert failure['textually_different_numerically_equal_ready_slots'] > 0
    for sample in failure['samples']:
        assert sample['source_coordinate'] != sample['target_coordinate']
        assert list(map(Decimal,sample['source_coordinate'])) == list(map(Decimal,sample['target_coordinate']))
    assert Decimal('0E-18') == Decimal('0')
    assert Decimal('1.000000000000000000') == Decimal('1')
    assert Decimal('1.000000000000000001') != Decimal('1')


def test_heterogeneous_accepted_mean_execution_preserves_prior_count_boundary():
    failure = read('reports/v4_11_r3a/INDEPENDENT_ORACLE_R3_PROJECTION_FP_BOUNDARY_FAILURE.json')
    mismatch = failure['mismatches'][0]
    assert mismatch['field'] == 'prior5_below_ma20_count'
    assert mismatch['observed'] == 5 and mismatch['expected'] == 4
    calculations = json.loads(gzip.decompress((ROOT / (DATA+'CALCULATIONS_2026-09-30_R3A_R2.json.gz')).read_bytes()))
    row = next(r for r in calculations if r['security_id'] == mismatch['security_id'])
    # This is an execution-boundary regression, with immutable real operands;
    # the oracle remains independent and cannot alter a business threshold.
    assert arithmetic(row['window'])['prior5_below_ma20_count'] == 5
    assert row['values']['prior5_below_ma20_count'] == 5


@pytest.mark.parametrize('status, raw_latest, expected', [('ACTUAL_TRADED',True,True),('SUSPENDED',False,False)])
def test_normal_universe_known_false_requires_accepted_eligibility_fact(status, raw_latest, expected):
    sid = 'SYNTHETIC_MECHANISM_VECTOR'
    window = [dict(date=(datetime(2025,1,1)+timedelta(days=i)).date().isoformat(),raw_close=10) for i in range(130)]
    if not raw_latest:
        window[-1]['raw_close'] = None
    inputs = dict(identity={sid:{'identity_status':'IDENTITY_BOUND'}},status={sid:{'status':status}})
    result, audit = universe_source_class({sid:window},inputs,window[-1]['date'])
    assert result[sid] is expected
    assert audit['missing_fact_cast_to_false'] is False
    assert audit['provider_unavailable_claim'] is False
    assert audit['current_local_file_absence_used_as_provider_evidence'] is False


def test_raw_absence_conflicting_with_accepted_actual_status_fails_closed():
    sid = 'SYNTHETIC_MECHANISM_VECTOR'
    window = [dict(date=(datetime(2025,1,1)+timedelta(days=i)).date().isoformat(),raw_close=10) for i in range(130)]
    window[-1]['raw_close'] = None
    inputs = dict(identity={sid:{'identity_status':'IDENTITY_BOUND'}},status={sid:{'status':'ACTUAL_TRADED'}})
    with pytest.raises(ValueError,match='RAW_ABSENCE_WITHOUT_ACCEPTED_SUSPENSION'):
        universe_source_class({sid:window},inputs,window[-1]['date'])


@pytest.mark.parametrize('current_value, prior_value', [(80,70),(60,70),(70,70),(None,70),(70,None)])
def test_rps_exact_prior_fraction_positive_negative_boundary_missing(current_value, prior_value):
    sessions = ['ORACLE_SESSION_'+str(i) for i in range(7)]
    def pub(day, value):
        return dict(trade_date=day, calendar_identity='ORACLE_CALENDAR', algorithm_identity='ORACLE_ALGORITHM',
            universe_identity={'producer_sha':'ORACLE_UNIVERSE'}, logical_digest='ORACLE_DIGEST',
            rows=[dict(security_id='SYNTHETIC_MECHANISM_VECTOR',rps5={'value':value},rps20={'value':value})])
    current, prior = pub(sessions[-1], current_value), pub(sessions[-4], prior_value)
    expected = rps_delta(current, prior, sessions, 'SYNTHETIC_MECHANISM_VECTOR')
    observed = delta(current, prior, 3, sessions)[0]['fields']['rps5_delta3']['value']
    assert same(expected, observed/100 if observed is not None else None)
    wrong_prior = deepcopy(prior)
    wrong_prior['trade_date'] = sessions[-3]
    with pytest.raises(ValueError):
        rps_delta(current, wrong_prior, sessions, 'SYNTHETIC_MECHANISM_VECTOR')
    with pytest.raises(ValueError):
        delta(current, wrong_prior, 3, sessions)


def admission_vector():
    cutoff = datetime.now(timezone.utc).isoformat()
    sources = [bind('config/research_attention_v3.yaml')]
    return seal(dict(producer_contract_id=CONTRACT,parameter_set_id=PARAMETERS,
        scope='REAL_ACCEPTED_SOURCE_CANDIDATE', accepted=False, AS_RECORDED=False,
        trade_date='2026-09-30',knowledge_cutoff=cutoff,source_bindings=sources,source_digest=digest(sources),
        permissions=dict(production=False,shadow=False,focus=False,global_mandatory_adoption=False),
        rows=[dict(security_id='SYNTHETIC_MECHANISM_VECTOR', trade_date='2026-09-30',
                   facts={'amr20_mean_prior':dict(value=1.2,quality='KNOWN',reason=None,time_role='TARGET_SESSION_D0',
                    source_digest=digest(sources),window_identity=digest([]),system_available_at=cutoff)})]))


def test_admission_negative_vectors_begin_with_valid_oracle_only_candidate():
    vector = admission_vector()
    assert validate(vector, ROOT, expected_sources=vector['source_bindings']) == vector


@pytest.mark.parametrize('fault', ['wrong_source','source_hash','future_cutoff','future_fact','same_day_feedback','focus','final_state','unknown_zero','unknown_false','no_reason','diagnostic_true'])
def test_admission_rejects_wrong_source_future_feedback_and_missing_fabrication(fault):
    vector = admission_vector()
    original_sources = deepcopy(vector['source_bindings'])
    fact = vector['rows'][0]['facts']['amr20_mean_prior']
    if fault == 'wrong_source':
        vector['source_bindings'] = [bind('config/v4_11_legacy_extraction_manifest_r2.json')]
    elif fault == 'source_hash':
        vector['source_bindings'][0]['sha256'] = '0'*64
    elif fault == 'future_cutoff':
        vector['knowledge_cutoff'] = '2999-01-01T00:00:00+00:00'
    elif fault == 'future_fact':
        fact['system_available_at'] = '2999-01-01T00:00:00+00:00'
    elif fault in ('same_day_feedback','focus','final_state'):
        fact['time_role'] = {'same_day_feedback':'SAME_DAY_DOWNSTREAM','focus':'FOCUS','final_state':'FINAL_STATE'}[fault]
    elif fault in ('unknown_zero','unknown_false'):
        fact.update(value=0 if fault == 'unknown_zero' else False, quality='UNKNOWN',reason='SOURCE_MISSING')
    elif fault == 'no_reason':
        fact.update(value=None,quality='UNKNOWN',reason=None)
    else:
        vector['rows'][0]['facts']['pullback_episode_confirmed'] = dict(fact,value=True)
    vector = seal(vector)
    with pytest.raises(ValueError):
        validate(vector, ROOT, expected_sources=original_sources)


def test_real_source_oracle_report_has_exact_rps_prior_binding_and_full_market_readback():
    if not (ROOT / REPORT).exists():
        pytest.fail('Real independent accepted source oracle report is required')
    report = read(REPORT)
    assert report['status'] == 'PASS' and report['universe_coverage'] == 5224
    assert report['source_slot_checks'] == 5224*27
    assert report['mismatches'] == [] and report['producer_invoked_for_arithmetic'] is False
    assert report['rps_exact_prior_binding'] != report['rps_current_binding']
    from src.v4.rps_pit_history_a02_v1 import read_publication
    current = read_publication(ROOT, report['rps_current_binding'])
    prior = read_publication(ROOT, report['rps_exact_prior_binding'])
    from src.v4.a02_a05_external_acceptance_r1 import read_accepted_rps
    accepted = read_accepted_rps(ROOT, '2026-09-30')
    assert prior['trade_date'] == accepted['sessions'][accepted['sessions'].index(current['trade_date'])-3]
    wrong = deepcopy(report['rps_exact_prior_binding'])
    wrong['sha256'] = '0'*64
    with pytest.raises(ValueError):
        read_publication(ROOT, wrong)


def test_new_oracle_and_producer_sources_have_no_literal_market_symbol():
    paths = ['scripts/verify_v4_11_target_facts_r3a.py','src/v4/target_fact_producers_r3.py','scripts/build_v4_11_target_facts_r3a.py']
    pattern = re.compile(r'(?i)(?:\b(?:sh|sz|bj)[.:-]?\d{6}\b|\b\d{6}\.(?:sh|sz|bj)\b)')
    for path in paths:
        assert not pattern.search((ROOT / path).read_text(encoding='utf8')), path
