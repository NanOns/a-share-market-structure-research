from datetime import date, datetime, timezone
import importlib.util
import math
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[2]


def _module():
    path = ROOT / "scripts/build_m8c_local_reference_preview.py"
    spec = importlib.util.spec_from_file_location("build_m8c_local_reference_preview", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _bar(day, close, *, synthetic=False):
    return {
        "security_id": "SH.600001",
        "date": day,
        "raw_close": close,
        "has_actual_bar": True,
        "data_observed": True,
        "is_synthetic_fill": synthetic,
        "missing_state": "BAR",
    }


def test_local_ohlc_reference_uses_previous_valid_raw_close_only():
    module = _module()
    rows = module.build_reference_rows(
        [{"security_id": "SH.600001", "trade_date": date(2026, 9, 8)}],
        [_bar(date(2026, 9, 7), 10.0), _bar(date(2026, 9, 8), 11.0)],
        source_ref="local:normalized",
        observed_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
    )
    assert rows[0]["quote_prev_close"] == 10.0
    assert rows[0]["status_known"] is False
    assert rows[0]["quote_capability"] == "APPROXIMATE"
    assert rows[0]["reference_status"] == "APPROXIMATE"
    assert rows[0]["rule_id"] == "UNREGISTERED"
    assert rows[0]["float_shares"] is None


def test_local_ohlc_does_not_promote_synthetic_bar_to_exact_reference():
    module = _module()
    rows = module.build_reference_rows(
        [{"security_id": "SH.600001", "trade_date": date(2026, 9, 8)}],
        [_bar(date(2026, 9, 7), 10.0, synthetic=True), _bar(date(2026, 9, 8), 11.0)],
        source_ref="local:normalized",
        observed_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
    )
    assert rows[0]["quote_prev_close"] is None
    assert rows[0]["status_known"] is False
    assert "QUOTE_PREVIOUS_CLOSE_UNAVAILABLE" in rows[0]["quality_codes"]


def test_local_continuous_bars_stay_approximate_without_independent_reference_event():
    module = _module()
    def stable_bar(day, close):
        row = _bar(day, close)
        row.update({
            "qfq_mul": "1",
            "qfq_add": "0",
            "adjustment_status": "VERIFIED_REPRODUCIBLE_TDX_NATIVE",
            "adjustment_version": "tdx-affine-qfq-v0.2",
            "is_master_session": True,
        })
        return row

    rows = module.build_reference_rows(
        [{"security_id": "SH.600001", "trade_date": date(2026, 9, 8)}],
        [stable_bar(date(2026, 9, 7), 10.0), stable_bar(date(2026, 9, 8), 11.0)],
        source_ref="local:normalized",
        observed_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
    )
    assert rows[0]["quote_prev_close"] == 10.0
    assert rows[0]["status_known"] is False
    assert rows[0]["quote_capability"] == "APPROXIMATE"
    assert rows[0]["reference_status"] == "APPROXIMATE"
    assert rows[0]["ex_rights_reference_unknown"] is True
    assert rows[0]["reference_basis"] == "RAW_PREV_CLOSE_APPROXIMATE"


def test_board_identity_is_configured_scope_only_and_not_a_limit_rule():
    module = _module()
    assert module.board_for_security_id("SH.688001") == ("SH", "STAR")
    assert module.board_for_security_id("SZ.300001") == ("SZ", "GROWTH")
    assert module.board_for_security_id("BJ.920001") == ("BJ", "BJ")
    assert module.board_for_security_id("SH.600001") == ("SH", "MAIN")


def test_normalized_input_gate_rejects_non_finite_values_and_duplicate_dates():
    module = _module()
    infinite = _bar(date(2026, 9, 7), math.inf)
    with pytest.raises(module.ReferenceCapabilityError, match="NON_FINITE_RAW_CLOSE"):
        module.build_reference_rows([], [infinite], source_ref="local", observed_at=datetime(2026, 9, 11, tzinfo=timezone.utc))

    duplicate = [_bar(date(2026, 9, 7), 10.0), _bar(date(2026, 9, 7), 10.1)]
    with pytest.raises(module.ReferenceCapabilityError, match="DUPLICATE_SECURITY_DATE"):
        module.build_reference_rows([], duplicate, source_ref="local", observed_at=datetime(2026, 9, 11, tzinfo=timezone.utc))


def test_normalized_input_gate_rejects_unknown_adjustment_status():
    module = _module()
    row = _bar(date(2026, 9, 7), 10.0)
    row["adjustment_status"] = "MADE_UP_STATUS"
    with pytest.raises(module.ReferenceCapabilityError, match="STATUS_NOT_WHITELISTED"):
        module.build_reference_rows([], [row], source_ref="local", observed_at=datetime(2026, 9, 11, tzinfo=timezone.utc))
