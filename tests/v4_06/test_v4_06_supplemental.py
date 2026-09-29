from __future__ import annotations

from dataclasses import asdict
from datetime import date, timedelta
import hashlib
import json
import socket
from types import SimpleNamespace

import pytest

from workbench_analysis.baostock_supplemental import BaoStockClient, BaoStockError, NormalizedRow, RequestBudget, normalize_row
from workbench_analysis.v4_06_supplemental import (
    AppendOnlySupplementalStore,
    BoundedHistoryWorker,
    ScheduledRequest,
    SupplementalError,
    SupplementalRow,
    build_supplemental_row,
    compute_turnover_context,
    digest_json,
    enforce_priority_budget,
    evaluate_binding,
    make_manifest,
    map_code_change,
    order_requests,
    provider_code_from_local,
    source_failure_state,
    validate_identity_map,
)


def provider_row(**updates):
    value = {
        "date": "2026-09-01", "code": "sh.600000", "close": "10.0000",
        "volume": "1200", "amount": "12000.00", "turn": "1.25",
        "tradestatus": "1", "isST": "0",
    }
    value.update(updates)
    return value


def accepted_tolerance(**changes):
    value = {
        "contract_id": "BAOSTOCK_TURNOVER_BINDING_TOLERANCE_V1", "version": "1.0.0",
        "source_contract_id": "BAOSTOCK_SUPPLEMENTAL_SOURCE_V1",
        "dataset_id": "BAOSTOCK_TURNOVER_DAILY_V1", "acceptance": "INDEPENDENTLY_ACCEPTED",
        "tolerances": {"close": 0.01, "volume": 0, "amount": 0.01},
        "evidence_digest": "a" * 64, "accepted_by": "fixture-only-test-reviewer",
        "accepted_at_utc": "2026-09-29T00:00:00Z",
        "denominator_semantics_acceptance": {
            "status": "INDEPENDENTLY_ACCEPTED", "basis": "PROVIDER_DEFINED_CIRCULATING_SHARES",
            "evidence_digest": "b" * 64,
            "accepted_by": "fixture-only-test-reviewer", "accepted_at_utc": "2026-09-29T00:00:00Z",
        },
    }
    value.update(changes)
    return value


def local_ref(**changes):
    value = {
        "security_id": "SEC-001", "trade_date": "2026-09-01", "close": 10.0,
        "volume": 1200, "amount": 12000.0, "tradestatus": "1", "isST": "0",
    }
    value.update(changes)
    return value


def history(target_rate=0.25, n=60, *, zeros=False):
    target_day = date(2026, 9, 28)
    prior = []
    for index in range(n):
        day = target_day - timedelta(days=index + 1)
        prior.append({"trade_date": day.isoformat(), "session_state": "BOUND_STRICT",
                      "local_tradestatus": "1", "turnover_rate": 0.0 if zeros else (index + 1) / 1000})
    target = {"trade_date": target_day.isoformat(), "binding_status": "BOUND_STRICT",
              "local_tradestatus": "1", "turnover_rate": target_rate}
    return target_day.isoformat(), target, prior


def supplemental_row(revision=1, *, binding="BOUND_STRICT", source_digest=None, context="NORMAL"):
    return SupplementalRow(
        publication_id="PUB-ACCEPTED-1", security_id="SEC-001", enrichment_revision=revision,
        provider="BAOSTOCK", trade_date="2026-09-28",
        query_identity={"provider_code":"sh.600000","frequency":"d","start_date":"2026-09-01",
                        "end_date":"2026-09-28","adjustflag":"3"},
        turnover_rate=0.0125,
        turnover_state="AVAILABLE" if binding == "BOUND_STRICT" else binding,
        turnover_context=context if binding == "BOUND_STRICT" else "UNKNOWN",
        supplemental_participation_context={"effect": "NONE", "context": "NONE"},
        provider_asof="2026-09-28", binding_quality=binding,
        quality_codes=(), source_contract_id="BAOSTOCK_SUPPLEMENTAL_SOURCE_V1",
        source_revision_id=f"BAOSTOCK:{revision}:SEC-001",
        source_digest=source_digest or hashlib.sha256(f"source-{revision}".encode()).hexdigest(),
        raw_source_value="1.25", raw_source_unit="PERCENT_POINTS", created_at="2026-09-29T00:00:00Z",
    )


