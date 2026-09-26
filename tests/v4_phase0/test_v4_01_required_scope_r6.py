from workbench_analysis.v4_01_required_scope import (
    REQUIRED_BOARD_KEYS,
    classify_bse_scope,
    classify_unknown_roster_code,
    required_scope_digest,
    required_board,
    required_identity_missing_from_roster,
    required_scope_counts,
    roster_suspicion_flags,
    split_roster_scope,
    suspicious_day_accepted,
    validate_fresh_roster_runs,
)


def test_roster_exact_page_multiple_requires_revalidation():
    assert "SUSPICIOUS_PROVIDER_PAGE_BOUNDARY" in roster_suspicion_flags(
        row_count=4000, prior_row_count=5600, required_lifecycle_count=5100
    )


def test_roster_large_day_over_day_drop_requires_revalidation():
    assert "LARGE_DAY_OVER_DAY_DROP" in roster_suspicion_flags(
        row_count=5100, prior_row_count=5650, required_lifecycle_count=5100
    )


def test_roster_lifecycle_scale_gap_requires_revalidation():
    assert "LARGE_REQUIRED_LIFECYCLE_COUNT_GAP" in roster_suspicion_flags(
        row_count=2000, prior_row_count=None, required_lifecycle_count=5100
    )


def test_fresh_session_repeat_digest_must_match():
    first = {"row_count": 7413, "codes_sha256": "a", "duplicate_count": 0}
    second = {"row_count": 7413, "codes_sha256": "a", "duplicate_count": 0}
    assert validate_fresh_roster_runs(first, second) == []
    second["codes_sha256"] = "b"
    assert "FRESH_SESSION_DIGEST_MISMATCH" in validate_fresh_roster_runs(first, second)


def test_roster_traded_required_scope_subset_must_be_present():
    from workbench_analysis.v4_01_required_scope import missing_traded_required_codes
    assert missing_traded_required_codes({"SH.600000", "SZ.300001"}, {"SH.600000"}) == {"sz.300001"}


def test_bse_degraded_does_not_block_required_scope():
    assert classify_bse_scope(101, False)["status"] == "DEGRADED_BSE"
    assert len(REQUIRED_BOARD_KEYS) == 4


def test_required_scope_identity_uses_type_exchange_and_board():
    assert required_board({"security_type": "A_STOCK", "exchange": "SZ", "board": "CHINEXT"}) == "CHINEXT"
    assert required_board({"security_type": "FUND", "exchange": "SZ", "board": "CHINEXT"}) is None
    assert required_board({"security_type": "A_STOCK", "exchange": "SZ", "board": "BEIJING"}) is None


def test_main_board_unresolved_blocks():
    identity = {"source_security_key": "SH.600000", "security_type": "A_STOCK", "exchange": "SH",
                "board": "MAIN", "security_id": None, "list_date": "1999-11-10", "source_revision_id": "r1"}
    assert required_scope_counts([identity])["SH_MAIN"]["unresolved_identity_rows"] == 1


def test_sz_main_unresolved_blocks():
    identity = {"source_security_key": "SZ.000001", "security_type": "A_STOCK", "exchange": "SZ",
                "board": "MAIN", "security_id": None, "list_date": "1991-04-03", "source_revision_id": "r1"}
    assert required_scope_counts([identity])["SZ_MAIN"]["unresolved_identity_rows"] == 1


def test_chinext_unresolved_blocks():
    identity = {"source_security_key": "SZ.300001", "security_type": "A_STOCK", "exchange": "SZ",
                "board": "CHINEXT", "security_id": None, "list_date": "2009-10-30", "source_revision_id": "r1"}
    assert required_scope_counts([identity])["CHINEXT"]["unresolved_identity_rows"] == 1


def test_star_unresolved_blocks():
    identity = {"source_security_key": "SH.688001", "security_type": "A_STOCK", "exchange": "SH",
                "board": "STAR", "security_id": None, "list_date": "2019-07-22", "source_revision_id": "r1"}
    assert required_scope_counts([identity])["STAR"]["unresolved_identity_rows"] == 1


