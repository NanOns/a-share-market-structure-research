from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from workbench_analysis import baostock_supplemental as bao

conx = SimpleNamespace(default_socket=None)


def source_row(**updates):
    row = {
        "date": "2026-09-01",
        "code": "sh.600000",
        "close": "10.0000",
        "volume": "1200",
        "amount": "12000.00",
        "turn": "1.25",
        "tradestatus": "1",
        "isST": "0",
    }
    row.update(updates)
    return row


def test_turn_is_percent_points_and_fraction_conversion_is_explicit():
    assert bao.normalize_turn("1.25") == pytest.approx(0.0125)
    assert bao.normalize_turn("") is None
    with pytest.raises(bao.BaoStockError, match="INVALID_TURN_VALUE"):
        bao.normalize_turn("NaN")
    with pytest.raises(bao.BaoStockError, match="INVALID_BAOSTOCK_ROW"):
        bao.normalize_row("sh.600000", source_row(volume="1.5"))


def test_normalized_receipt_digest_is_deterministic_and_contains_no_credentials():
    first = bao.normalize_row("sh.600000", source_row())
    second = bao.normalize_row("sh.600000", source_row())
    assert first == second
    assert first.turn_fraction == pytest.approx(0.0125)
    serialized = json.dumps(first.__dict__)
    assert "password" not in serialized.lower()
    assert "api_key" not in serialized.lower()


def test_strict_binding_requires_exact_identity_and_date_and_all_fingerprint_fields():
    row = bao.normalize_row("sh.600000", source_row())
    tol = {"close": 0.0001, "volume": 0, "amount": 0.01}
    local = {"security_id": "sh.600000", "trade_date": 20260901, "close": 10.0, "volume": 1200, "amount": 12000.0}
    assert bao.strict_fingerprint(local, row, tol)
    assert not bao.strict_fingerprint({**local, "security_id": "sz.600000"}, row, tol)
    assert not bao.strict_fingerprint({**local, "trade_date": 20260902}, row, tol)
    with pytest.raises(bao.BaoStockError, match="TOLERANCE_CONTRACT_INVALID"):
        bao.strict_fingerprint(local, row, {"close": 0.1})


def test_binding_stays_soft_without_independently_accepted_tolerance_and_status():
    row = bao.normalize_row("sh.600000", source_row())
    local = {"security_id": "sh.600000", "trade_date": 20260901, "close": 10.0, "volume": 1200,
             "amount": 12000.0, "tradestatus": "1", "isST": "0"}
    pending = {"tolerances": {"close": 0.0001, "volume": 0, "amount": 0.01}}
    assert bao.evaluate_binding(local, row, pending) == "BOUND_SOFT"
    assert bao.evaluate_binding(local, row, None) == "UNBOUND"
    accepted = {
        **pending,
        "contract_id": "BAOSTOCK_FINGERPRINT_TOLERANCE_V1",
        "version": "1.0.0",
        "evidence_digest": "1" * 64,
        "accepted_by": "independent_review",
        "accepted_at_utc": "2026-09-25T00:00:00Z",
        "acceptance": "INDEPENDENTLY_ACCEPTED",
    }
    assert bao.evaluate_binding(local, row, accepted) == "BOUND_STRICT"
    assert bao.evaluate_binding({**local, "isST": "1"}, row, accepted) == "BOUND_SOFT"


def test_budget_counts_retries_and_stops_before_daily_hard_limit(tmp_path: Path):
    ledger = bao.RequestBudget(tmp_path / "ledger.json", hard_limit=4, soft_limit=3)
    assert ledger.consume("login") == 1
    assert ledger.consume("query") == 2
    assert ledger.consume("retry") == 3
    with pytest.raises(bao.BaoStockError, match="DAILY_REQUEST_SOFT_STOP"):
        ledger.consume("new_query")
    assert ledger.consume("logout", bypass_soft_stop=True) == 4
    with pytest.raises(bao.BaoStockError, match="DAILY_REQUEST_HARD_STOP"):
        ledger.consume("over_cap", bypass_soft_stop=True)
    saved = json.loads((tmp_path / "ledger.json").read_text(encoding="utf-8"))
    assert sum(item["count"] for item in saved["by_shanghai_date"].values()) == 4
    assert "secret" not in json.dumps(saved).lower()


