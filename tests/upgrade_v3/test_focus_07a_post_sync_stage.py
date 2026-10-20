import json
from pathlib import Path
from types import SimpleNamespace

from workbench_service import focus_daily_stage
from workbench_service.focus_daily_stage import run_after_pg_sync


SYNC = {"status": "FULL_PASS", "trade_date": "2026-09-24",
        "publication_id": "publication-1"}


def report(**values):
    return json.dumps({"contract_id": "FOCUS_DAILY_RUNNER_V1",
                       "trade_date": "2026-09-24", **values})


def identity_report(**values):
    return json.dumps({"contract_id": "FOCUS_TECHNICAL_IDENTITY_REGISTRATION_V1",
                       "status": "ACCEPTED", "trade_date": "2026-09-24",
                       "publication_id": "publication-1", "source_object_id": "result-object",
                       "legacy_hash": "a" * 64, "canonical_hash": "b" * 64,
                       "evidence_sha256": "c" * 64, "row_count": 1, **values})


def with_identity(runner):
    def wrapped(command, **kwargs):
        if "scripts.register_focus_technical_identity" in command:
            return SimpleNamespace(returncode=0, stdout=identity_report())
        return runner(command, **kwargs)
    return wrapped


def call(runner, monkeypatch):
    monkeypatch.setattr(focus_daily_stage, "_automatic_apply_gate",
                        lambda _root: (True, "ACCEPTED"))
    return run_after_pg_sync(root=Path("/tmp/project"), trade_date="2026-09-24",
                             publication_id="publication-1", sync_report=SYNC,
                             run_command=with_identity(runner))


def test_focus_runs_only_after_exact_accepted_sync():
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Focus subprocess must not run")
    result = run_after_pg_sync(
        root=Path("/tmp/project"), trade_date="2026-09-24",
        publication_id="publication-1",
        sync_report={**SYNC, "publication_id": "other"}, run_command=forbidden)
    assert result["status"] == "FAILED"
    assert result["core_status"] == "NOT_RUN"


def test_automatic_apply_gate_reads_exact_pg_bound_bytes_without_local_file():
    raw = (Path(__file__).resolve().parents[2] / "config/focus_daily_pipeline_gate_v1.json").read_bytes()
    calls = []

    def source_loader(root, source_path, *, expected_sha256):
        calls.append((root, source_path, expected_sha256))
        return SimpleNamespace(read_bytes=lambda: raw)

    enabled, reason = focus_daily_stage._automatic_apply_gate(
        Path("G:/not-used-as-a-file-authority"), source_loader=source_loader)

    assert calls == [(Path("G:/not-used-as-a-file-authority"),
                      focus_daily_stage.GATE_SOURCE_PATH,
                      focus_daily_stage.GATE_SOURCE_SHA256)]
    assert enabled is False
    assert reason == "REAL_NEXT_DAY_ACCEPTED; MULTI_DAY_FORWARD_AND_DUE_OUTCOME_ACCEPTANCE_PENDING"


def test_automatic_apply_gate_fails_closed_when_pg_source_unavailable():
    def unavailable(*_args, **_kwargs):
        raise RuntimeError("PG_UNAVAILABLE")

    assert focus_daily_stage._automatic_apply_gate(
        Path("G:/not-used-as-a-file-authority"), source_loader=unavailable) == (
            False, "FOCUS_PIPELINE_GATE_UNAVAILABLE")


def test_preflight_then_apply_and_report_ready(monkeypatch):
    calls = []
    def runner(command, **_kwargs):
        calls.append(command[-1])
        if command[-1] == "--preflight":
            return SimpleNamespace(returncode=0, stdout=report(
                core_status="PREFLIGHT_READY", publication_id="publication-1",
                manifest_sha256="abc"))
        return SimpleNamespace(returncode=0, stdout=report(
            core_status="ACTIVATED", outcome_status="NO_DUE_OUTCOMES"))
    result = call(runner, monkeypatch)
    assert calls == ["--preflight", "--apply"]
    assert result["status"] == "READY"
    assert result["manifest_sha256"] == "abc"
    assert result["technical_identity"]["status"] == "ACCEPTED"


def test_preflight_failure_never_applies(monkeypatch):
    calls = []
    def runner(command, **_kwargs):
        calls.append(command[-1])
        return SimpleNamespace(returncode=2, stdout=report(
            core_status="BLOCKED", reason="SOURCE_UNAVAILABLE"))
    result = call(runner, monkeypatch)
    assert calls == ["--preflight"]
    assert result["status"] == "DEGRADED"


def test_settlement_degradation_preserves_core_activation(monkeypatch):
    def runner(command, **_kwargs):
        if command[-1] == "--preflight":
            return SimpleNamespace(returncode=0, stdout=report(
                core_status="PREFLIGHT_READY", publication_id="publication-1"))
        return SimpleNamespace(returncode=3, stdout=report(
            core_status="ACTIVATED", outcome_status="DEGRADED",
            outcome_error="TimeoutError"))
    result = call(runner, monkeypatch)
    assert result["status"] == "DEGRADED"
    assert result["core_status"] == "ACTIVATED"


def test_closed_release_gate_runs_preflight_only():
    calls = []
    def runner(command, **_kwargs):
        calls.append(command[-1])
        return SimpleNamespace(returncode=0, stdout=report(
            core_status="PREFLIGHT_READY", publication_id="publication-1"))
    result = run_after_pg_sync(
        root=Path(__file__).resolve().parents[2], trade_date="2026-09-24",
        publication_id="publication-1", sync_report=SYNC,
        run_command=with_identity(runner))
    assert calls == ["--preflight"]
    assert result["automatic_apply_enabled"] is False


def test_identity_failure_is_reported_without_blocking_focus_preflight(monkeypatch):
    monkeypatch.setattr(focus_daily_stage, "_automatic_apply_gate",
                        lambda _root: (False, "GATE_CLOSED"))
    calls = []
    def runner(command, **_kwargs):
        calls.append(command[2])
        if "scripts.register_focus_technical_identity" in command:
            return SimpleNamespace(returncode=2, stdout=identity_report(status="BLOCKED"))
        return SimpleNamespace(returncode=0, stdout=report(
            core_status="PREFLIGHT_READY", publication_id="publication-1"))
    result = run_after_pg_sync(root=Path("/tmp/project"), trade_date="2026-09-24",
                               publication_id="publication-1", sync_report=SYNC,
                               run_command=runner)
    assert calls == ["scripts.register_focus_technical_identity", "scripts.run_focus_daily"]
    assert result["core_status"] == "PREFLIGHT_READY"
    assert result["technical_identity"]["status"] == "BLOCKED"


def test_identity_registration_precedes_focus_preflight(monkeypatch):
    monkeypatch.setattr(focus_daily_stage, "_automatic_apply_gate",
                        lambda _root: (False, "GATE_CLOSED"))
    calls = []
    def runner(command, **_kwargs):
        calls.append((command[2], command[-1]))
        if "scripts.register_focus_technical_identity" in command:
            return SimpleNamespace(returncode=0, stdout=identity_report())
        return SimpleNamespace(returncode=0, stdout=report(
            core_status="PREFLIGHT_READY", publication_id="publication-1"))
    result = run_after_pg_sync(root=Path("/tmp/project"), trade_date="2026-09-24",
                               publication_id="publication-1", sync_report=SYNC,
                               run_command=runner)
    assert calls == [("scripts.register_focus_technical_identity", "--apply"),
                     ("scripts.run_focus_daily", "--preflight")]
    assert result["technical_identity"]["status"] == "ACCEPTED"