def manifest_for(rows, revision=1):
    return make_manifest(
        publication_id="PUB-ACCEPTED-1", enrichment_revision=revision, provider="BAOSTOCK",
        source_contract_id="BAOSTOCK_SUPPLEMENTAL_SOURCE_V1", field_map_version="BAOSTOCK_FIELD_MAP_V1.1",
        parameter_digest="b" * 64, observed_at="2026-09-29T00:00:00Z",
        ingested_at="2026-09-29T00:00:01Z", provider_asof="2026-09-28", rows=rows,
    )


def test_percent_points_normalize_to_fraction_and_preserve_raw_source_value():
    row = normalize_row("sh.600000", provider_row())
    assert row.turn_fraction == pytest.approx(0.0125)
    assert row.turn_source_value == "1.25"
    assert row.turn_source_unit == "PERCENT_POINTS"


def test_security_mapping_uses_accepted_local_identity_and_market_case_map():
    assert provider_code_from_local("SH.600000") == "sh.600000"
    assert validate_identity_map([{"security_id": "SEC-001", "source_security_key": "SH.600000"}]) == {
        "SEC-001": "sh.600000"
    }
    with pytest.raises(SupplementalError, match="IDENTITY_CONFLICT"):
        validate_identity_map([
            {"security_id": "SEC-001", "source_security_key": "SH.600000"},
            {"security_id": "SEC-001", "source_security_key": "SZ.000001"},
        ])


def test_security_code_change_requires_explicit_accepted_map():
    assert map_code_change("sz.000001", "sz.000001", "SEC-001", {"sz.000001": "sz.000001"}) == "sz.000001"
    with pytest.raises(SupplementalError, match="CODE_CHANGE_IDENTITY_UNACCEPTED"):
        map_code_change("sz.000001", "sz.000002", "SEC-001", {})


def test_exact_trade_date_and_source_identity_are_required_for_binding():
    source = normalize_row("sh.600000", provider_row())
    status, _ = evaluate_binding(local_ref(), source, expected_provider_code="sh.600000",
                                 tolerance_contract=accepted_tolerance())
    assert status == "BOUND_STRICT"
    stale, reasons = evaluate_binding(local_ref(trade_date="2026-09-02"), source,
                                      expected_provider_code="sh.600000", tolerance_contract=accepted_tolerance())
    assert stale == "STALE" and "SOURCE_DATE_STALE" in reasons
    mismatch, _ = evaluate_binding(local_ref(), source, expected_provider_code="sz.600000",
                                   tolerance_contract=accepted_tolerance())
    assert mismatch == "UNBOUND"


def test_binding_statuses_fail_closed_and_conflicts_remain_diagnostic():
    source = normalize_row("sh.600000", provider_row())
    soft, codes = evaluate_binding(local_ref(isST="1"), source, expected_provider_code="sh.600000",
                                   tolerance_contract=accepted_tolerance())
    assert soft == "BOUND_SOFT" and "LOCAL_STATUS_CROSSCHECK_CONFLICT" in codes
    unfrozen, _ = evaluate_binding(local_ref(), source, expected_provider_code="sh.600000",
                                   tolerance_contract={"tolerances": {"close": 0.01, "volume": 0, "amount": 0.01}})
    assert unfrozen == "BOUND_SOFT"
    assert evaluate_binding(local_ref(), None, expected_provider_code="sh.600000",
                             tolerance_contract=None)[0] == "MISSING"
    assert evaluate_binding(local_ref(), None, expected_provider_code="sh.600000",
                             tolerance_contract=None, provider_error_code="10001015")[0] == "SOURCE_NOT_READY"


def test_tolerance_plus_minus_epsilon_boundaries_and_outside_fail_closed():
    source = normalize_row("sh.600000", provider_row())
    tol = accepted_tolerance(tolerances={"close": 0.01, "volume": 0, "amount": 0.01})
    for delta in (-0.01, 0.01):
        assert evaluate_binding(local_ref(close=10.0 + delta), source, expected_provider_code="sh.600000",
                                tolerance_contract=tol)[0] == "BOUND_STRICT"
    assert evaluate_binding(local_ref(close=10.0101), source, expected_provider_code="sh.600000",
                            tolerance_contract=tol)[0] == "UNBOUND"


