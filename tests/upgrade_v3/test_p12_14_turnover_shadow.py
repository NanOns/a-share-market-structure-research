from workbench_analysis.turnover_shadow_v3_3 import build_observation, canonical_observations, report


def active(day="2026-09-15", digest="bundle-a"):
    return {"output_digest": digest, "identity": {"trade_date": day, "research_run_id": "run-a"}}


def enrichment(status="AVAILABLE", items=None, enhanced_items=None):
    return {"status": status, "request": {"candidate_count": 2}, "items": items or [], "enhanced_items": enhanced_items or []}


def bound(security_id="SH.600000", value=.03):
    return {"security_id": security_id, "trade_date": "2026-09-15", "turnover_rate": value, "turnover_basis": "EASTMONEY_FLOAT_SHARE_BASIS", "source_id": "EASTMONEY_QUOTES_LATEST", "capability_status": "BOUND", "observed_at_utc": "2026-09-16T01:00:00Z"}


def test_failure_attempt_is_auditable_but_not_a_bound_sample():
    observation = build_observation(active=active(), enrichment=enrichment("UNAVAILABLE"), captured_at_utc="2026-09-16T01:00:00Z")
    assert observation["requested_count"] == 2
    assert observation["bound_count"] == 0
    assert observation["items"] == []
    summary = report([observation])
    assert summary["gate"] == {"minimum_bound_days": 20, "minimum_bound_rows": 50, "attempt_days": 1, "bound_days": 0, "bound_rows": 0}
    assert summary["effect_status"] == "EFFECT_NOT_EVALUATED"


def test_only_bound_normalized_rows_are_sealed():
    unavailable = {**bound("SZ.000001"), "capability_status": "UNAVAILABLE", "turnover_rate": None}
    enhanced = [{"security_id": "SH.600000", "turnover_activity_percentile": 1.0, "turnover_activity_band": "HIGH", "turnover_enhanced_rank": 1, "turnover_usage": "SECONDARY_ORDER_FOR_QUALIFIED_UNRANKED"}]
    observation = build_observation(active=active(), enrichment=enrichment(items=[bound(), unavailable], enhanced_items=enhanced), captured_at_utc="2026-09-16T01:00:00Z")
    assert observation["bound_count"] == 1
    assert [item["security_id"] for item in observation["items"]] == ["SH.600000"]
    assert observation["items"][0]["turnover_enhanced_rank"] == 1
    assert observation["guardrails"] == {"raw_payload_persisted": False, "core_score_or_category_rank_changed": False, "effect_claimed": False}


def test_canonical_revision_prefers_more_bound_rows():
    failed = build_observation(active=active(), enrichment=enrichment("UNAVAILABLE"), captured_at_utc="2026-09-16T01:00:00Z")
    recovered = build_observation(active=active(), enrichment=enrichment(items=[bound()]), captured_at_utc="2026-09-16T02:00:00Z")
    selected = canonical_observations([failed, recovered])
    assert len(selected) == 1 and selected[0]["bound_count"] == 1


def test_coverage_gate_needs_twenty_distinct_bound_days_and_fifty_rows():
    observations = []
    for index in range(20):
        day = f"2026-10-{index + 1:02d}"
        rows = [{**bound(f"SH.{index * 3 + offset:06d}"), "trade_date": day} for offset in range(3)]
        observations.append(build_observation(active=active(day, f"bundle-{index}"), enrichment=enrichment(items=rows), captured_at_utc=f"{day}T08:00:00Z"))
    summary = report(observations)
    assert summary["status"] == "SHADOW_COVERAGE_READY"
    assert summary["gate"]["bound_days"] == 20
    assert summary["gate"]["bound_rows"] == 60
    assert summary["turnover_distribution"]["status"] == "DESCRIPTIVE_ONLY"
    assert summary["effect_status"] == "EFFECT_NOT_EVALUATED"
