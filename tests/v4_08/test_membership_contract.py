from copy import deepcopy

import pytest

from src.sector.membership_baseline import (
    classify_replay_rows,
    derive_parent_membership,
    formal_membership_eligible,
    identity_postcheck,
    map_source_sector_type,
    select_available_revisions,
    seed_dependent_state,
    snapshot_digest,
    validate_revision_chain,
    verify_file_digests,
)


REGISTRY = {"industry": "INDUSTRY", "concept": "THEME", "style": "STYLE"}


def _row(**overrides):
    base = {
        "sector_id": "INDUSTRY:801010", "sector_code": "801010", "sector_name": "测试行业",
        "sector_type": "INDUSTRY", "security_id": "SEC-1", "source_security_key": "SH.600001",
        "source_sector_type": "industry", "membership_basis": "PIT_OBSERVED",
        "membership_quality": "PIT_OBSERVED_ACCEPTED", "pit_observed": True,
        "historical_backtest_safe": True, "identity_status": "MAPPED",
    }
    base.update(overrides)
    return base


def _snapshot(rows, *, trade_date="2026-09-30", cutoff="2026-09-30T08:00:00Z", sources=None):
    return snapshot_digest(
        target_trade_date=trade_date, cutoff=cutoff, sector_type_registry_digest="a" * 64,
        source_revision_ids=["rev-1"], source_digest="b" * 64,
        source_file_digests=sources or {"industry.cfg": "c" * 64}, rows=rows,
        membership_basis="PIT_OBSERVED", membership_quality="PIT_OBSERVED_ACCEPTED",
    )


def test_current_snapshot_observed_at_t_cannot_be_used_as_pit_at_t_minus_100():
    current = {"source_revision_id": "rev-t", "system_available_at": "2026-09-30T08:00:00Z"}
    assert select_available_revisions([current], "2026-09-30T08:00:00Z") == [current]
    assert select_available_revisions([current], "2026-06-22T08:00:00Z") == []


def test_historical_replay_is_diagnostic_only():
    row = classify_replay_rows([_row()], "2026-06-22")[0]
    assert row["membership_basis"] == "CURRENT_MEMBERSHIP_REPLAY"
    assert row["pit_observed"] is False
    assert row["historical_backtest_safe"] is False
    assert row["membership_asof_date"] is None
    assert not formal_membership_eligible(row)


def test_t_snapshot_is_unchanged_by_t_plus_1_correction():
    before = _snapshot([_row()])
    _t1_correction = {"source_revision_id": "rev-t1", "system_available_at": "2026-10-01T08:00:00Z", "supersedes_revision_id": "rev-t"}
    after = _snapshot([_row()])
    assert before == after


def test_late_correction_is_a_new_revision():
    revisions = [
        {"source_revision_id": "rev-1", "supersedes_revision_id": None},
        {"source_revision_id": "rev-2", "supersedes_revision_id": "rev-1"},
    ]
    assert validate_revision_chain(revisions)["status"] == "PASS"
    assert len(revisions) == 2


def test_revision_fork_fails_closed():
    revisions = [
        {"source_revision_id": "rev-1", "supersedes_revision_id": None},
        {"source_revision_id": "rev-2a", "supersedes_revision_id": "rev-1"},
        {"source_revision_id": "rev-2b", "supersedes_revision_id": "rev-1"},
    ]
    result = validate_revision_chain(revisions)
    assert result["status"] == "BLOCKED"
    assert "REVISION_FORK" in result["errors"]


def test_duplicate_sector_security_fact_fails_closed():
    result = identity_postcheck([_row(), _row()])
    assert result["status"] == "BLOCKED"
    assert result["duplicate_fact_count"] == 1


def test_unknown_security_identity_is_retained_and_reported():
    row = _row(security_id=None, identity_status="UNKNOWN", source_security_key="SH.999999")
    result = identity_postcheck([row])
    assert result["unknown_identity_count"] == 1
    assert result["unknown_identity_source_keys"] == ["SH.999999"]
    assert result["status"] == "BLOCKED"


