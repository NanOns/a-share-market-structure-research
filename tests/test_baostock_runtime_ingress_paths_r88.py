from pathlib import Path


def test_dynamic_acceptance_uses_pg_session_and_contract_before_ingress(monkeypatch, tmp_path):
    from scripts import accept_dynamic_daily_baostock_v2 as runtime

    calls = []
    monkeypatch.setattr(runtime, "official_sessions", lambda root: calls.append(("sessions", root)) or ["2026-10-16"])
    monkeypatch.setattr(runtime, "source_readiness", lambda target, now: {"time_eligible": False})

    result = runtime.accept_runtime("2026-10-16", tmp_path)

    assert result == {"status": "WAIT_BAOSTOCK_FACTOR", "reason": "TIME_GATE_NOT_REACHED"}
    assert calls == [("sessions", tmp_path)]


def test_dynamic_acceptance_cache_uses_configured_cache_root(monkeypatch, tmp_path):
    from scripts import accept_dynamic_daily_baostock_v2 as runtime

    cache = tmp_path / "configured-cache"
    monkeypatch.setattr(runtime, "resolve_baostock_cache_root", lambda root: cache)

    assert runtime.runtime_acceptance_cache_dir(tmp_path, "2026-10-16") == (
        cache / "baostock" / "20261016" / "runtime_acceptance"
    )


def test_runtime_smoke_cache_uses_configured_cache_root(monkeypatch, tmp_path):
    from scripts import accept_v4_dm01_baostock_runtime as runtime

    cache = tmp_path / "configured-cache"
    monkeypatch.setattr(runtime, "resolve_baostock_cache_root", lambda root: cache)

    assert runtime.runtime_acceptance_cache_dir(tmp_path, "2026-10-16") == (
        cache / "baostock" / "20261016" / "runtime_acceptance"
    )


def test_acceptance_entrypoint_has_no_reports_authority_or_local_schema_read():
    root = Path(__file__).resolve().parents[1]
    source = (root / "scripts/accept_dynamic_daily_baostock_v2.py").read_text(encoding="utf-8")

    assert "official_sessions(root)" in source
    assert "_daily_runtime_contract('BAOSTOCK_DM01_SDK_SCHEMA_ADAPTER_V2','2.0.0',version_field='version')" in source
    assert "config/baostock_dm01_sdk_schema_adapter_v2.json" not in source
    assert "reports'/'v4_baostock'/'runtime_acceptance" not in source
