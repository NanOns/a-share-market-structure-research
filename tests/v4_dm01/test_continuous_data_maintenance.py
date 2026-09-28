from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

import pytest

from workbench_analysis.continuous_data_maintenance import (
    adjustment_capability_status,
    adjustment_impact_set,
    append_adjustment_revision,
    choose_tdx_record,
    classify_trading_status,
    cross_component_postcheck,
    idempotency_key,
    identity_delta_events,
    isst_change,
    latest_completed_session,
    lineage_for_bridge_date,
    official_weekday_sessions,
    period_is_mutable,
    period_view_status,
    plan_catch_up,
    require_source_freeze_before_component_build,
    resume_reference_close,
    source_readiness,
    special_phase_increment,
)
from workbench_analysis.daily_data_head import (
    CAPABILITIES,
    build_data_head,
    canonical_digest,
    promote_data_head,
    write_json_atomic,
)
from workbench_analysis.daily_source_freeze import (
    SourceFreezeError,
    build_source_freeze_manifest,
    source_freeze_complete,
    write_source_freeze_atomic,
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _capabilities(status: str = "FULL_PASS") -> dict[str, dict[str, str]]:
    return {name: {"status": status} for name in CAPABILITIES}


def _freeze() -> dict:
    family = {"source_revision": "rev1", "sha256": _sha("source"), "bytes": 4}
    return build_source_freeze_manifest(
        trade_date="2026-09-28",
        tdx_snapshot_identity={**family, "snapshot_id": "tdx-snap-1"},
        changed_tdx_files=[],
        exchange_calendar_revision={**family, "calendar_revision": "calendar-r1"},
        baostock_source_identity={**family, "query_receipt": "query-r1"},
        gbbq_snapshot={**family, "snapshot_id": "gbbq-r1"},
        identity_lifecycle_manifest={**family, "manifest_id": "identity-r1"},
        special_price_phase_manifest={**family, "manifest_id": "phase-r1"},
        observed_at="2026-09-28T07:00:00+08:00",
        ingested_at="2026-09-28T07:01:00+08:00",
        system_available_at="2026-09-28T07:02:00+08:00",
    )


def _head(temp: Path, trade_date: str = "2026-09-24") -> tuple[Path, Path, Path, dict]:
    root = temp / "project"
    root.mkdir(parents=True, exist_ok=True)
    tdx = temp / "tdx"
    tdx.mkdir(exist_ok=True)
    stage, dev, head = root / "STAGE.json", root / "DEV.json", root / "DATA.json"
    stage.write_text('{"stage":"sealed"}\n', encoding="utf-8")
    dev.write_text('{"dev":"frozen"}\n', encoding="utf-8")
    current = {
        "accepted_trade_date": trade_date,
        "manifest_sha256": _sha("accepted"),
    }
    write_json_atomic(head, current, tdx_root=tdx)
    candidate = build_data_head(
        trade_date="2026-09-28",
        source_revision="src-r2",
        canonical_data_revision="data-r2",
        manifest_path="candidate.json",
        manifest_sha256=_sha("candidate"),
        parent_head_sha256=hashlib.sha256(head.read_bytes()).hexdigest(),
        stage_accepted_head_sha256=hashlib.sha256(stage.read_bytes()).hexdigest(),
        dev_baseline_sha256=hashlib.sha256(dev.read_bytes()).hexdigest(),
        component_permissions=_capabilities(),
    )
    return head, stage, dev, {"tdx": tdx, "candidate": candidate, "current": current}


def test_no_new_session_is_noop() -> None:
    sessions = ["2026-09-24"]
    target = latest_completed_session(
        sessions, now=datetime.fromisoformat("2026-09-28T07:26:00+08:00")
    )
    plan = plan_catch_up(
        official_sessions=sessions, last_accepted_trade_date="2026-09-24", target_cutoff=target
    )
    assert plan["status"] == "READY"
    assert plan["promotable_sessions"] == []


def test_one_session_increment() -> None:
    plan = plan_catch_up(
        official_sessions=["2026-09-24", "2026-09-28"],
        last_accepted_trade_date="2026-09-24",
        target_cutoff="2026-09-28",
    )
    assert plan["promotable_sessions"] == ["2026-09-28"]


def test_multi_session_catchup_is_strictly_sequential() -> None:
    plan = plan_catch_up(
        official_sessions=["2026-09-24", "2026-09-25", "2026-09-28", "2026-09-29"],
        last_accepted_trade_date="2026-09-24",
        target_cutoff="2026-09-29",
    )
    assert plan["promotable_sessions"] == ["2026-09-25", "2026-09-28", "2026-09-29"]
    assert plan["strictly_sequential"] is True


def test_weekend_holiday_not_inferred_from_missing_bars() -> None:
    sessions = official_weekday_sessions(
        "2026-09-24", "2026-09-28",
        official_closures=[{"start": "2026-09-25", "end": "2026-09-27"}],
        source_revision="official-notice-r1",
        source_sha256=_sha("official"),
    )
    assert sessions == ["2026-09-24", "2026-09-28"]


def test_stale_tdx_blocks_required_raw_increment() -> None:
    result = source_readiness(
        trade_date="2026-09-28", tdx_available_through="2026-09-24",
        accepted_package_available_through="2026-09-24", calendar_session_confirmed=True,
    )
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "SOURCE_NOT_READY"


def test_local_tdx_wins_overlap_conflict() -> None:
    result = choose_tdx_record(
        local_record={"sha256": "local"}, accepted_package_record={"sha256": "package"}
    )
    assert result["status"] == "LOCAL_WINS_CONFLICT"
    assert result["selected"]["sha256"] == "local"
    assert result["conflict_receipt_required"] is True


def test_same_source_digest_is_idempotent() -> None:
    left = idempotency_key("2026-09-28", _sha("source"), _sha("contract"))
    right = idempotency_key("2026-09-28", _sha("source"), _sha("contract"))
    assert left == right


def test_source_revision_creates_new_revision() -> None:
    old = idempotency_key("2026-09-28", _sha("source-a"), _sha("contract"))
    new = idempotency_key("2026-09-28", _sha("source-b"), _sha("contract"))
    assert old != new


def test_crash_before_head_swap_keeps_old_head(tmp_path: Path) -> None:
    head, stage, dev, state = _head(tmp_path)
    prior_bytes = head.read_bytes()
    result = promote_data_head(
        head_path=head, candidate_head=state["candidate"],
        candidate_manifest={"status": "CANDIDATE_MANIFEST_READY"},
        source_freeze_pass=False, independent_postcheck_status="PASS",
        stage_head_path=stage, dev_baseline_path=dev, tdx_root=state["tdx"],
    )
    assert result["status"] == "BLOCKED"
    assert head.read_bytes() == prior_bytes


def test_new_listing_identity_delta() -> None:
    events = identity_delta_events(
        previous_active={"SH.600001": {"security_id": "SEC-A"}},
        current_active={"SH.600001": {"security_id": "SEC-A"}, "SH.600002": {"security_id": "SEC-B"}},
    )
    assert any(row["event_type"] == "NEW_LISTING_CANDIDATE" for row in events)


def test_delisting_identity_delta() -> None:
    events = identity_delta_events(
        previous_active={"SH.600001": {"security_id": "SEC-A"}},
        current_active={},
    )
    assert events == [{"event_type": "DELISTING_CANDIDATE", "source_security_key": "SH.600001",
                       "security_id": "SEC-A"}]


def test_nonoverlap_code_change_daily_candidate() -> None:
    events = identity_delta_events(
        previous_active={"SZ.000001": {"security_id": "SEC-A", "exchange": "SZ"}},
        current_active={"SZ.000002": {"security_id": "SEC-B", "exchange": "SZ"}},
    )
    assert any(row["event_type"] == "CODE_CHANGE_CANDIDATE" and row["shared_bar_sessions"] == 0
               for row in events)


def test_suspension_does_not_mean_data_gap() -> None:
    result = classify_trading_status(
        calendar_is_session=True, lifecycle_active=True, actual_bar_present=False,
        dated_provider_tradestatus="0",
    )
    assert result["status"] == "SUSPENDED"


def test_resume_carries_previous_official_close() -> None:
    suspended = classify_trading_status(
        calendar_is_session=True, lifecycle_active=True, actual_bar_present=False,
        dated_provider_tradestatus="0", previous_official_close=12.34,
    )
    resumed = classify_trading_status(
        calendar_is_session=True, lifecycle_active=True, actual_bar_present=True,
        dated_provider_tradestatus="1", previous_official_close=12.34,
    )
    assert suspended["close_carry"] == 12.34
    assert resumed["status"] == "ACTUAL_TRADED"
    assert resume_reference_close(12.34, actual_bar_present=True) == 12.34


def test_isst_change() -> None:
    assert isst_change("0", "1") == {
        "status": "KNOWN", "changed": True, "previous_is_st": "0", "current_is_st": "1"
    }


def test_gbbq_snapshot_frozen_before_adjustment_build() -> None:
    manifest = _freeze()
    assert source_freeze_complete(manifest)
    require_source_freeze_before_component_build(manifest)
    assert manifest["source_families"]["GBBQ"]["snapshot_id"] == "gbbq-r1"


def test_corporate_action_recomputes_only_affected_adjusted_history() -> None:
    impact = adjustment_impact_set(
        {"SEC-A": [{"trade_date": "2026-09-24", "close": 10}],
         "SEC-B": [{"trade_date": "2026-09-24", "close": 20}]},
        {"SEC-A": [{"trade_date": "2026-09-24", "close": 5}],
         "SEC-B": [{"trade_date": "2026-09-24", "close": 20}]},
        source_snapshot_id="gbbq-r2", old_adjustment_revision="adj-r1",
        new_adjustment_revision="adj-r2", reason="corporate_action_revision",
    )
    assert [row["security_id"] for row in impact] == ["SEC-A"]
    assert impact[0]["old_adjustment_revision"] == "adj-r1"
    assert impact[0]["new_adjustment_revision"] == "adj-r2"


def test_unsupported_adjustment_fails_closed() -> None:
    assert adjustment_capability_status(supported=False, rows_ready=False)["status"] == "BLOCKED"


def test_weekly_asof_partial() -> None:
    assert period_view_status(period_last_session="2026-10-02", target_trade_date="2026-09-28") == "AS_OF_PARTIAL"


def test_weekly_closed_on_formal_period_last_session() -> None:
    assert period_view_status(period_last_session="2026-09-28", target_trade_date="2026-09-28") == "CLOSED_ONLY"


def test_monthly_asof_partial() -> None:
    assert period_view_status(period_last_session="2026-09-30", target_trade_date="2026-09-28") == "AS_OF_PARTIAL"


def test_monthly_closed_on_formal_period_last_session() -> None:
    assert period_view_status(period_last_session="2026-09-30", target_trade_date="2026-09-30") == "CLOSED_ONLY"


def test_holiday_shortened_week_closes_on_official_last_session() -> None:
    assert period_view_status(period_last_session="2026-09-24", target_trade_date="2026-09-24") == "CLOSED_ONLY"


def test_special_price_phase_increment() -> None:
    event = {"security_id": "SEC-A", "effective_date": "2026-09-28", "event_type": "IPO"}
    assert special_phase_increment(security_id="SEC-A", trade_date="2026-09-28",
                                   events=[event], evidence_complete=True)["status"] == "KNOWN_EVENT"
    assert special_phase_increment(security_id="SEC-A", trade_date="2026-09-28",
                                   events=[], evidence_complete=False)["status"] == "UNKNOWN_SPECIAL_PHASE"


def test_bridge_date_not_claimed_pit_observed_without_snapshot() -> None:
    assert lineage_for_bridge_date("2026-09-25", pit_eligible_from="2026-09-28",
                                  frozen_source_set_digest=None) == "DIAGNOSTIC_NON_PIT"


def test_pit_eligible_date_uses_frozen_source_set() -> None:
    assert lineage_for_bridge_date("2026-09-28", pit_eligible_from="2026-09-28",
                                  frozen_source_set_digest=_sha("freeze")) == "PIT_OBSERVED"


def test_data_head_move_does_not_move_dev_baseline(tmp_path: Path) -> None:
    head, stage, dev, state = _head(tmp_path)
    dev_before = dev.read_bytes()
    stage_before = stage.read_bytes()
    result = promote_data_head(
        head_path=head, candidate_head=state["candidate"],
        candidate_manifest={"status": "CANDIDATE_MANIFEST_READY"},
        source_freeze_pass=True, independent_postcheck_status="PASS",
        stage_head_path=stage, dev_baseline_path=dev, tdx_root=state["tdx"],
    )
    assert result["status"] == "PROMOTED"
    assert dev.read_bytes() == dev_before
    assert stage.read_bytes() == stage_before


def test_data_head_move_does_not_modify_stage_accepted_head(tmp_path: Path) -> None:
    head, stage, dev, state = _head(tmp_path)
    before = hashlib.sha256(stage.read_bytes()).hexdigest()
    promote_data_head(
        head_path=head, candidate_head=state["candidate"],
        candidate_manifest={"status": "CANDIDATE_MANIFEST_READY"},
        source_freeze_pass=True, independent_postcheck_status="PASS",
        stage_head_path=stage, dev_baseline_path=dev, tdx_root=state["tdx"],
    )
    assert hashlib.sha256(stage.read_bytes()).hexdigest() == before


def test_cross_component_key_consistency() -> None:
    keys = [("SEC-A", "2026-09-28")]
    report = cross_component_postcheck(
        universe_keys=keys, trading_status_keys=keys, isst_keys=keys, price_limit_keys=keys,
        actual_traded_keys=keys, bar_keys=keys, suspended_keys=[], fabricated_zero_return_keys=[],
        adjusted_ready_keys=keys, adjusted_raw_fallback_keys=[], period_max_source_dates=["2026-09-28"],
        head_cutoff="2026-09-28", tdx_root_write_count=0,
    )
    assert report["status"] == "PASS"


def test_atomic_publication_and_rollback(tmp_path: Path) -> None:
    head, stage, dev, state = _head(tmp_path)
    old_head = json.loads(head.read_text("utf-8"))
    blocked = promote_data_head(
        head_path=head, candidate_head=state["candidate"],
        candidate_manifest={"status": "STAGING"},
        source_freeze_pass=True, independent_postcheck_status="BLOCKED",
        stage_head_path=stage, dev_baseline_path=dev, tdx_root=state["tdx"],
    )
    assert blocked["status"] == "BLOCKED"
    assert json.loads(head.read_text("utf-8")) == old_head
    promoted = promote_data_head(
        head_path=head, candidate_head=state["candidate"],
        candidate_manifest={"status": "CANDIDATE_MANIFEST_READY"},
        source_freeze_pass=True, independent_postcheck_status="PASS",
        stage_head_path=stage, dev_baseline_path=dev, tdx_root=state["tdx"],
    )
    assert promoted["status"] == "PROMOTED"
    assert not list(head.parent.glob("DATA.json.*.tmp"))


def test_daily_head_idempotent_noop(tmp_path: Path) -> None:
    head, stage, dev, state = _head(tmp_path)
    current = dict(state["candidate"])
    current["accepted_trade_date"] = "2026-09-24"
    current["manifest_sha256"] = _sha("accepted")
    head.write_text(json.dumps(current), encoding="utf-8")
    result = promote_data_head(
        head_path=head, candidate_head=current,
        candidate_manifest={"status": "CANDIDATE_MANIFEST_READY"},
        source_freeze_pass=True, independent_postcheck_status="PASS",
        stage_head_path=stage, dev_baseline_path=dev, tdx_root=state["tdx"],
    )
    assert result["status"] == "NOOP_ALREADY_ACCEPTED"


def test_source_freeze_has_all_required_lineage_fields() -> None:
    manifest = _freeze()
    assert source_freeze_complete(manifest)
    assert manifest["tdx_root_write_count"] == 0
    assert manifest["source_families"]["TDX"]["snapshot_id"] == "tdx-snap-1"


def test_source_freeze_requires_each_family_digest() -> None:
    with pytest.raises(SourceFreezeError, match="SOURCE_FREEZE_GBBQ_IDENTITY_INCOMPLETE"):
        build_source_freeze_manifest(
            trade_date="2026-09-28",
            tdx_snapshot_identity={"source_revision": "r", "sha256": _sha("x"), "bytes": 1},
            changed_tdx_files=[], exchange_calendar_revision={"source_revision": "r", "sha256": _sha("x"), "bytes": 1},
            baostock_source_identity={"source_revision": "r", "sha256": _sha("x"), "bytes": 1},
            gbbq_snapshot={"source_revision": "r", "bytes": 1},
            identity_lifecycle_manifest={"source_revision": "r", "sha256": _sha("x"), "bytes": 1},
            special_price_phase_manifest={"source_revision": "r", "sha256": _sha("x"), "bytes": 1},
            observed_at="2026-09-28T07:00:00+08:00", ingested_at="2026-09-28T07:01:00+08:00",
            system_available_at="2026-09-28T07:02:00+08:00",
        )


def test_tdx_root_write_is_rejected_for_receipts(tmp_path: Path) -> None:
    tdx = tmp_path / "tdx"
    tdx.mkdir()
    manifest = _freeze()
    with pytest.raises(SourceFreezeError, match="OUTPUT_UNDER_TDX_ROOT_FORBIDDEN"):
        write_source_freeze_atomic(tdx / "receipt.json", manifest, tdx_root=tdx)


def test_closed_period_never_mutates() -> None:
    assert period_is_mutable(is_current_period=True, period_status="AS_OF_PARTIAL")
    assert not period_is_mutable(is_current_period=False, period_status="CLOSED_ONLY_READY")


def test_promotion_rejects_blocked_component() -> None:
    with pytest.raises(ValueError, match="CAPABILITY_BLOCKED:PRICE_LIMIT"):
        build_data_head(
            trade_date="2026-09-28", source_revision="r2", canonical_data_revision="c2",
            manifest_path="m.json", manifest_sha256=_sha("m"), parent_head_sha256=None,
            stage_accepted_head_sha256=_sha("stage"), dev_baseline_sha256=_sha("dev"),
            component_permissions={**_capabilities(), "PRICE_LIMIT": {"status": "BLOCKED"}},
        )


def test_adjustment_revision_is_append_only() -> None:
    old = [{"security_id": "SEC-A", "revision_id": "adj-r1", "digest": _sha("old")}]
    new = append_adjustment_revision(old, {"security_id": "SEC-A", "revision_id": "adj-r2", "digest": _sha("new")})
    assert len(new) == 2
    assert old[0].get("superseded_by") is None
    assert new[0]["superseded_by"] == "adj-r2"


def test_actual_traded_requires_real_bar_not_synthetic_zero() -> None:
    report = cross_component_postcheck(
        universe_keys=[("SEC-A", "2026-09-28")],
        trading_status_keys=[("SEC-A", "2026-09-28")], isst_keys=[("SEC-A", "2026-09-28")],
        price_limit_keys=[("SEC-A", "2026-09-28")], actual_traded_keys=[("SEC-A", "2026-09-28")],
        bar_keys=[], suspended_keys=[], fabricated_zero_return_keys=[],
        adjusted_ready_keys=[], adjusted_raw_fallback_keys=[], period_max_source_dates=[],
        head_cutoff="2026-09-28", tdx_root_write_count=0,
    )
    assert report["checks"]["actual_traded_has_bar"] == "BLOCKED"
