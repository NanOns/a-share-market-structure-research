from __future__ import annotations

from datetime import date, timedelta
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from v4_01.source_fingerprint_candidate import analyze_source_fingerprint  # noqa: E402


def _diagnostic(path: str) -> dict:
    payload = gzip.decompress((ROOT / path).read_bytes())
    return json.loads(payload.decode("utf-8"))


def _contract() -> dict:
    return json.loads(
        (ROOT / "config/v4_01_source_fingerprint_candidate_v1.json").read_text(encoding="utf-8")
    )


def _synthetic_report(active_days: int = 100, tdx_volume_mismatches: int = 0) -> dict:
    old_code, new_code = "SZ.300114", "SZ.302132"
    dates = []
    day = date(2025, 2, 14)
    while len(dates) < active_days:
        if day.weekday() < 5:
            dates.append(day.isoformat())
        day -= timedelta(days=1)
    dates.reverse()

    def history_rows(code: str) -> list[dict[str, str]]:
        rows = []
        for trade_date in dates:
            rows.append({
                "date": trade_date,
                "code": code.lower(),
                "open": "10",
                "high": "11",
                "low": "9",
                "close": "10",
                "preclose": "9.5",
                "volume": "1000",
                "amount": "100000",
                "tradestatus": "1",
                "isST": "0",
            })
        return rows

    return {
        "inputs": {
            "old_code": old_code,
            "new_code": new_code,
            "effective_date": "2025-02-17",
            "previous_session": "2025-02-14",
        },
        "tdx": {
            "files": {
                old_code: {"exists": True, "last_date": "2025-02-14"},
                new_code: {"exists": True, "first_date": "2010-08-27"},
            },
            "overlap": {
                "overlap_session_count": 20,
                "mismatch_field_counts": {"volume": tdx_volume_mismatches},
            },
            "current_security_master": {"securities": {}},
        },
        "baostock": {
            "query_failures": [],
            "long_history": {
                old_code.lower(): {"metadata": {"error_code": "0"}, "raw_rows": history_rows(old_code)},
                new_code.lower(): {"metadata": {"error_code": "0"}, "raw_rows": history_rows(new_code)},
            },
            "window_history": {
                old_code.lower(): {"raw_rows": []},
                new_code.lower(): {"raw_rows": []},
            },
            "roster_matrix": {},
            "stock_basic_metadata_continuity": {},
        },
    }


def test_blind_sample_predictions_match_frozen_candidate_study() -> None:
    contract = json.loads((ROOT / "config/v4_01_source_fingerprint_candidate_v1.json").read_text(encoding="utf-8"))
    cases = json.loads((ROOT / "config/v4_01_source_fingerprint_blind_cases_v1.json").read_text(encoding="utf-8"))["cases"]
    predictions = {
        item["case_id"]: analyze_source_fingerprint(_diagnostic(item["diagnostic_report"]), contract)
        for item in cases
    }

    assert predictions["BLIND-01"]["disposition"] == "STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT_CANDIDATE"
    assert predictions["BLIND-02"]["disposition"] == "STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT_CANDIDATE"
    assert predictions["BLIND-03"]["disposition"] == "NO_STRONG_ALIAS_FINGERPRINT_IN_SAMPLE"
    assert predictions["BLIND-04"]["disposition"] == "NO_STRONG_ALIAS_FINGERPRINT_IN_SAMPLE"
    assert all(not item["candidate_auto_link_allowed"] for item in predictions.values())
    assert all(not item["production_identity_mutation_authorized"] for item in predictions.values())


def test_reserved_bytes_and_identical_dual_bar_do_not_veto_candidate() -> None:
    contract = json.loads((ROOT / "config/v4_01_source_fingerprint_candidate_v1.json").read_text(encoding="utf-8"))
    report = _diagnostic("reports/v4_01/V4_01_CODE_CHANGE_SOURCE_FINGERPRINT_300114_302132_R1.json.gz")
    result = analyze_source_fingerprint(report, contract)

    assert result["features"]["tdx_ohlc_amount_exact_on_all_shared_dates"] is True
    assert result["features"]["tdx_volume_exact_ratio"] > 0.95
    assert result["features"]["duplicate_identical_bar_days"] == ["2025-02-14"]
    assert result["features"]["substantive_dual_trade_days"] == []
    assert result["disposition"] == "STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT_CANDIDATE"


def test_empty_old_tdx_file_does_not_count_as_a_full_prefix() -> None:
    from scripts.diagnose_v4_01_code_change_source_fingerprint import tdx_overlap

    old = {"records": [], "by_date": {}}
    new_record = {
        "trade_date": "2020-01-02",
        "_raw": b"new record",
        "open": 1,
        "high": 1,
        "low": 1,
        "close": 1,
        "amount": 1,
        "volume": 1,
        "reserved": 0,
    }
    new = {"records": [new_record], "by_date": {"2020-01-02": new_record}}

    assert tdx_overlap(old, new)["old_history_equals_full_new_prefix"] is False


def test_f6_identical_alias_bars_are_not_substantive_dual_trading() -> None:
    from scripts.diagnose_v4_01_code_change_source_fingerprint import f6_actual_trading_signals

    duplicate = [{"trade_date": "2025-02-14"}]
    signals = f6_actual_trading_signals([], duplicate)

    assert signals["F6_no_substantive_dual_actual_trading"] is True
    assert signals["F6_identical_provider_alias_bar_dates"] == ["2025-02-14"]
    assert "F6_no_overlapping_dual_actual_trading" not in signals
    assert f6_actual_trading_signals(duplicate, [])[
        "F6_no_substantive_dual_actual_trading"
    ] is False


