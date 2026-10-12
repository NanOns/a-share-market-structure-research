from collections import defaultdict
from decimal import Decimal
import json
from types import SimpleNamespace

import pytest

from focus_tracker.v4_exact_identity_adapter_r4 import AcceptedPaths, CONTRACT
from workbench_db.v4_series_pg_r1 import build
from workbench_service.current_v4_context import SourceInvalid, digest


def paths(tmp_path, *, symbol='SZ.000062'):
    series = tmp_path / 'series.pg.json'
    build(tmp_path, series, [('SEC-A', day, dict(trade_date=day, symbol=symbol, raw_ohlc=[value] * 4)) for day, value in [('2026-09-28', '10'), ('2026-09-30', '9.70')]], t0='2026-09-30', source_digest='a' * 64)
    p = AcceptedPaths.__new__(AcceptedPaths)
    p.series, p.calendar, p.bindings, p.cache, p.status = series, ['2026-09-28', '2026-09-30'], {}, {}, {}
    p.symbols = {'SEC-A': 'SZ.000062'}
    p.events = defaultdict(list, {'SZ.000062': [SimpleNamespace(security_id='SZ.000062', event_date=20260930, category=1, c1=3.0, c2=0.0, c3=0.0, c4=0.0, source_record_index=0)]})
    p.dispositions = {'1': {'formal_disposition': 'SUPPORTED_PRICE_AFFECTING'}}
    return p


def test_internal_id_resolves_cash_action_on_real_pg_path(tmp_path):
    p = paths(tmp_path)
    fact = p.path('SEC-A', '2026-09-28', '2026-09-30')
    assert fact['quality'] == 'READY'
    assert fact['source_security_key'] == 'SZ.000062'
    assert Decimal(fact['metrics']['return_close']) == 0
    assert Decimal(fact['metrics']['peak_close']) == Decimal('9.70')
    assert fact['price_basis'] == 'TDX_EXACT_NATIVE_AFFINE_AS_OF_OBSERVATION_R4'


def test_mismatched_series_symbol_is_refused_not_unadjusted(tmp_path):
    p = paths(tmp_path, symbol='SEC-A')
    with pytest.raises(SourceInvalid, match='IDENTITY_MISMATCH'):
        p.path('SEC-A', '2026-09-28', '2026-09-30')


def test_missing_identity_and_unsupported_action_fail_closed(tmp_path):
    p = paths(tmp_path)
    with pytest.raises(SourceInvalid, match='IDENTITY_MISSING'):
        p.path('SEC-MISSING', '2026-09-28', '2026-09-30')
    p.events['SZ.000062'][0].category = 99
    fact = p.path('SEC-A', '2026-09-28', '2026-09-30')
    assert fact['quality'] == 'DATA_UNAVAILABLE' and fact['metrics'] is None
    assert fact['reason'] == 'UNSUPPORTED_OR_UNKNOWN_PRICE_IMPACT'


def test_future_action_does_not_change_earlier_coordinate(tmp_path):
    p = paths(tmp_path)
    p.events['SZ.000062'][0].event_date = 20261009
    fact = p.path('SEC-A', '2026-09-28', '2026-09-28')
    assert Decimal(fact['close']) == Decimal('10')
    assert Decimal(fact['metrics']['return_close']) == 0


@pytest.mark.parametrize('rows,error', [
    ([{'security_id': 'SEC-A', 'source_security_key': 'SEC-A'}], 'KEY_INVALID'),
    ([{'security_id': 'SEC-A', 'source_security_key': 'SH.600000'}] * 2, 'IDENTITY_DUPLICATE'),
    ([{'security_id': 'SEC-A', 'source_security_key': 'SH.600000'}, {'security_id': 'SEC-B', 'source_security_key': 'SH.600000'}], 'IDENTITY_DUPLICATE'),
])
def test_bound_map_rejects_invalid_or_duplicate_identity(tmp_path, rows, error):
    path = tmp_path / 'identity.json'
    path.write_text(json.dumps({'rows': rows}))
    with pytest.raises(SourceInvalid, match=error):
        AcceptedPaths(tmp_path, dict(path_contract=CONTRACT, security_identity=dict(path='identity.json', sha256=digest(path.read_bytes()))))
