from __future__ import annotations

from workbench_service.universe import (
    A_SHARE_RE,
    CONTRACT_ID,
    classify_security_id,
    is_a_share_security_id,
    summarize_universe,
)


def test_hushenbei_prefixes_are_one_shared_a_share_scope() -> None:
    for security_id in ("SH.600000", "SZ.000001", "SZ.300750", "SZ.302132", "BJ.400001", "BJ.830001", "BJ.920000"):
        decision = classify_security_id(security_id, {"status": "LISTED"})
        assert decision.classification == "A_STOCK"
        assert decision.display_eligible is True
        assert decision.quote_eligible is True
        assert decision.structure_eligible is True
        assert is_a_share_security_id(security_id)
        assert A_SHARE_RE.fullmatch(security_id)


def test_b_share_and_new_third_board_are_displayable_but_out_of_scope() -> None:
    b_share = classify_security_id("SH.900901")
    third_board = classify_security_id("NQ.430001")
    assert (b_share.classification, b_share.exclusion_reason) == ("B_STOCK", "OUT_OF_SCOPE_B_STOCK")
    assert (third_board.classification, third_board.exclusion_reason) == (
        "NEW_THIRD_BOARD",
        "OUT_OF_SCOPE_NEW_THIRD_BOARD",
    )
    assert b_share.display_eligible and third_board.display_eligible
    assert not b_share.quote_eligible and not third_board.structure_eligible
    assert not is_a_share_security_id("SH.900901")


def test_unknown_status_is_not_delisted() -> None:
    decision = classify_security_id("SZ.000001", {"status": "UNKNOWN"})
    assert decision.classification == "A_STOCK"
    assert decision.classification != "DELISTED"
    assert decision.display_eligible and decision.quote_eligible
    assert not decision.structure_eligible
    assert decision.exclusion_reason == "STATUS_UNKNOWN_FOR_STRUCTURE"
    missing = classify_security_id("SH.600000")
    assert missing.classification == "A_STOCK"
    assert missing.display_eligible and not missing.structure_eligible


def test_identity_mismatch_cannot_promote_an_id() -> None:
    decision = classify_security_id("BJ.920000", {"market": "SH", "security_type": "A_STOCK"})
    assert decision.classification == "UNKNOWN"
    assert decision.exclusion_reason == "IDENTITY_MARKET_MISMATCH"
    assert not decision.quote_eligible and not decision.structure_eligible


def test_summary_keeps_three_eligibility_denominators_explainable() -> None:
    result = summarize_universe(
        [
            {"security_id": "SH.600000", "status": "LISTED"},
            {"security_id": "SH.900901"},
            {"security_id": "NQ.430001"},
            {"security_id": "SZ.000001", "status": "UNKNOWN"},
        ],
        quote_valid_ids={"SH.600000", "SZ.000001"},
    )
    assert result["contract_id"] == CONTRACT_ID
    assert result["display_count"] == 4
    assert result["quote_valid_count"] == 2
    assert result["structure_eligible_count"] == 1
    assert result["excluded_by_reason"]["quote"]["OUT_OF_SCOPE_B_STOCK"] == 1
    assert result["excluded_by_reason"]["structure"]["OUT_OF_SCOPE_NEW_THIRD_BOARD"] == 1
    assert result["excluded_by_reason"]["structure"]["STATUS_UNKNOWN_FOR_STRUCTURE"] == 1