def test_bad_or_unreadable_ledger_fails_closed(tmp_path: Path):
    path = tmp_path / "ledger.json"
    path.write_text("not json", encoding="utf-8")
    with pytest.raises(bao.BaoStockError, match="REQUEST_LEDGER_UNREADABLE_FAIL_CLOSED"):
        bao.RequestBudget(path).consume("query")


def test_vip_client_refuses_to_start_without_vip_environment_secrets(monkeypatch, tmp_path: Path):
    for name in ("BAOSTOCK_USERNAME", "BAOSTOCK_PASSWORD", "BAOSTOCK_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(bao.BaoStockError, match="BAOSTOCK_CREDENTIAL_ENV_MISSING"):
        with bao.BaoStockClient(bao.RequestBudget(tmp_path / "ledger.json"), auth_mode="VIP_API_KEY"):
            pytest.fail("session must not start")


def test_client_fake_sdk_routes_api_key_and_keeps_session_serial(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("BAOSTOCK_USERNAME", "user-placeholder")
    monkeypatch.setenv("BAOSTOCK_PASSWORD", "password-placeholder")
    monkeypatch.setenv("BAOSTOCK_API_KEY", "bs-placeholder")
    monkeypatch.setattr(bao.importlib.metadata, "version", lambda _: bao.VIP_PACKAGE_VERSION)

    class Result:
        error_code = "0"
        fields = ["date", "code", "close", "volume", "amount", "turn", "tradestatus", "isST"]

        def __init__(self):
            self.rows = [list(source_row().values())]

        def next(self):
            return bool(self.rows)

        def get_row_data(self):
            return self.rows.pop(0)

    class SDK:
        api_key = None
        login_args = None
        query_args = None
        logout_calls = 0
        default_socket = None

        @staticmethod
        def set_API_key(key):
            SDK.api_key = key

        @staticmethod
        def login(user, password):
            SDK.login_args = (user, password)
            return SimpleNamespace(error_code="0")

        @staticmethod
        def query_history_k_data_plus(*args, **kwargs):
            SDK.query_args = (args, kwargs)
            return Result()

        @staticmethod
        def logout():
            SDK.logout_calls += 1

    ledger = tmp_path / "ledger.json"
    client = bao.BaoStockClient(bao.RequestBudget(ledger), sdk=SDK, auth_mode="VIP_API_KEY")
    with client:
        rows = client.query_daily("sh.600000", "2026-09-01", "2026-09-01")
        with pytest.raises(bao.BaoStockError, match="ANOTHER_BAOSTOCK_SESSION_ACTIVE"):
            with bao.BaoStockClient(bao.RequestBudget(ledger), sdk=SDK):
                pass
    assert len(rows) == 1
    assert SDK.api_key == "bs-placeholder"
    assert SDK.login_args == ("user-placeholder", "password-placeholder")
    assert SDK.query_args[1]["adjustflag"] == "3"
    assert SDK.query_args[1]["frequency"] == "d"
    assert SDK.logout_calls == 1
    assert "placeholder" not in ledger.read_text(encoding="utf-8")
    assert not (tmp_path / "ledger.json.session.lock").exists()


def test_public_anonymous_mode_uses_no_credentials_or_api_key(monkeypatch, tmp_path: Path):
    for name in ("BAOSTOCK_USERNAME", "BAOSTOCK_PASSWORD", "BAOSTOCK_API_KEY", "BAOSTOCK_AUTH_MODE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(bao.importlib.metadata, "version", lambda _: bao.PACKAGE_VERSION)

    class Result:
        error_code = "0"
        fields = ["calendar_date", "is_trading_day"]
        data = [["2026-09-01", "1"]]
        cur_row_num = 0
        per_page_count = 2000

        def next(self):
            return self.cur_row_num < len(self.data)

        def get_row_data(self):
            row = self.data[self.cur_row_num]
            self.cur_row_num += 1
            return row

    class SDK:
        key_setter_called = False
        login_args = None
        logout_calls = 0

        @staticmethod
        def set_API_key(_key):
            SDK.key_setter_called = True

        @staticmethod
        def login(*args):
            SDK.login_args = args
            return SimpleNamespace(error_code="0", error_msg="success")

        @staticmethod
        def query_trade_dates(**_kwargs):
            return Result()

        @staticmethod
        def logout():
            SDK.logout_calls += 1
            return SimpleNamespace(error_code="0", error_msg="success")

    client = bao.BaoStockClient(bao.RequestBudget(tmp_path / "public-ledger.json"), sdk=SDK,
                                auth_mode="PUBLIC_ANONYMOUS")
    with client:
        rows, metadata = client.probe_trade_dates("2026-09-01", "2026-09-02")
    assert len(rows) == 1
    assert metadata["error_code"] == "0"
    assert SDK.login_args == ()
    assert SDK.key_setter_called is False
    assert client.login_result["error_code"] == "0"
    assert client.logout_result["error_code"] == "0"
    assert bao.BaoStockClient.credentials_present("PUBLIC_ANONYMOUS")
    assert not bao.BaoStockClient.credentials_present("VIP_API_KEY")


def test_public_runtime_fails_closed_on_unverified_sdk_version(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(bao.importlib.metadata, "version", lambda _: bao.VIP_PACKAGE_VERSION)
    with pytest.raises(bao.BaoStockError, match="BAOSTOCK_PACKAGE_VERSION_UNPINNED_FOR_AUTH_MODE"):
        with bao.BaoStockClient(bao.RequestBudget(tmp_path / "ledger.json"), sdk=object(),
                                auth_mode="PUBLIC_ANONYMOUS"):
            pytest.fail("unverified public SDK version must be rejected")
    assert not (tmp_path / "ledger.json").exists()
    assert not (tmp_path / "ledger.json.session.lock").exists()


def test_package_metadata_is_pinned_and_secret_free():
    metadata = bao.package_metadata()
    assert metadata["version"] in bao.SUPPORTED_PACKAGE_VERSIONS
    assert metadata["default_auth_mode"] == "PUBLIC_ANONYMOUS"
    assert metadata["expected_version_for_default_auth_mode"] == "0.9.3"
    assert "VIP_API_KEY" in metadata["supported_auth_modes"]
    assert "password" not in json.dumps(metadata).lower()


def test_history_worker_sorts_checkpoints_and_resumes_idempotently(tmp_path: Path):
    calls = []
    persisted = []

    class Client:
        def query_daily(self, code, start, end):
            calls.append(code)
            return [bao.normalize_row(code, source_row(code=code))]

    checkpoint_path = tmp_path / "checkpoint.json"
    result = bao.run_history_job(
        Client(), ["sz.000001", "sh.600000", "sz.000001"], "2026-09-01", "2026-09-02",
        checkpoint_path, lambda _: "BOUND_STRICT",
        lambda code, rows: persisted.append((code, len(rows))), "job-1",
    )
    assert result["status"] == "COMPLETE"
    assert calls == ["sh.600000", "sz.000001"]
    assert persisted == [("sh.600000", 1), ("sz.000001", 1)]
    checkpoint = checkpoint_path.read_text(encoding="utf-8")
    assert "close_price_cny" not in checkpoint
    assert "raw_payload" not in checkpoint
    resumed = bao.run_history_job(
        Client(), ["sh.600000", "sz.000001"], "2026-09-01", "2026-09-02",
        checkpoint_path, lambda _: "BOUND_STRICT",
        lambda code, rows: pytest.fail("completed request repeated"), "job-1",
    )
    assert resumed["status"] == "COMPLETE"
    assert calls == ["sh.600000", "sz.000001"]


def test_history_worker_rejects_checkpoint_for_different_query(tmp_path: Path):
    checkpoint = tmp_path / "checkpoint.json"
    checkpoint.write_text(json.dumps({"request_identity": {"wrong": True}}), encoding="utf-8")
    with pytest.raises(bao.BaoStockError, match="CHECKPOINT_IDENTITY_MISMATCH"):
        bao.run_history_job(object(), ["sh.600000"], "2026-09-01", "2026-09-02", checkpoint,
                            lambda _: "BOUND_SOFT", lambda *_: None, "job-2")
