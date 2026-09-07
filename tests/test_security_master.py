from __future__ import annotations

from tdx.security_master import classify_security, current_a_stock_ids


def test_classification_prefers_tdx_industry_membership() -> None:
    assert classify_security("SH", "600000", {"SH.600000"}) == "A_STOCK"
    assert classify_security("SH", "000001", set()) == "INDEX"
    assert classify_security("SZ", "128001", set()) == "CONVERTIBLE_BOND"


def test_b_shares_are_not_promoted_by_industry_membership() -> None:
    assignments = [
        {"security_id": "SZ.200012", "market": "SZ", "code": "200012"},
        {"security_id": "SH.900901", "market": "SH", "code": "900901"},
        {"security_id": "SZ.302132", "market": "SZ", "code": "302132"},
    ]
    selected = current_a_stock_ids(assignments)
    assert selected == {"SZ.302132"}
    assert classify_security("SZ", "200012", {"SZ.200012"}) == "B_STOCK"
