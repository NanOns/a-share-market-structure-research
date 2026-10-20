from scripts.accept_dynamic_daily_baostock_v2 import _provider_failure
from workbench_analysis.baostock_supplemental import BaoStockError


def test_failed_runtime_smoke_retains_sanitized_provider_diagnostic():
    exc = BaoStockError(
        "BAOSTOCK_LOGIN_FAILED",
        provider_code="10002007!",
        provider_message="provider login rejected",
    )

    assert _provider_failure(exc) == {
        "code": "10002007",
        "message": "provider login rejected",
        "source": "SANITIZED_BAOSTOCK_CLIENT_ERROR",
    }


def test_failed_runtime_smoke_without_provider_metadata_stays_generic():
    assert _provider_failure(RuntimeError("SYNTHETIC_FAILURE")) is None
