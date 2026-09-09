import json

import pandas as pd
import pytest

from workbench_analysis.reference_capability import (
    ReferenceCapabilityError,
    build_reference_capability_report,
    normalize_reference_rows,
)


def _rows():
    return pd.DataFrame(
        [
            {"security_id": "SH.600001", "trade_date": "2026-09-08", "quote_prev_close": 10, "float_shares": 1000000, "shares_unit": "SHARES", "shares_basis": "FLOAT_SHARES", "source_ref": "local:ref:1"},
            {"security_id": "SH.600002", "trade_date": "2026-09-08", "quote_prev_close": None, "float_shares": 2000000, "shares_unit": "LOTS", "shares_basis": "UNKNOWN", "source_ref": "local:ref:2"},
            {"security_id": "SH.600003", "trade_date": "2026-09-08", "quote_prev_close": 11, "float_shares": None, "source_ref": None},
        ]
    )


def test_reference_capabilities_require_source_and_verified_share_unit():
    result = normalize_reference_rows(_rows(), cutoff="2026-09-08", rule_id="RULE_PENDING_M8C02")
    exact = result[result.security_id == "SH.600001"].iloc[0]
    unknown = result[result.security_id == "SH.600002"].iloc[0]
    missing = result[result.security_id == "SH.600003"].iloc[0]
    assert exact.quote_capability == "EXACT" and exact.shares_capability == "EXACT" and exact.turnover_capability == "EXACT"
    assert unknown.quote_capability == "UNAVAILABLE" and unknown.shares_capability == "UNKNOWN" and unknown.turnover_capability == "UNKNOWN"
    assert missing.quote_capability == "UNKNOWN" and missing.shares_capability == "UNAVAILABLE"
    assert "SHARES_UNIT_UNKNOWN" in unknown.quality_codes
    assert set(result.rule_registration_status) == {"REGISTERED"}


def test_report_counts_exact_unknown_unavailable_and_keeps_missing_null():
    report = build_reference_capability_report(_rows(), cutoff="2026-09-08")
    assert report["price_capability"] == {"EXACT": 1, "UNKNOWN": 1, "UNAVAILABLE": 1}
    assert report["shares_capability"] == {"EXACT": 1, "UNKNOWN": 1, "UNAVAILABLE": 1}
    assert report["policy"]["volume_as_shares"] is False
    assert report["items"][2]["quote_prev_close"] == 11
    assert report["items"][2]["float_shares"] is None
    json.dumps(report, ensure_ascii=False, default=str)


def test_reference_input_future_and_duplicate_rows_are_rejected():
    with pytest.raises(ReferenceCapabilityError, match="AFTER_CUTOFF"):
        normalize_reference_rows(_rows().assign(trade_date="2026-09-09"), cutoff="2026-09-08")
    with pytest.raises(ReferenceCapabilityError, match="DUPLICATE"):
        normalize_reference_rows(pd.concat([_rows(), _rows().iloc[[0]]], ignore_index=True))
