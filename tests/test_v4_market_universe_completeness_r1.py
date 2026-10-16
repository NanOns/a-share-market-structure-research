from copy import deepcopy

import pytest

from workbench_db.v4_market_universe_completeness_r1 import (
    CONTRACT_ID,
    evaluate_market_universe_completeness,
    seal_universe_snapshot,
)


def _row(index, *, status="ACTIVE", exchange="SSE", asset_class="COMMON_STOCK", share_class="A"):
    return {"security_id": f"CN.{index:06d}", "asset_class": asset_class,
            "share_class": share_class, "exchange": exchange, "status": status,
            "source_id": "tdx-security-master-r1"}


def _evaluate(monkeypatch, snapshot, core_rows, *, source_digest="a" * 64, locator_sha=None):
    import workbench_db.v4_daily_source_ingest_r6 as ingest

    monkeypatch.setattr(ingest, "_verify_independent_acceptance_authority", lambda _plan: object())
    plan = {"status": "ACCEPTED", "source_facts": [
        {"source_key": "security_universe", "source_fact_sha256": source_digest,
         "record_locator": {"universe_id": snapshot["universe_id"],
                            "universe_sha256": locator_sha or snapshot["universe_sha256"],
                            "record_count": len(snapshot["securities"])}},
    ]}
    return evaluate_market_universe_completeness(
        trade_date="2026-10-16", universe_snapshot=snapshot,
        core_rows=core_rows, accepted_source_package_plan=plan,
    )


def test_independent_universe_counts_common_a_shares_and_reports_excluded_types(monkeypatch):
    source_digest = "a" * 64
    rows = [
        _row(1), _row(2, status="SUSPENDED"), _row(3, status="NEWLY_LISTED"),
        _row(4, status="CODE_MIGRATION"), _row(5, exchange="BSE"),
        _row(6, share_class="B"), _row(7, asset_class="ETF", share_class="NOT_APPLICABLE"),
        _row(8, asset_class="INDEX", share_class="NOT_APPLICABLE"),
        _row(9, status="DELISTED"),
    ]
    snapshot = seal_universe_snapshot(
        trade_date="2026-10-16", universe_id="TDX_SECURITY_MASTER_T0_R1",
        exchange_scope=["SSE", "SZSE", "BSE"], securities=rows,
        source_fact_sha256=source_digest,
    )
    core = [{"security_id": row["security_id"]} for row in rows[:5]]
    result = _evaluate(monkeypatch, snapshot, core, source_digest=source_digest)
    assert result["contract_id"] == CONTRACT_ID
    assert result["market_universe_completeness_status"] == "PASS"
    assert result["source_internal_integrity_status"] == "NOT_EVALUATED_SEPARATE_CONTRACT"
    assert result["expected_count"] == result["core_count"] == 5
    assert result["coverage_ratio"] == 1.0
    assert result["category_counts"]["suspended"] == 1
    assert result["category_counts"]["newly_listed"] == 1
    assert result["category_counts"]["code_migration"] == 1
    assert result["category_counts"]["ignored_asset_class"] == 3
    assert result["category_counts"]["delisted"] == 1


def test_missing_and_extra_core_security_are_explicit_blockers(monkeypatch):
    source_digest = "b" * 64
    rows = [_row(i) for i in range(1, 6)]
    snapshot = seal_universe_snapshot(trade_date="2026-10-16", universe_id="U1",
                                      exchange_scope=["SSE", "SZSE", "BSE"], securities=rows,
                                      source_fact_sha256=source_digest)
    missing = _evaluate(monkeypatch, snapshot, [{"security_id": r["security_id"]} for r in rows[:-1]], source_digest=source_digest)
    assert missing["status"] == "BLOCKED"
    assert missing["coverage_ratio"] == 0.8
    assert "UNIVERSE_REQUIRED_SECURITIES_MISSING" in missing["reason"]
    assert missing["category_counts"]["missing_core"] == 1
    extra = _evaluate(monkeypatch, snapshot, [{"security_id": r["security_id"]} for r in rows] + [{"security_id": "CN.999999"}], source_digest=source_digest)
    assert extra["status"] == "BLOCKED"
    assert "CORE_SECURITY_OUTSIDE_UNIVERSE" in extra["reason"]
    assert extra["category_counts"]["unexpected_core"] == 1


def test_universe_source_must_be_bound_to_signed_accepted_package(monkeypatch):
    snapshot = seal_universe_snapshot(trade_date="2026-10-16", universe_id="U1",
                                      exchange_scope=["SSE", "SZSE", "BSE"], securities=[_row(1)],
                                      source_fact_sha256="c" * 64)
    result = evaluate_market_universe_completeness(
        trade_date="2026-10-16", universe_snapshot=snapshot,
        core_rows=[{"security_id": "CN.000001"}], accepted_source_package_plan=None,
    )
    assert result["status"] == "BLOCKED"
    assert result["expected_count"] is None
    assert "UNIVERSE_ACCEPTED_SOURCE_PACKAGE_REQUIRED" in result["reason"]

    with pytest.raises(ValueError, match="UNIVERSE_SOURCE_FACT_BINDING_MISMATCH"):
        _evaluate(monkeypatch, snapshot, [{"security_id": "CN.000001"}],
                  source_digest="d" * 64, locator_sha="0" * 64)


def test_5100_same_day_members_are_compared_without_using_core_as_denominator(monkeypatch):
    source_digest = "e" * 64
    rows = [_row(i) for i in range(1, 5101)]
    rows[100] = _row(101, status="SUSPENDED")
    rows[101] = _row(102, status="NEWLY_LISTED")
    snapshot = seal_universe_snapshot(trade_date="2026-10-16", universe_id="TDX_ALL_A_5100",
                                      exchange_scope=["SSE", "SZSE", "BSE"], securities=rows,
                                      source_fact_sha256=source_digest)
    core = [{"security_id": row["security_id"]} for row in rows]
    result = _evaluate(monkeypatch, snapshot, core, source_digest=source_digest)
    assert result["market_universe_completeness_status"] == "PASS"
    assert result["expected_count"] == 5100
    assert result["category_counts"]["suspended"] == 1
    assert result["category_counts"]["newly_listed"] == 1


def test_unknown_identity_and_implicit_exchange_scope_fail_closed(monkeypatch):
    source_digest = "f" * 64
    rows = [_row(1), _row(2, status="UNKNOWN", exchange="UNKNOWN")]
    snapshot = seal_universe_snapshot(trade_date="2026-10-16", universe_id="U1",
                                      exchange_scope=["SSE", "SZSE", "BSE"], securities=rows,
                                      source_fact_sha256=source_digest)
    result = _evaluate(monkeypatch, snapshot, [{"security_id": "CN.000001"}], source_digest=source_digest)
    assert result["status"] == "BLOCKED"
    assert "UNIVERSE_UNKNOWN_IDENTITY_PRESENT" in result["reason"]
    mutated = deepcopy(snapshot)
    mutated["exchange_scope"] = ["SSE", "SZSE"]
    with pytest.raises(ValueError, match="UNIVERSE_EXCHANGE_SCOPE_MUST_BE_EXPLICIT"):
        _evaluate(monkeypatch, mutated, [{"security_id": "CN.000001"}], source_digest=source_digest)
