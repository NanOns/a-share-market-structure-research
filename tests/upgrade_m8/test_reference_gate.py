import json

import pandas as pd
import pytest

from workbench_analysis.reference_capability import normalize_reference_rows
from workbench_analysis.reference_gate import ReferenceGateError, build_capability_gate, json_report


def _references():
    return normalize_reference_rows(
        pd.DataFrame(
            [
                {"security_id": "SH.600001", "trade_date": "2026-09-08", "quote_prev_close": 10, "float_shares": 1000, "shares_unit": "SHARES", "shares_basis": "FLOAT_SHARES", "source_ref": "local:1", "ex_rights_reference_unknown": False},
                {"security_id": "SH.600002", "trade_date": "2026-09-08", "quote_prev_close": 10, "float_shares": 1000, "shares_unit": "SHARES", "shares_basis": "APPROXIMATE", "source_ref": "local:2", "ex_rights_reference_unknown": False},
                {"security_id": "SH.600003", "trade_date": "2026-09-08", "quote_prev_close": None, "float_shares": None, "source_ref": None},
            ]
        )
    )


def test_gate_separates_exact_approximate_unknown_and_requires_verified_rule():
    result = build_capability_gate(
        _references(),
        limit_results=[
            {"security_id": "SH.600001", "trade_date": "2026-09-08", "limit_state": "NOT_LIMIT", "rule_verified": True},
            {"security_id": "SH.600002", "trade_date": "2026-09-08", "limit_state": "NOT_LIMIT", "rule_verified": False},
        ],
    )
    items = result["items"].set_index("security_id")
    assert items.loc["SH.600001", "reference_capability"] == "EXACT" and bool(items.loc["SH.600001", "available"]) is True
    assert items.loc["SH.600002", "reference_capability"] == "APPROXIMATE" and bool(items.loc["SH.600002", "available"]) is False
    assert items.loc["SH.600002", "limit_capability"] == "UNKNOWN"
    assert items.loc["SH.600003", "reference_capability"] == "UNKNOWN"
    assert result["summary"].iloc[0][["exact_count", "approximate_count", "unknown_count"]].tolist() == [1, 1, 1]
    assert "RULE_NOT_VERIFIED" in items.loc["SH.600002", "quality_codes"]


def test_gate_is_order_invariant_and_json_report_has_no_nan():
    left = build_capability_gate(_references())
    right = build_capability_gate(_references().sample(frac=1, random_state=4))
    pd.testing.assert_frame_equal(left["items"], right["items"])
    report = json_report(left)
    text = json.dumps(report, ensure_ascii=False, allow_nan=False)
    assert "unverified_is_available" in text and report["policy"]["unverified_is_available"] is False


def test_gate_rejects_duplicate_keys():
    with pytest.raises(ReferenceGateError, match="DUPLICATE"):
        build_capability_gate(pd.concat([_references(), _references().iloc[[0]]], ignore_index=True))


def test_string_false_rule_verification_cannot_open_capability():
    references = pd.DataFrame([{"security_id": "SH.600001", "trade_date": "2026-09-08", "quote_capability": "EXACT", "reference_status": "KNOWN", "reference_basis": "LOCAL_REFERENCE_EXPLICIT", "ex_rights_reference_unknown": False, "shares_capability": "EXACT"}])
    result = build_capability_gate(references, limit_results=[{"security_id": "SH.600001", "trade_date": "2026-09-08", "limit_state": "LIMIT_UP", "rule_verified": "false"}])
    item = result["items"].iloc[0]
    assert item["limit_capability"] == "UNKNOWN" and bool(item["available"]) is False