def test_target_date_is_excluded_from_prior_windows_and_metrics_are_explainable():
    target_day, target, prior = history(n=60)
    out = compute_turnover_context(target_trade_date=target_day, target=target, prior_sessions=prior)
    assert out["turnover_state"] == "AVAILABLE"
    assert out["turnover_ma5"] == pytest.approx(sum((i + 1) / 1000 for i in range(5)) / 5)
    assert out["turnover_median20"] == pytest.approx((0.010 + 0.011) / 2)
    assert out["turnover_pct60"] == 1.0
    assert out["turnover_delta3"] == pytest.approx(0.25 - 0.003)
    assert target_day not in out["prior_sample_dates"]["60"]


def test_confirmed_suspension_can_be_skipped_but_never_enters_baseline():
    target_day, target, prior = history(n=60)
    prior[0] = {"trade_date": "2026-09-27", "session_state": "CONFIRMED_SUSPENSION",
                "local_tradestatus": "0", "turnover_rate": None}
    prior.append({"trade_date": "2026-07-28", "session_state": "BOUND_STRICT",
                  "local_tradestatus": "1", "turnover_rate": 0.061})
    out = compute_turnover_context(target_trade_date=target_day, target=target, prior_sessions=prior)
    assert out["turnover_state"] == "AVAILABLE"
    assert "2026-09-27" not in out["prior_sample_dates"]["60"]


def test_unknown_missing_session_stops_baseline_instead_of_skipping():
    target_day, target, prior = history(n=60)
    prior[3] = {"trade_date": "2026-09-24", "session_state": "UNKNOWN", "turnover_rate": None}
    out = compute_turnover_context(target_trade_date=target_day, target=target, prior_sessions=prior)
    assert out["turnover_state"] == "DEGRADED"
    assert out["turnover_context"] == "UNKNOWN"
    assert "UNKNOWN_MISSING_SESSION_STOPS_HISTORY" in out["quality_codes"]
    assert out["prior_strict_sample_count"] == 3


def test_insufficient_history_degrades_only_turnover_metrics():
    target_day, target, prior = history(n=59)
    out = compute_turnover_context(target_trade_date=target_day, target=target, prior_sessions=prior)
    assert out["turnover_state"] == "DEGRADED"
    assert out["turnover_ma5"] is not None
    assert out["turnover_median20"] is not None
    assert out["turnover_pct60"] is None
    assert out["turnover_context"] == "UNKNOWN"


def test_sixty_prior_strict_actual_samples_is_the_available_lower_boundary():
    target_day, target, prior = history(n=60)
    assert compute_turnover_context(target_trade_date=target_day, target=target, prior_sessions=prior)["turnover_state"] == "AVAILABLE"
    target_day, target, prior = history(n=59)
    assert compute_turnover_context(target_trade_date=target_day, target=target, prior_sessions=prior)["turnover_state"] == "DEGRADED"


def test_lookback_is_capped_at_250_market_sessions():
    target_day, target, prior = history(n=300)
    out = compute_turnover_context(target_trade_date=target_day, target=target, prior_sessions=prior)
    assert out["prior_strict_sample_count"] == 60
    assert out["lookback_market_session_count"] == 250
    assert len(out["prior_sample_dates"]["60"]) == 60
    assert out["turnover_state"] == "AVAILABLE"


def test_nonpositive_median_denominator_returns_unavailable_ratio_without_epsilon():
    target_day, target, prior = history(n=60, zeros=True)
    out = compute_turnover_context(target_trade_date=target_day, target=target, prior_sessions=prior)
    assert out["turnover_median20"] == 0
    assert out["turnover_ratio20"] is None
    assert "NONPOSITIVE_RATIO_DENOMINATOR" in out["quality_codes"]


def test_delta3_is_unavailable_when_endpoint_sample_is_missing():
    target_day, target, prior = history(n=2)
    out = compute_turnover_context(target_trade_date=target_day, target=target, prior_sessions=prior)
    assert out["turnover_delta3"] is None
    assert "DELTA3_ENDPOINT_MISSING" in out["quality_codes"]


def test_soft_or_unbound_target_never_enters_turnover_factor():
    target_day, target, prior = history(n=60)
    target["binding_status"] = "BOUND_SOFT"
    out = compute_turnover_context(target_trade_date=target_day, target=target, prior_sessions=prior)
    assert out["turnover_rate"] is None
    assert out["turnover_pct20"] is None
    assert out["turnover_state"] == "BOUND_SOFT"


