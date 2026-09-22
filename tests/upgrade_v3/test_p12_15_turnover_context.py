from workbench_analysis.turnover_context_v3_3 import ALGORITHM_CONTRACT_ID, build_turnover_context


def candidate(i, *, tier_shape="strong", rank_status="QUALIFIED_UNRANKED"):
    clv = .82 if tier_shape == "strong" else .62
    return {
        "security_id": f"SZ.{i:06d}", "primary_category": "LAUNCH_CONFIRM",
        "selection_mode": "INDEPENDENT", "rank_status": rank_status,
        "category_rank": 7 if rank_status == "SCORED" else None,
        "clv": clv, "break_margin_close20": .016 if tier_shape == "strong" else .003,
        "amr20_mean_prior": 1.4, "intraday_reject_high20": False,
        "factor_evidence": {"clv": clv, "break_margin_close20": .016 if tier_shape == "strong" else .003,
                            "amr20_mean_prior": 1.4, "intraday_reject_high20": False},
        "scanner_evidence": {"launch": {"eligible": True}},
    }


def evidence(i, rate, **overrides):
    base = {
        "security_id": f"SZ.{i:06d}", "capability_status": "BOUND", "turnover_rate": rate,
        "turnover_basis": "FLOAT_SHARE", "basis_verification": "VERIFIED",
        "session_binding_status": "SESSION_VERIFIED", "source_id": "TENCENT_QUOTES_LATEST",
        "source_contract_id": "TENCENT_V1", "field_map_version": "MAP_V1",
    }
    return {**base, **overrides}


def test_mid_distribution_ties_and_five_row_gate():
    result = build_turnover_context([candidate(i) for i in range(5)], [evidence(i, .01 + i * .01) for i in range(5)])
    assert result["algorithm_contract_id"] == ALGORITHM_CONTRACT_ID
    assert result["layer_status"] == "AVAILABLE"
    assert [row["turnover_activity_percentile"] for row in result["items"]] == [.1, .3, .5, .7, .9]
    tied = build_turnover_context([candidate(i) for i in range(5)], [evidence(i, .02) for i in range(5)])
    assert {row["turnover_activity_percentile"] for row in tied["items"]} == {.5}
    assert {row["turnover_activity_band"] for row in tied["items"]} == {"NORMAL"}


def test_small_group_and_unverified_tencent_basis_fail_closed():
    small = build_turnover_context([candidate(i) for i in range(4)], [evidence(i, .01 + i * .01) for i in range(4)])
    assert small["layer_status"] == "AVAILABLE"
    assert all(row["turnover_activity_band"] is None for row in small["items"])
    legacy = [evidence(i, .01 + i * .01, basis_verification="DECLARED_ONLY", session_binding_status="FINGERPRINT_ONLY") for i in range(5)]
    degraded = build_turnover_context([candidate(i) for i in range(5)], legacy)
    assert degraded["layer_status"] == "BYPASSED"
    assert degraded["coverage"] == {"candidate_n": 5, "fact_n": 5, "comparable_n": 0, "fact_coverage": 1.0, "semantic_coverage": 0.0}
    assert all(row["turnover_rate"] is not None and row["turnover_priority_tier"] == "T2" for row in degraded["items"])


def test_context_matrix_and_missing_slot_locking():
    rows = [candidate(0, tier_shape="marginal"), candidate(1), candidate(2), candidate(3), candidate(4), candidate(5)]
    # Original ready tiers are T3, missing, T1, T2, T1. The missing row stays at slot 2.
    source = [evidence(0, .09), evidence(2, .07), evidence(3, .01), evidence(4, .05), evidence(5, .08)]
    source.append(evidence(1, .03, capability_status="SOURCE_FAILED", turnover_rate=None))
    result = build_turnover_context(rows, source, params={"global_semantic_coverage_min": .8, "group_coverage_min": .7})
    by_id = {row["security_id"]: row for row in result["items"]}
    assert by_id["SZ.000000"]["turnover_priority_tier"] == "T3"
    assert by_id["SZ.000001"]["enhanced_display_order"] == 2
    assert by_id["SZ.000001"]["position_policy"] == "LOCKED"
    assert by_id["SZ.000002"]["turnover_priority_tier"] == "T1"
    assert by_id["SZ.000003"]["turnover_priority_tier"] == "T2"


def test_scored_rank_and_core_projection_are_unchanged():
    rows = [candidate(i, rank_status="SCORED") for i in range(5)]
    result = build_turnover_context(rows, [evidence(i, .01 + i * .01) for i in range(5)])
    assert all(row["category_rank"] == 7 and row["turnover_enhanced_rank"] is None for row in result["items"])


def test_out_of_scope_and_conflicting_evidence_do_not_affect_distribution():
    rows = [candidate(i) for i in range(5)]
    source = [evidence(i, .01 + i * .01) for i in range(5)] + [evidence(99, .99)]
    assert build_turnover_context(rows, source)["items"][-1]["turnover_activity_percentile"] == .9
    source.append(evidence(4, .8))
    conflict = build_turnover_context(rows, source)
    assert conflict["coverage"]["comparable_n"] == 4
    assert "EVIDENCE_CONFLICT" in conflict["items"][-1]["turnover_reason_codes"]
