from pathlib import Path
from types import SimpleNamespace

import scripts.run_p12_14_daily_turnover as daily
import scripts.run_p12_daily_pipeline as pipeline


def test_daily_turnover_retries_failed_existing_bundle_observation(tmp_path, monkeypatch):
    active = {"output_digest": "bundle-a", "identity": {"publication_id": "pub", "trade_date": "2026-09-15", "research_run_id": "run"}}
    existing = {"contract_id": "P12_14_TURNOVER_SHADOW_OBSERVATION_V1", "trade_date": "2026-09-15", "bundle_digest": "bundle-a", "research_run_id": "run", "captured_at_utc": "x", "source_status": "UNAVAILABLE", "source_error": "TimeoutError", "requested_count": 20, "bound_count": 0, "coverage_ratio": 0, "items": [], "guardrails": {"raw_payload_persisted": False, "selection_or_rank_changed": False, "effect_claimed": False}, "observation_digest": "obs-a"}
    monkeypatch.setattr(daily, "read_active", lambda _path: active)
    monkeypatch.setattr(daily, "load_all", lambda _root: [existing])
    class RetryService:
        def __init__(self, *_args, **_kwargs): pass
        def load(self, **_kwargs): return {"status": "UNAVAILABLE", "source_error": "retry", "request": {"candidate_count": 54}, "items": [], "enhanced_items": []}
    monkeypatch.setattr(daily, "TurnoverEnrichmentService", RetryService)
    monkeypatch.setattr(daily, "seal", lambda *_args: {"reused": False})
    monkeypatch.setattr(daily, "report", lambda *_args: {"status": "SHADOW_COVERAGE_PENDING"})
    monkeypatch.setattr(daily, "atomic_write_json", lambda *_args: None)
    result = daily.run("pub", "2026-09-15")
    assert result["status"] == "OPTIONAL_DEGRADED"
    assert result["reused"] is False
    assert result["requested_count"] == 54
    assert result["local_pipeline_blocked"] is False


def test_daily_turnover_identity_mismatch_skips_without_network(monkeypatch):
    monkeypatch.setattr(daily, "read_active", lambda _path: {"output_digest": "x", "identity": {"publication_id": "other", "trade_date": "2026-09-15"}})
    result = daily.run("pub", "2026-09-15")
    assert result == {"status": "OPTIONAL_SKIPPED", "reason": "ACTIVE_IDENTITY_MISMATCH", "local_pipeline_blocked": False}


def test_main_pipeline_reports_optional_failure_but_remains_ready(tmp_path, monkeypatch, capsys):
    pointer = tmp_path / "active.json"
    pointer.write_text("{}", encoding="utf-8")
    active = {"contract_id": "TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_03_FULL_LOO", "output_digest": "bundle", "identity": {"publication_id": "pub", "trade_date": "2026-09-15"}, "bundle_path": str(tmp_path / "bundle")}
    (tmp_path / "bundle").mkdir()
    (tmp_path / "bundle/results.json").write_text('[{"security_name":"A","scanner_evidence":{}}]', encoding="utf-8")
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)
    monkeypatch.setattr(pipeline, "POINTER", pointer)
    monkeypatch.setattr(pipeline, "read_active", lambda _path: active)
    monkeypatch.setattr(pipeline, "optional_turnover", lambda *_args: {"status": "OPTIONAL_DEGRADED", "local_pipeline_blocked": False})
    monkeypatch.setattr(pipeline.sys, "argv", ["run", "--publication-id", "pub", "--trade-date", "2026-09-15"])
    pipeline.main()
    output = capsys.readouterr().out
    assert '"status": "READY"' in output
    assert '"OPTIONAL_DEGRADED"' in output


def test_optional_subprocess_report_failure_is_nonblocking(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)
    monkeypatch.setattr(pipeline.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=9, stdout="", stderr="boom"))
    result = pipeline.optional_turnover("pub", "2026-09-15")
    assert result["status"] == "OPTIONAL_DEGRADED"
    assert result["local_pipeline_blocked"] is False


def test_optional_subprocess_timeout_is_nonblocking(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)
    monkeypatch.setattr(pipeline.subprocess, "run", lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError("slow")))
    result = pipeline.optional_turnover("pub", "2026-09-15")
    assert result == {"status": "OPTIONAL_DEGRADED", "reason": "TimeoutError", "local_pipeline_blocked": False}