def test_noncore_unresolved_does_not_block_required_a_scope():
    noncore = {"source_security_key": "SH.510300", "security_type": None, "exchange": "SH",
               "board": None, "security_id": None}
    counts = required_scope_counts([noncore])
    assert all(value["unresolved_identity_rows"] == 0 for value in counts.values())
    assert classify_unknown_roster_code("SH.510300") == "OUT_OF_REQUIRED_SCOPE_PENDING_CLASSIFICATION"


def test_unknown_all_stock_security_not_auto_promoted_to_a_stock():
    assert classify_unknown_roster_code("SZ.399001") == "OUT_OF_REQUIRED_SCOPE_PENDING_CLASSIFICATION"


def test_required_universe_uses_accepted_a_stock_identity():
    identities = [{"source_security_key": "SZ.300001", "security_type": "A_STOCK", "exchange": "SZ",
                   "board": "CHINEXT", "security_id": "SEC-1", "list_date": "2009-10-30",
                   "symbol_effective_from": "2009-10-30", "symbol_effective_to": None}]
    assert required_identity_missing_from_roster(identities, "2026-09-24", {"sz.300001"}) == set()


def test_bse_rows_isolated_from_required_universe_digest():
    from workbench_analysis.v4_01_required_scope import split_roster_scope
    core = {"source_security_key": "sh.600000", "security_type": "A_STOCK", "exchange": "SH",
            "board": "MAIN", "security_id": "SEC-1", "list_date": "1999-11-10",
            "symbol_effective_from": "1999-11-10"}
    bse = {"source_security_key": "BJ.920001", "security_type": "A_STOCK", "exchange": "BJ",
           "board": "BEIJING", "security_id": "SEC-BSE", "list_date": "2025-10-09",
           "source_revision_id": "r1", "symbol_effective_from": "2025-10-09"}
    split = split_roster_scope({"SH.600000", "BJ.920001"}, {"sh.600000": core, "bj.920001": bse},
                               "2026-09-24", {})
    assert split["required"] == ["sh.600000"]
    assert split["bse_optional"] == ["bj.920001"]
    assert all(value["security_keys"] == 0 for value in required_scope_counts([bse]).values())


def test_roster_incomplete_day_blocks_final_gate():
    first = {"row_count": 3, "codes_sha256": "a", "duplicate_count": 0}
    second = {"row_count": 3, "codes_sha256": "a", "duplicate_count": 0}
    assert not suspicious_day_accepted(first, second, provider_ok=True, market_crosscheck_ok=True,
                                       missing_lifecycle=set(), missing_traded={"sz.300001"}, unknown_traded=set())


def test_scope_split_keeps_unknown_out_of_required_universe():
    identities = {"sh.600000": {"source_security_key": "SH.600000", "security_type": "A_STOCK",
                                  "exchange": "SH", "board": "MAIN", "symbol_effective_from": "1999-11-10"}}
    split = split_roster_scope({"SH.600000", "SH.999999"}, identities, "2026-09-24", {})
    assert split["required"] == ["sh.600000"]
    assert split["pending"] == ["sh.999999"]


def test_required_scope_digest_excludes_bse_rows():
    core = [{"trade_date": "2026-09-24", "board_scope": "SH_MAIN", "source_security_key": "SH.600000",
             "security_id": "SEC-1"}]
    assert required_scope_digest(core) == required_scope_digest(core.copy())


def test_lifecycle_expected_set_rejects_missing_required_code():
    identities = [{"source_security_key": "SH.600000", "security_type": "A_STOCK", "exchange": "SH",
                   "board": "MAIN", "security_id": "SEC-1", "list_date": "1999-11-10",
                   "symbol_effective_from": "1999-11-10", "symbol_effective_to": None}]
    assert required_identity_missing_from_roster(identities, "2026-09-24", set()) == {"sh.600000"}