def test_timeout_and_provider_not_ready_are_supplemental_only_states():
    assert source_failure_state(None, timed_out=True) == "UNAVAILABLE"
    assert source_failure_state("10001015") == "SOURCE_NOT_READY"
    assert source_failure_state("OTHER") == "UNAVAILABLE"


def test_priority_order_is_deterministic_and_p0_runs_first():
    values = [ScheduledRequest("P2_HISTORICAL_BACKFILL", "SEC-3", "sz.300001", "2025-01-01"),
              ScheduledRequest("P0_DAILY_INCREMENTAL", "SEC-2", "sh.600001", "2026-09-28"),
              ScheduledRequest("P1_MISSING_RECENT_WINDOW", "SEC-1", "sz.000001", "2026-09-20")]
    assert [item.priority for item in order_requests(values)] == [
        "P0_DAILY_INCREMENTAL", "P1_MISSING_RECENT_WINDOW", "P2_HISTORICAL_BACKFILL"
    ]
    assert order_requests(values) == order_requests(reversed(values))


def test_backfill_cannot_consume_reserved_daily_incremental_headroom():
    enforce_priority_budget(priority="P0_DAILY_INCREMENTAL", daily_total=39_998, estimated_request_cost=2)
    with pytest.raises(SupplementalError, match="RESERVED_HEADROOM"):
        enforce_priority_budget(priority="P2_HISTORICAL_BACKFILL", daily_total=35_000, estimated_request_cost=1)
    with pytest.raises(SupplementalError, match="RESERVED_HEADROOM"):
        enforce_priority_budget(priority="P0_DAILY_INCREMENTAL", daily_total=40_000, estimated_request_cost=1)


def test_worker_checkpoint_resume_is_idempotent_and_contains_no_source_rows(tmp_path):
    day = "2026-09-28"

    class Budget:
        hard_limit = 45_000
        soft_limit = 40_000
        def _today_shanghai(self): return day
        def _load(self): return {"by_shanghai_date": {day: {"count": 0}}}

    class Client:
        budget = Budget()
        calls = 0
        def query_daily(self, code, start, end):
            self.calls += 1
            return [normalize_row(code, provider_row(date=day, code=code))]

    client = Client()
    checkpoint = tmp_path / "checkpoint.json"
    worker = BoundedHistoryWorker(client, checkpoint_path=checkpoint)
    request = ScheduledRequest("P1_MISSING_RECENT_WINDOW", "SEC-001", "sh.600000", day)
    first = worker.run([request], start_date=day, end_date=day, job_id="j1")
    second = worker.run([request], start_date=day, end_date=day, job_id="j1")
    assert first["status"] == second["status"] == "COMPLETE"
    assert client.calls == 1
    checkpoint_text = checkpoint.read_text(encoding="utf-8")
    assert "close_price_cny" not in checkpoint_text and "turn_source_value" not in checkpoint_text


def test_worker_circuit_breaks_on_source_not_ready_and_keeps_checkpoint(tmp_path):
    day = "2026-09-28"

    class Budget:
        hard_limit = 45_000
        soft_limit = 40_000
        def _today_shanghai(self): return day
        def _load(self): return {"by_shanghai_date": {day: {"count": 0}}}

    class Client:
        budget = Budget()
        calls = 0
        def query_daily(self, code, start, end):
            self.calls += 1
            raise BaoStockError("BAOSTOCK_QUERY_FAILED", provider_code="10001015")

    client = Client()
    requests = [ScheduledRequest("P1_MISSING_RECENT_WINDOW", f"SEC-{i}", f"sh.60000{i}", day) for i in range(3)]
    result = BoundedHistoryWorker(client, checkpoint_path=tmp_path / "checkpoint.json").run(
        requests, start_date=day, end_date=day, job_id="provider-not-ready")
    assert result["status"] == "CIRCUIT_OPEN"
    assert result["circuit_breaker_reason"] == "PROVIDER_NOT_READY"
    assert client.calls == 1