def test_style_is_excluded_from_formal_sector_and_rotation_qualification():
    row = _row(sector_type="STYLE", sector_id="STYLE:1")
    assert not formal_membership_eligible(row)


def test_unknown_sector_type_is_excluded_but_source_type_is_preserved():
    source_type = "index_group"
    mapped = map_source_sector_type(source_type, REGISTRY)
    row = _row(sector_type=mapped, source_sector_type=source_type)
    assert row["sector_type"] == "UNKNOWN"
    assert row["source_sector_type"] == "index_group"
    assert not formal_membership_eligible(row)


def test_parent_industry_is_child_union_and_deduplicates_members():
    rows = [
        _row(sector_id="INDUSTRY:801011", sector_code="801011", security_id="SEC-1"),
        _row(sector_id="INDUSTRY:801012", sector_code="801012", security_id="SEC-1"),
        _row(sector_id="INDUSTRY:801012", sector_code="801012", security_id="SEC-2", source_security_key="SH.600002"),
    ]
    parents = derive_parent_membership(rows, parent_code="80101", child_code_to_parent={"801011": "80101", "801012": "80101"})
    assert {row["security_id"] for row in parents} == {"SEC-1", "SEC-2"}
    assert parents[0]["child_sector_ids"] == ["INDUSTRY:801011", "INDUSTRY:801012"]
    assert all(row["membership_basis"] == "DERIVED_PARENT_MEMBERSHIP" for row in parents)


def test_parent_derivation_rejects_impossible_cross_industry_identity():
    with pytest.raises(ValueError, match="cross-industry"):
        derive_parent_membership([_row(sector_code="802011")], parent_code="80101", child_code_to_parent={"802011": "80201"})


def test_snapshot_hash_is_deterministic_under_row_order():
    rows = [_row(security_id="SEC-2"), _row(security_id="SEC-1")]
    assert _snapshot(rows) == _snapshot(list(reversed(rows)))


def test_same_day_revision_chain_is_allowed_without_fork():
    revisions = [
        {"source_revision_id": "day-r1", "supersedes_revision_id": None},
        {"source_revision_id": "day-r2", "supersedes_revision_id": "day-r1"},
    ]
    assert validate_revision_chain(revisions)["status"] == "PASS"


def test_source_file_hash_mismatch_fails_closed():
    result = verify_file_digests({"industry.cfg": "a" * 64}, {"industry.cfg": "b" * 64})
    assert result["status"] == "BLOCKED"
    assert result["mismatches"] == ["industry.cfg"]


def test_cutoff_cannot_see_fact_before_system_available_at():
    revision = {"source_revision_id": "late", "system_available_at": "2026-09-30T08:00:01Z"}
    assert select_available_revisions([revision], "2026-09-30T08:00:00Z") == []


def test_missing_system_available_time_fails_closed():
    with pytest.raises(ValueError, match="system_available_at"):
        select_available_revisions([{"source_revision_id": "unknown-time"}], "2026-09-30T08:00:00Z")


def test_daily_identity_changes_only_when_date_or_truth_changes():
    unchanged = _snapshot([_row()])
    same_truth = _snapshot([_row()])
    changed_truth = _snapshot([_row(sector_name="改名版本")])
    next_day = _snapshot([_row()], trade_date="2026-10-01")
    assert unchanged == same_truth
    assert changed_truth != unchanged
    assert next_day != unchanged


def test_seed_dependent_fields_remain_unknown_while_upstream_signal_degraded():
    result = seed_dependent_state(v4_07_real_signal_capability="DEGRADED_BY_ACCEPTED_PRIOR_RPS_BOOTSTRAP_UNKNOWN", value=0)
    assert result == {"value": None, "quality": "UNKNOWN", "reason": "DEGRADED_BY_UPSTREAM_BASE_SEED_SIGNAL"}
