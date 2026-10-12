from datetime import date
from decimal import Decimal
from hashlib import sha256
from copy import deepcopy
import pytest
from adjustment.tdx_adjustment_v0_3 import XrxdEvent,build_affine_factors
from adjustment.exact_factor_transport_r1 import ExactFactorTransport
from focus_tracker.exact_path_candidate_r3 import exact_path,exact_path_receipt

SOURCE=b'exact isolated path source';SID='SH.688553';SESSIONS=[date(2025,4,14),date(2026,10,9)]
def args():
    events=[XrxdEvent(SID,20250613,Decimal('4.63')),XrxdEvent(SID,20260617,Decimal('2'),bonus_transfer_per_10=Decimal('4.8'))]
    factors=build_affine_factors([20250414,20261009],events);rows={}
    for day in SESSIONS:
        wire=ExactFactorTransport(SID,20261009,sha256(SOURCE).hexdigest(),factors[int(day.strftime('%Y%m%d'))]).to_dict()
        rows[day]=dict(has_actual_bar=True,exact_factor=wire,raw_open='15.13',raw_high='16',raw_low='14',raw_close='15.13')
    return dict(sessions=SESSIONS,rows=rows,source_bytes=SOURCE,security_id=SID,basis_date=20261009)

def test_exact_coordinate_tie_and_real_metrics_consumer():
    options=args();path=exact_path(**options)
    assert path[0].close==Decimal('9.78') and path[-1].close==Decimal('15.13')
    receipt=exact_path_receipt(**options)
    assert Decimal(receipt['metrics']['return_close'])==Decimal('15.13')/Decimal('9.78')-1
    assert Decimal(receipt['metrics']['mfe'])==Decimal('16')/Decimal('9.78')-1
    assert receipt['status']=='READY' and receipt['PIT_ELIGIBLE'] is False

def test_missing_session_remains_source_incomplete():
    options=args();del options['rows'][SESSIONS[0]]
    assert exact_path(**options) is None
    assert exact_path_receipt(**options)['status']=='SOURCE_INCOMPLETE'

def test_source_drift_and_missing_exact_refused():
    options=args();options['source_bytes']=b'different'
    with pytest.raises(ValueError,match='SOURCE_MISMATCH'):exact_path(**options)
    options=args();del options['rows'][SESSIONS[0]]['exact_factor']['coefficients']['qfq_mul']
    with pytest.raises(ValueError,match='COEFFICIENT_MISSING'):exact_path(**options)

def test_mixed_row_date_and_float_raw_refused():
    options=args();options['rows'][SESSIONS[0]]['exact_factor']['trade_date']=20250415
    with pytest.raises(ValueError,match='ROW_DATE_MISMATCH'):exact_path(**options)
    options=args();options['rows'][SESSIONS[0]]['raw_close']=15.13
    with pytest.raises(ValueError,match='PRECISION_REQUIRED'):exact_path(**options)

def test_empty_and_duplicate_calendar_refused():
    for sessions in ([],SESSIONS+SESSIONS):
        options=args();options['sessions']=sessions
        with pytest.raises(ValueError,match='SESSION_ORDER'):exact_path(**options)

def test_observation_coordinate_cancels_later_actions_without_decimal_approximation():
    options=args();options['sessions']=[SESSIONS[0]]
    path=exact_path(**options)
    assert path[0].close==Decimal('15.13') and path[0].open==Decimal('15.13')
    assert path[0].high==Decimal('16') and path[0].low==Decimal('14')