def test_sdk_retry_is_charged_to_the_shared_request_ledger(monkeypatch, tmp_path):
    for name in ("BAOSTOCK_USERNAME", "BAOSTOCK_PASSWORD", "BAOSTOCK_API_KEY", "BAOSTOCK_AUTH_MODE"):
        monkeypatch.delenv(name, raising=False)

    class Result:
        error_code = "0"
        error_msg = "success"
        fields = ["date", "code", "close", "volume", "amount", "turn", "tradestatus", "isST"]
        cur_row_num = 0
        per_page_count = 2000
        data = [["2026-09-01", "sh.600000", "10", "1200", "12000", "1.25", "1", "0"]]
        def next(self):
            return self.cur_row_num < len(self.data)
        def get_row_data(self):
            row = self.data[self.cur_row_num]
            self.cur_row_num += 1
            return row

    class SDK:
        calls = 0
        @staticmethod
        def login(): return SimpleNamespace(error_code="0", error_msg="success")
        @staticmethod
        def query_history_k_data_plus(*_args, **_kwargs):
            SDK.calls += 1
            if SDK.calls == 1:
                raise socket.timeout("synthetic transport timeout")
            return Result()
        @staticmethod
        def logout(): return SimpleNamespace(error_code="0", error_msg="success")

    path = tmp_path / "ledger.json"
    client = BaoStockClient(RequestBudget(path), sdk=SDK, timeout=1, auth_mode="PUBLIC_ANONYMOUS")
    with client:
        rows = client.query_daily("sh.600000", "2026-09-01", "2026-09-01")
    ledger = json.loads(path.read_text(encoding="utf-8"))
    current = next(iter(ledger["by_shanghai_date"].values()))
    assert len(rows) == 1 and SDK.calls == 2
    assert current["operations"]["query_history_k_data_plus_adjustflag_3"] == 2
    assert current["count"] == 4  # login + first query + retry + logout


def test_request_priority_budget_rejects_invalid_and_unbounded_inputs():
    with pytest.raises(SupplementalError, match="PRIORITY_INVALID"):
        enforce_priority_budget(priority="P9", daily_total=0, estimated_request_cost=1)
    with pytest.raises(SupplementalError, match="INPUT_INVALID"):
        enforce_priority_budget(priority="P0_DAILY_INCREMENTAL", daily_total=-1, estimated_request_cost=1)


def test_revision_manifest_counts_bindings_and_source_revision_set_deterministically():
    rows = [supplemental_row(binding="BOUND_STRICT"),
            supplemental_row(revision=1, binding="BOUND_SOFT", source_digest="c" * 64, context="UNKNOWN")]
    rows[1] = SupplementalRow(**{**asdict(rows[1]), "security_id": "SEC-002"})
    first = manifest_for(rows)
    second = manifest_for(rows)
    assert first == second
    assert first["security_count"] == 2
    assert first["strict_bound_count"] == 1 and first["soft_bound_count"] == 1
    assert first["unavailable_count"] == 0
    assert len(first["source_revision_set_digest"]) == 64


def test_supplemental_revision_is_append_only_and_same_publication_can_advance_revision():
    store = AppendOnlySupplementalStore()
    row1 = supplemental_row(1)
    store.append(manifest_for([row1], 1), [row1])
    row2 = supplemental_row(2, source_digest="d" * 64)
    store.append(manifest_for([row2], 2), [row2])
    assert store.next_revision("PUB-ACCEPTED-1") == 3
    assert len(store.manifests) == 2 and len(store.rows) == 2
    assert store.rows[0].enrichment_revision == 1 and store.rows[0].source_digest != store.rows[1].source_digest


def test_each_supplemental_row_requires_auditable_query_identity():
    row = supplemental_row()
    wrong_adjustment = {**asdict(row), "query_identity": {**row.query_identity, "adjustflag": "2"}}
    with pytest.raises(SupplementalError, match="ENRICHMENT_QUERY_IDENTITY_INVALID"):
        SupplementalRow(**wrong_adjustment).validate()
    missing_target = {**asdict(row), "query_identity": {**row.query_identity, "end_date": "2026-09-27"}}
    with pytest.raises(SupplementalError, match="ENRICHMENT_QUERY_IDENTITY_RANGE_INVALID"):
        SupplementalRow(**missing_target).validate()


