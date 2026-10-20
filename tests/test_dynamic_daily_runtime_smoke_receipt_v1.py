from scripts import accept_dynamic_daily_baostock_v2 as smoke
from workbench_analysis.baostock_supplemental import BaoStockError


def test_failed_runtime_smoke_retains_sanitized_provider_diagnostic():
    exc = BaoStockError(
        "BAOSTOCK_LOGIN_FAILED",
        provider_code="10002007!",
        provider_message="provider login rejected",
    )

    assert smoke._provider_failure(exc) == {
        "code": "10002007",
        "message": "provider login rejected",
        "source": "SANITIZED_BAOSTOCK_CLIENT_ERROR",
    }


def test_failed_runtime_smoke_without_provider_metadata_stays_generic():
    assert smoke._provider_failure(RuntimeError("SYNTHETIC_FAILURE")) is None


def test_full_market_smoke_uses_bounded_timeout_above_observed_response_time(monkeypatch, tmp_path):
    captured = {}

    class FakeBudget:
        def __init__(self, path):
            captured["ledger_path"] = path

    class FakeClient:
        def __init__(self, budget, **kwargs):
            captured["kwargs"] = kwargs

    monkeypatch.setattr(smoke, "RequestBudget", FakeBudget)
    monkeypatch.setattr(smoke, "BaoStockClient", FakeClient)
    client = smoke._live_smoke_client(tmp_path)

    assert isinstance(client, FakeClient)
    assert captured["ledger_path"] == tmp_path / "reports/v4_baostock/request_ledger.json"
    assert captured["kwargs"] == {
        "auth_mode": "PUBLIC_ANONYMOUS",
        "allow_unaccepted_runtime_smoke": True,
        "timeout": 90,
    }
