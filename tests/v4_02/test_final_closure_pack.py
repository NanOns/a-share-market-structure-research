from decimal import Decimal
import json
from pathlib import Path

from workbench_analysis.v4_02_closure import (
    TEMPORAL_REQUIRED_CASES,
    adjusted_value_or_none,
    asof_visible_rows,
    category_disposition_for_security,
    classify_dated_status,
    closed_only_disposition,
    historical_adjusted_lineage,
    validate_snapshot_hash_binding,
)
from adjustment.tdx_adjustment import XrxdEvent, build_affine_factors
from workbench_analysis.limit_rules import LimitStateService
from workbench_analysis.v4_02_closure import ex_right_reference_price


def test_tdx_actual_bar_overrides_baostock_status_conflict():
    assert classify_dated_status(True, "0") == "ACTUAL_TRADED"


def test_missing_bar_never_implies_suspension_without_provider_fact():
    assert classify_dated_status(False, None) == "UNKNOWN"


def test_unknown_gbbq_category_blocks_only_affected_security():
    dispositions = {"SEC-A": "UNAVAILABLE_UNKNOWN_PRICE_IMPACT"}
    assert category_disposition_for_security(dispositions, "SEC-A") == "UNAVAILABLE_UNKNOWN_PRICE_IMPACT"
    assert category_disposition_for_security(dispositions, "SEC-B") == "READY"


def test_qfq_blocked_never_falls_back_raw():
    assert adjusted_value_or_none("UNAVAILABLE_UNKNOWN_PRICE_IMPACT", Decimal("12.34")) is None
    assert adjusted_value_or_none("READY", Decimal("12.34")) == Decimal("12.34")


def test_closed_only_rejects_unknown_gap():
    assert closed_only_disposition(["SUSPENDED", "UNKNOWN"]) == "BLOCKED"


def test_asof_partial_never_consumes_future_daily():
    rows = [{"trade_date": "2026-09-24"}, {"trade_date": "2026-09-25"}]
    assert asof_visible_rows(rows, "2026-09-24") == [rows[0]]


def test_temporal_required_8_cases_present():
    assert len(TEMPORAL_REQUIRED_CASES) == 8
    assert set(TEMPORAL_REQUIRED_CASES) == {
        "WEEKLY_MONDAY", "WEEKLY_WEDNESDAY", "WEEKLY_FRIDAY", "MONTH_START",
        "MONTH_MIDDLE", "MONTH_END", "HOLIDAY_SHORTENED_WEEK", "NONTRADING_CALENDAR_MONTH_END",
    }


def test_future_corporate_action_perturbation_does_not_change_t0():
    dates = [20260923, 20260924]
    event = XrxdEvent("SEC-A", 20260928, cash_dividend_per_10=Decimal("1.00"))
    changed_future_event = XrxdEvent("SEC-A", 20260928, cash_dividend_per_10=Decimal("9.00"))
    baseline = build_affine_factors(dates, [event])
    perturbed = build_affine_factors(dates, [changed_future_event])
    assert baseline[20260924] == perturbed[20260924]


def test_historical_adjusted_lineage_never_claims_pit_without_snapshot():
    assert historical_adjusted_lineage(None, "2024-01-01T00:00:00Z") == "DIAGNOSTIC_NON_PIT"


def test_go_forward_gbbq_snapshot_hash_bound():
    manifest = {"files": {"gbbq": {"sha256": "a"}, "gbbq.map": {"sha256": "b"}}}
    assert validate_snapshot_hash_binding(manifest, {"gbbq": "a", "gbbq.map": "b"})
    assert not validate_snapshot_hash_binding(manifest, {"gbbq": "a", "gbbq.map": "c"})


def test_price_limit_registry_uses_effective_dated_authority_at_2026_boundary():
    root = Path(__file__).resolve().parents[2]
    contract = json.loads((root / "config/v4_02_price_limit_rules_v1.json").read_text(encoding="utf-8"))
    service = LimitStateService(contract["rules"])
    assert service.resolve("2026-07-05", "SH", "MAIN", "RISK_WARNING").limit_ratio == Decimal("0.05")
    assert service.resolve("2026-07-06", "SH", "MAIN", "RISK_WARNING").limit_ratio == Decimal("0.10")
    assert service.resolve("2026-07-05", "SZ", "MAIN", "RISK_WARNING").limit_ratio == Decimal("0.05")
    assert service.resolve("2026-07-06", "SZ", "MAIN", "RISK_WARNING").limit_ratio == Decimal("0.10")
    assert service.resolve("2026-07-06", "SZ", "GROWTH", "RISK_WARNING").limit_ratio == Decimal("0.20")


def test_xrxd_reference_uses_adjustment_transform_and_tick_rounding():
    event = XrxdEvent("SEC-A", 20260626, cash_dividend_per_10=Decimal("1.00"), bonus_transfer_per_10=Decimal("2.00"))
    assert ex_right_reference_price("10.00", [event]) == Decimal("8.25")
