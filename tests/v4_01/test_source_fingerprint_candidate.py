from __future__ import annotations

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
