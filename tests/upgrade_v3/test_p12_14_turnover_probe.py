from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (ROOT / "scripts/run_p12_14_turnover_probe.py").read_text(encoding="utf-8")


def test_probe_uses_bounded_sequential_batches_and_never_persists_raw_payload():
    assert "candidate_ids = select_enrichment_ids" in SCRIPT
    assert "timeout_seconds=8" in SCRIPT
    assert "max_response_bytes=200_000" in SCRIPT
    assert "range(0, len(candidate_ids), 50)" in SCRIPT
    assert '"planned_batch_count": (len(candidate_ids) + 49) // 50' in SCRIPT
    assert '"max_batch_size": 50' in SCRIPT
    assert '"raw_payload_persisted": False' in SCRIPT
    assert "result.body" not in SCRIPT


def test_probe_binds_to_active_bundle_date_and_local_daily_fingerprint():
    assert 'target_date = identity["trade_date"]' in SCRIPT
    assert "raw_close, raw_amount, raw_volume" in SCRIPT
    assert "bind_turnover_row" in SCRIPT
    assert '"core_score_or_category_rank_changed": False' in SCRIPT
    assert '"historical_backfill_attempted": False' in SCRIPT
    assert '"FULL_PASS" if counts.get("BOUND") else "DEGRADED_PASS"' in SCRIPT