def test_frozen_v1_thresholds_include_exact_095_and_099_boundaries() -> None:
    contract = _contract()

    at_boundaries = analyze_source_fingerprint(_synthetic_report(tdx_volume_mismatches=1), contract)
    assert at_boundaries["features"]["tdx_volume_exact_ratio"] == 0.95
    assert at_boundaries["features"]["baostock_active_exact_ratio"] == 1.0
    assert at_boundaries["disposition"] == "STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT_CANDIDATE"

    bao_at_boundary = _synthetic_report()
    new_rows = bao_at_boundary["baostock"]["long_history"]["sz.302132"]["raw_rows"]
    new_rows[0]["amount"] = "100001"
    at_099 = analyze_source_fingerprint(bao_at_boundary, contract)
    assert at_099["features"]["baostock_active_exact_ratio"] == 0.99
    assert at_099["disposition"] == "STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT_CANDIDATE"


def test_frozen_v1_thresholds_reject_values_below_095_and_099() -> None:
    contract = _contract()

    below_volume = analyze_source_fingerprint(
        _synthetic_report(tdx_volume_mismatches=2), contract
    )
    assert below_volume["features"]["tdx_volume_exact_ratio"] == 0.9
    assert below_volume["disposition"] != "STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT_CANDIDATE"

    below_baostock = _synthetic_report()
    new_rows = below_baostock["baostock"]["long_history"]["sz.302132"]["raw_rows"]
    new_rows[0]["amount"] = "100001"
    new_rows[1]["amount"] = "100001"
    at_098 = analyze_source_fingerprint(below_baostock, contract)
    assert at_098["features"]["baostock_active_exact_ratio"] == 0.98
    assert at_098["disposition"] != "STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT_CANDIDATE"


def test_suspended_blank_and_zero_representation_is_normalized() -> None:
    report = _synthetic_report()
    old_rows = report["baostock"]["long_history"]["sz.300114"]["raw_rows"]
    new_rows = report["baostock"]["long_history"]["sz.302132"]["raw_rows"]
    old_rows[0].update({"tradestatus": "0", "volume": "0", "amount": "0"})
    new_rows[0].update({"tradestatus": "0", "volume": "", "amount": ""})

    result = analyze_source_fingerprint(report, _contract())

    assert result["features"]["baostock_normalized_suspended_representation_days"] == 1
    assert result["disposition"] == "STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT_CANDIDATE"


def test_substantive_dual_actual_bar_difference_fails_closed() -> None:
    report = _synthetic_report()
    old_code, new_code = "sz.300114", "sz.302132"
    old_row = {
        "date": "2025-02-14", "code": old_code, "open": "10", "high": "11",
        "low": "9", "close": "10", "preclose": "9.5", "volume": "1000",
        "amount": "100000", "tradestatus": "1", "isST": "0",
    }
    new_row = {**old_row, "code": new_code, "close": "10.1"}
    report["baostock"]["window_history"][old_code]["raw_rows"] = [old_row]
    report["baostock"]["window_history"][new_code]["raw_rows"] = [new_row]
    report["baostock"]["roster_matrix"] = {
        "2025-02-14": {old_code: True, new_code: True},
    }

    result = analyze_source_fingerprint(report, _contract())

    assert result["features"]["substantive_dual_trade_days"] == ["2025-02-14"]
    assert result["disposition"] == "UNRESOLVED_SUBSTANTIVE_DUAL_TRADING_CONFLICT"
    assert result["candidate_auto_link_allowed"] is False


def test_provider_code_mismatch_duplicate_dates_and_incomplete_query_fail_closed() -> None:
    contract = _contract()

    wrong_code = _synthetic_report()
    wrong_code["baostock"]["long_history"]["sz.302132"]["raw_rows"][0]["code"] = "sz.999999"
    assert analyze_source_fingerprint(wrong_code, contract)["disposition"] == (
        "INCOMPLETE_OR_UNRESOLVED_SOURCE_FINGERPRINT"
    )

    duplicate_date = _synthetic_report()
    old_rows = duplicate_date["baostock"]["long_history"]["sz.300114"]["raw_rows"]
    old_rows.append(dict(old_rows[0]))
    assert analyze_source_fingerprint(duplicate_date, contract)["disposition"] == (
        "INCOMPLETE_OR_UNRESOLVED_SOURCE_FINGERPRINT"
    )

    incomplete = _synthetic_report()
    incomplete["baostock"]["query_failures"] = [{"code": "sz.302132", "error": "incomplete"}]
    assert analyze_source_fingerprint(incomplete, contract)["disposition"] == (
        "INCOMPLETE_OR_UNRESOLVED_SOURCE_FINGERPRINT"
    )


def test_shared_ipo_metadata_alone_does_not_emit_candidate() -> None:
    report = _synthetic_report(active_days=3)
    old_code, new_code = "SZ.300114", "SZ.302132"
    report["tdx"]["files"][old_code]["exists"] = False
    report["tdx"]["files"][new_code]["first_date"] = "2010-08-27"
    report["baostock"]["stock_basic_metadata_continuity"] = {
        "old_ipoDate": "2010-08-27",
        "new_ipoDate": "2010-08-27",
        "old_outDate": "2025-02-17",
        "new_status": "1",
    }

    result = analyze_source_fingerprint(report, _contract())

    assert result["features"]["metadata_lifecycle_continuity_support"] is True
    assert result["features"]["baostock_pre_effective_active_both_days"] == 3
    assert result["disposition"] != "STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT_CANDIDATE"
    assert result["candidate_auto_link_allowed"] is False