def test_query_identity_must_match_the_normalized_source_row():
    source = normalize_row("sh.600001", provider_row(date="2026-09-28", code="sh.600001"))
    with pytest.raises(SupplementalError, match="ENRICHMENT_QUERY_SOURCE_MISMATCH"):
        build_supplemental_row(
            publication_id="PUB-ACCEPTED-1", security_id="SEC-001", enrichment_revision=1,
            trade_date="2026-09-28",
            query_identity={"provider_code":"sh.600000","frequency":"d","start_date":"2026-09-01",
                            "end_date":"2026-09-28","adjustflag":"3"},
            binding_quality="BOUND_SOFT", source=source,
            source_revision_id="BAOSTOCK:QUERY-MISMATCH", source_digest=source.source_digest,
            turnover_context=None, created_at="2026-09-29T00:00:00Z",
        )


def test_duplicate_publication_revision_security_provider_is_rejected():
    store = AppendOnlySupplementalStore()
    row = supplemental_row(1)
    manifest = manifest_for([row], 1)
    store.append(manifest, [row])
    with pytest.raises(SupplementalError, match="REVISION_ALREADY_EXISTS"):
        store.append(manifest, [row])


def test_manifest_rejects_duplicate_security_provider_within_one_revision():
    row = supplemental_row(1)
    duplicate = SupplementalRow(**{**asdict(row), "source_revision_id": "another"})
    with pytest.raises(SupplementalError, match="DUPLICATE_ENRICHMENT"):
        manifest_for([row, duplicate], 1)


def test_source_digest_is_stable_and_commits_raw_unit_and_value():
    first = normalize_row("sh.600000", provider_row())
    again = normalize_row("sh.600000", provider_row())
    changed = normalize_row("sh.600000", provider_row(turn="1.26"))
    assert first.source_digest == again.source_digest
    assert first.source_digest != changed.source_digest
    assert first.turn_source_unit == "PERCENT_POINTS"


def test_core_isolation_matrix_keeps_six_digest_components_for_a_b_c_d():
    core = {
        "core_fact_digest": "1" * 64, "core_profile_digest": "2" * 64,
        "core_eligibility_digest": "3" * 64, "core_state_digest": "4" * 64,
        "core_event_digest": "5" * 64, "validation_enrollment_digest": "6" * 64,
    }
    scenarios = {
        "A_NO_TURNOVER": {},
        "B_TURNOVER_PRE_CACHED": {"turnover_rate": 0.02, "binding": "BOUND_SOFT"},
        "C_TURNOVER_AFTER_ACCEPTANCE": {"enrichment_revision": 1},
        "D_PROVIDER_STATUS_CONFLICT": {"tradestatus": "0", "isST": "1"},
    }
    result = __import__("workbench_analysis.v4_06_supplemental", fromlist=["run_core_isolation_matrix"]).run_core_isolation_matrix(core, scenarios)
    assert result["all_core_components_identical"]
    assert all(item["before"] == item["after"] for item in result["checks"].values())


def test_core_isolation_rejects_supplemental_channel_core_mutation():
    from workbench_analysis.v4_06_supplemental import run_core_isolation_matrix
    core = {key: "a" * 64 for key in ("core_fact_digest", "core_profile_digest", "core_eligibility_digest",
                                       "core_state_digest", "core_event_digest", "validation_enrollment_digest")}
    scenarios = {name: {} for name in ("A_NO_TURNOVER", "B_TURNOVER_PRE_CACHED", "C_TURNOVER_AFTER_ACCEPTANCE", "D_PROVIDER_STATUS_CONFLICT")}
    scenarios["C_TURNOVER_AFTER_ACCEPTANCE"]["core_profile_digest"] = "b" * 64
    with pytest.raises(SupplementalError, match="CORE_MUTATION"):
        run_core_isolation_matrix(core, scenarios)


def test_soft_binding_row_cannot_publish_a_semantic_turnover_context():
    row = supplemental_row(binding="BOUND_SOFT")
    row = SupplementalRow(**{**asdict(row), "turnover_context": "HIGH"})
    with pytest.raises(SupplementalError, match="SOFT_BINDING_SEMANTIC_USE"):
        row.validate()


def test_factor_contract_source_gate_remains_fail_closed():
    contract = json.loads(__import__("pathlib").Path("config/baostock_turnover_binding_tolerance_v1.json").read_text())
    assert contract["status"] == "UNFROZEN_NO_INDEPENDENT_ACCEPTANCE"
    assert contract["tolerances"] is None and contract["strict_binding_allowed"] is False
