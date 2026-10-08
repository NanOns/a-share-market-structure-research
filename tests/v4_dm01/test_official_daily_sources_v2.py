from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from tdx.day_reader import DAY_STRUCT
from workbench_analysis import baostock_daily_update_source as bao_source
from workbench_analysis import tdx_official_daily_source as tdx_source
from workbench_analysis.baostock_daily_update_source import (
    BaoStockDailyUpdateError,
    capture_baostock_daily_update,
    crosscheck_tdx_with_baostock,
)
from workbench_analysis.baostock_supplemental import BaoStockError, RequestBudget
from workbench_analysis.baostock_runtime_acceptance import (
    build_runtime_acceptance_manifest,
    load_runtime_acceptance_manifest,
    runtime_acceptance_error,
)
from workbench_analysis.continuous_data_maintenance import (
    BAR_STATUS_SUSPENDED,
    BAR_STATUS_UNKNOWN,
    classify_trading_status,
)
from workbench_analysis.daily_data_head import CAPABILITIES
from workbench_analysis.daily_increment_builder import (
    affected_component_scopes,
    build_raw_increment_staging,
    run_incremental_components,
)
from workbench_analysis.daily_increment_postcheck import (
    independent_daily_increment_postcheck,
    make_independent_postcheck_callback,
)
from workbench_analysis.daily_source_freeze import build_source_freeze_manifest_v2
from workbench_analysis.daily_source_manifests import (
    build_current_lifecycle_snapshot,
    build_special_phase_source_manifest,
)
from workbench_analysis.daily_source_orchestrator import evaluate_daily_source_readiness
from workbench_analysis.gbbq_source_revision_probe import probe_gbbq_source_revision
from workbench_analysis.tdx_official_daily_source import TDXSourceError
from workbench_analysis.tdx_snapshot_delta import (
    TDXDeltaError,
    build_tdx_package_delta,
    build_tdx_session_delta_view,
)


TARGET = "2026-09-28"
TARGET_NUMBER = 20260928


def _tdx_ready():
    digest = "a" * 64
    return {"target_date": TARGET, "update_date": TARGET, "status": "TDX_PACKAGE_READY",
            "snapshot_id": "sha256-" + digest, "download": {"sha256": digest, "bytes": 1},
            "zip_validation": {"status": "PASS", "crc_integrity": "PASS"}}


def _bao_ready():
    return {"status": "BAOSTOCK_DAILY_SNAPSHOT_READY", "trade_date": TARGET, "provider_date": TARGET,
            "snapshot_id": "bao1", "source_revision_id": "20260928-r1",
            "daily_rows": [_daily_row()], "adjustment_factor_rows": []}


def _day_record(day: int, close: int, *, open_: int | None = None) -> bytes:
    open_ = close if open_ is None else open_
    return DAY_STRUCT.pack(day, open_, max(open_, close), min(open_, close), close, 100000.0, 1000, 0)


def _day_file(*records: tuple[int, int]) -> bytes:
    return b"".join(_day_record(day, close) for day, close in records)


def _zip(path: Path, entries: dict[str, bytes]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, raw in entries.items():
            archive.writestr(name, raw)
    return path


def _tdx_pair(page_update: str, package_bytes: bytes | None = None):
    page = (b'<html><table><a href="https://data.tdx.com.cn/vipdoc/daily/official-pack.zip">zip</a></table>'
            b'<script>$.getScript("//data.tdx.com.cn/vipdoc/_hsjdayinfo.js?t=" + 1)</script></html>')
    info = f'window.HSJDAY_SOFT_TIME="{page_update} 15:57:50";'.encode("ascii")
    items = [FakeResponse(page, tdx_source.PAGE_URL), FakeResponse(info, "https://data.tdx.com.cn/vipdoc/_hsjdayinfo.js")]
    if package_bytes is not None:
        items.append(FakeResponse(package_bytes, "https://data.tdx.com.cn/vipdoc/daily/official-pack.zip"))
    return page, info, items


class FakeResponse:
    def __init__(self, body: bytes, url: str, headers: dict | None = None):
        self.body = body
        self.url = url
        self.headers = headers or {}
        self.offset = 0
        self.status = 200
        self.closed = False

    def read(self, count: int = -1) -> bytes:
        if count < 0:
            count = len(self.body) - self.offset
        data = self.body[self.offset:self.offset + count]
        self.offset += len(data)
        return data

    def geturl(self) -> str:
        return self.url

    def close(self) -> None:
        self.closed = True


def _capture_tdx(monkeypatch, tmp_path: Path, *, update: str, package: bytes | None = None):
    page, info, responses = _tdx_pair(update, package)
    monkeypatch.setattr(tdx_source, "_request", lambda url, timeout=30: responses.pop(0))
    return tdx_source.capture_tdx_official_daily_package(
        target_date=TARGET,
        snapshot_root=tmp_path / "outside" / "snapshots",
        tdx_root=tmp_path / "client" / "vipdoc",
    )


def _valid_package(close: int = 1000) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("sh/lday/sh600000.day", _day_file((20260924, 990), (TARGET_NUMBER, close)))
        archive.writestr("sz/lday/sz000001.day", _day_file((20260924, 1000), (TARGET_NUMBER, 1000)))
    return buffer.getvalue()


def test_tdx_page_update_date_before_target_waits(monkeypatch, tmp_path):
    result = _capture_tdx(monkeypatch, tmp_path, update="2026-09-25")
    assert result["status"] == "WAIT_TDX_PUBLICATION"
    assert result["update_date"] == "2026-09-25"
    assert result["download"] is None
    assert Path(result["receipt_path"]).is_file()


def test_before_close_waits_before_any_source_capture():
    result = evaluate_daily_source_readiness(
        trade_date=TARGET, observed_at="2026-09-28T03:30:00+00:00", official_session_confirmed=True,
        tdx_capture=None, baostock_capture=None, baostock_capability_accepted=False, gbbq_snapshot=None,
        lifecycle_snapshot=None, special_phase_snapshot=None,
    )
    assert result["status"] == "WAIT_MARKET_CLOSE"


def test_tdx_page_update_date_target_enables_download(monkeypatch, tmp_path):
    result = _capture_tdx(monkeypatch, tmp_path, update=TARGET, package=_valid_package())
    assert result["status"] == "TDX_PACKAGE_READY"
    assert result["update_date"] == TARGET
    assert result["zip_validation"]["crc_integrity"] == "PASS"


def test_static_cookie_challenge_uses_existing_downloader_and_preserves_rejection(monkeypatch, tmp_path):
    package = tmp_path / 'existing.zip'
    package.write_bytes(_valid_package())
    calls = []

    def existing(target, url, *, max_bytes):
        calls.append((target, url))
        return package, {'package': {'sha256': tdx_source.sha256_file(package)},
                         'adapter_contract': 'TDX_EXISTING_R3_DOWNLOADER_ADAPTER_V1'}

    monkeypatch.setattr(tdx_source, '_existing_downloader_package', existing)
    result = _capture_tdx(monkeypatch, tmp_path, update=TARGET,
                          package=b'<html>WTKkN:1,bOYDu:2,wyeCN:3</html>')
    assert calls and result['status'] == 'TDX_PACKAGE_READY'
    assert result['download']['sha256'] == tdx_source.sha256_file(package)
    rejected = Path(result['rejected_response']['path'])
    assert rejected.read_bytes().startswith(b'<html>')
    assert (rejected.parent / 'rejected_response_receipt.json').is_file()


def test_tdx_download_url_is_discovered_not_hardcoded():
    markup = b'<a href="https://data.tdx.com.cn/release/todays-file.zip">x</a>'
    assert tdx_source.discover_download_url(markup) == "https://data.tdx.com.cn/release/todays-file.zip"


def test_tdx_package_sha_is_frozen(monkeypatch, tmp_path):
    package = _valid_package()
    result = _capture_tdx(monkeypatch, tmp_path, update=TARGET, package=package)
    saved = Path(result["download"]["path"]).read_bytes()
    assert hashlib.sha256(saved).hexdigest() == result["download"]["sha256"]
    assert result["snapshot_id"] == "sha256-" + hashlib.sha256(package).hexdigest()


def test_same_package_is_noop(monkeypatch, tmp_path):
    package = _valid_package()
    first = _capture_tdx(monkeypatch, tmp_path, update=TARGET, package=package)
    second = _capture_tdx(monkeypatch, tmp_path, update=TARGET, package=package)
    assert first["status"] == "TDX_PACKAGE_READY"
    assert second["status"] == "NOOP_SOURCE_ALREADY_FROZEN"
    assert first["snapshot_id"] == second["snapshot_id"]
    assert Path(first["receipt_path"]).read_bytes() != Path(second["receipt_path"]).read_bytes()


def test_same_day_republished_package_creates_revision(monkeypatch, tmp_path):
    first = _capture_tdx(monkeypatch, tmp_path, update=TARGET, package=_valid_package(1000))
    second = _capture_tdx(monkeypatch, tmp_path, update=TARGET, package=_valid_package(1010))
    assert first["snapshot_id"] != second["snapshot_id"]
    assert first["source_revision_number"] == 1
    assert second["source_revision_number"] == 2


def test_zip_crc_failure_blocks(tmp_path):
    path = _zip(tmp_path / "bad.zip", {
        "sh/lday/sh600000.day": _day_file((20260924, 990)),
        "sz/lday/sz000001.day": _day_file((20260924, 1000)),
    })
    data = path.read_bytes()
    needle = _day_file((20260924, 990))
    offset = data.index(needle)
    path.write_bytes(data[:offset + 8] + bytes([data[offset + 8] ^ 1]) + data[offset + 9:])
    with pytest.raises(TDXSourceError, match="CRC_FAILURE"):
        tdx_source._zip_validate(path)


def test_zip_path_traversal_blocks(tmp_path):
    path = _zip(tmp_path / "unsafe.zip", {
        "../evil.day": _day_file((20260924, 990)),
        "sh/lday/sh600000.day": _day_file((20260924, 990)),
        "sz/lday/sz000001.day": _day_file((20260924, 1000)),
    })
    with pytest.raises(TDXSourceError, match="UNSAFE_ENTRY_PATH"):
        tdx_source._zip_validate(path)


def test_new_package_append_only_delta(tmp_path):
    parent = _zip(tmp_path / "parent.zip", {
        "sh/lday/sh600000.day": _day_file((20260924, 990)),
        "sz/lday/sz000001.day": _day_file((20260924, 1000)),
    })
    current = _zip(tmp_path / "current.zip", {
        "sh/lday/sh600000.day": _day_file((20260924, 990), (TARGET_NUMBER, 1010)),
        "sz/lday/sz000001.day": _day_file((20260924, 1000), (TARGET_NUMBER, 1000)),
    })
    delta = build_tdx_package_delta(parent_zip=parent, current_zip=current, target_date=TARGET,
                                    parent_snapshot_id="parent", current_snapshot_id="current")
    assert delta["status"] == "READY"
    assert delta["target_bar_count"] == 2
    assert delta["appended_bar_count"] == 2
    assert all(item["classification"] == "APPEND_ONLY_TARGET_DATE" for item in delta["entry_events"])


def test_historical_correction_is_detected(tmp_path):
    parent = _zip(tmp_path / "parent.zip", {
        "sh/lday/sh600000.day": _day_file((20260924, 990)),
        "sz/lday/sz000001.day": _day_file((20260924, 1000)),
    })
    current = _zip(tmp_path / "current.zip", {
        "sh/lday/sh600000.day": _day_file((20260924, 995), (TARGET_NUMBER, 1010)),
        "sz/lday/sz000001.day": _day_file((20260924, 1000), (TARGET_NUMBER, 1000)),
    })
    delta = build_tdx_package_delta(parent_zip=parent, current_zip=current, target_date=TARGET,
                                    parent_snapshot_id="parent", current_snapshot_id="current")
    assert delta["revision_events"][0]["classification"] == "HISTORICAL_CORRECTION"
    assert delta["entry_events"][0]["classification"] == "APPEND_WITH_HISTORICAL_CORRECTION"


def test_one_full_package_delta_supports_multiple_session_views(tmp_path):
    parent = _zip(tmp_path / "parent.zip", {
        "sh/lday/sh600000.day": _day_file((20260924, 990)),
        "sz/lday/sz000001.day": _day_file((20260924, 1000)),
    })
    current = _zip(tmp_path / "current.zip", {
        "sh/lday/sh600000.day": _day_file((20260924, 990), (20260925, 995), (TARGET_NUMBER, 1010)),
        "sz/lday/sz000001.day": _day_file((20260924, 1000), (20260925, 1005), (TARGET_NUMBER, 1000)),
    })
    source_delta = build_tdx_package_delta(parent_zip=parent, current_zip=current, target_date=TARGET,
                                           parent_snapshot_id="parent", current_snapshot_id="current")
    assert source_delta["changed_file_manifest"]
    assert all(item["sha256"] and item["bytes"] > 0 and item["trade_date"] == TARGET
               for item in source_delta["changed_file_manifest"])
    first = build_tdx_session_delta_view(source_delta, "2026-09-25")
    last = build_tdx_session_delta_view(source_delta, TARGET)
    assert first["status"] == last["status"] == "READY"
    assert first["target_bar_count"] == last["target_bar_count"] == 2
    assert first["current_snapshot_id"] == last["current_snapshot_id"] == "current"
    assert first["package_delta_sha256"] == last["package_delta_sha256"] == source_delta["delta_sha256"]
    for view in (first, last):
        staged = build_raw_increment_staging(
            trade_date=view["target_date"], source_snapshot_id="current", delta=view,
            output_path=tmp_path / f"raw_{view['target_date']}.jsonl", tdx_root=tmp_path / "tdx",
        )
        assert staged["status"] == "STAGING_READY"
        assert staged["rows"] == 2


def test_truncation_blocks(tmp_path):
    parent = _zip(tmp_path / "parent.zip", {
        "sh/lday/sh600000.day": _day_file((20260923, 980), (20260924, 990)),
        "sz/lday/sz000001.day": _day_file((20260924, 1000)),
    })
    current = _zip(tmp_path / "current.zip", {
        "sh/lday/sh600000.day": _day_file((20260924, 990)),
        "sz/lday/sz000001.day": _day_file((20260924, 1000)),
    })
    with pytest.raises(TDXDeltaError, match="TRUNCATION"):
        build_tdx_package_delta(parent_zip=parent, current_zip=current, target_date=TARGET,
                                parent_snapshot_id="parent", current_snapshot_id="current")


def test_same_length_day_file_trade_date_rewrite_blocks(tmp_path):
    parent = _zip(tmp_path / "parent.zip", {
        "sh/lday/sh600000.day": _day_file((20260923, 980), (20260924, 990)),
        "sz/lday/sz000001.day": _day_file((20260924, 1000)),
    })
    current = _zip(tmp_path / "current.zip", {
        "sh/lday/sh600000.day": _day_file((20260922, 980), (20260924, 990)),
        "sz/lday/sz000001.day": _day_file((20260924, 1000)),
    })
    with pytest.raises(TDXDeltaError, match="REWRITE"):
        build_tdx_package_delta(parent_zip=parent, current_zip=current, target_date=TARGET,
                                parent_snapshot_id="parent", current_snapshot_id="current")


def test_package_never_writes_client_vipdoc(monkeypatch, tmp_path):
    client_root = tmp_path / "client" / "vipdoc"
    _page, _info, responses = _tdx_pair(TARGET, _valid_package())
    monkeypatch.setattr(tdx_source, "_request", lambda url, timeout=30: responses.pop(0))
    result = tdx_source.capture_tdx_official_daily_package(target_date=TARGET, snapshot_root=tmp_path / "snapshots",
                                                           tdx_root=client_root)
    assert result["tdx_root_write_count"] == 0
    assert not client_root.exists()
    assert Path(result["download"]["path"]).is_relative_to(tmp_path / "snapshots")


class FakeSDK:
    def query_daily_history_k_AStock(self, *, date):
        return None

    def query_daily_adjust_factor(self, *, date):
        return None


class FakeBaoClient:
    def __init__(self, daily_rows=None, factor_rows=None, *, provider_date=TARGET, budget=None,
                 auth_mode="PUBLIC_ANONYMOUS"):
        self.logged_in = True
        self.sdk = FakeSDK()
        self.auth_mode = auth_mode
        self.daily_rows = [] if daily_rows is None else daily_rows
        self.factor_rows = [] if factor_rows is None else factor_rows
        self.provider_date = provider_date
        self.budget = budget
        self.calls = []

    def query_rows(self, operation, method_name, *args, max_rows, max_pages, **kwargs):
        if self.budget:
            self.budget.consume(operation)
        self.calls.append((operation, method_name, args, kwargs, max_rows, max_pages))
        if method_name == bao_source.DAILY_METHOD:
            return self.daily_rows, {"error_code": "0", "fields": sorted(self.daily_rows[0]) if self.daily_rows else [], "page_count": 1}
        return self.factor_rows, {"error_code": "0", "fields": sorted(self.factor_rows[0]) if self.factor_rows else [], "page_count": 1,
                                  "provider_date": self.provider_date}


def _daily_row(day=TARGET, code="sh.600000", **overrides):
    row = {"date": day, "code": code, "open": "10.0", "high": "10.0", "low": "10.0", "close": "10.0",
           "preclose": "9.9", "volume": "1000", "amount": "10000", "adjustflag": "3", "turn": "0.1",
           "tradestatus": "1", "pctChg": "1.0", "isST": "0"}
    row.update(overrides)
    return row


def _factor_row(**overrides):
    row = {"code": "sh.600000", "dividOperateDate": TARGET, "foreAdjustFactor": "1.0",
           "backAdjustFactor": "1.0", "adjustFactor": "1.0"}
    row.update(overrides)
    return row


def _runtime_manifest(sdk=None, auth_mode="PUBLIC_ANONYMOUS", target=TARGET):
    sdk = sdk or {"package": "baostock", "version": "0.9.3", "installed_python_sources_sha256": "sdk-hash"}
    live_smoke = {
        "status": "PASS", "target_date": target, "auth_mode": auth_mode,
        "daily": {"method": bao_source.DAILY_METHOD, "provider_date": target, "row_count": 1,
                  "fields": sorted(_daily_row(day=target)), "response_sha256": "d" * 64},
        "adjustment_factor": {"method": bao_source.FACTOR_METHOD, "provider_date": target, "row_count": 0,
                               "fields": sorted(_factor_row().keys()), "response_sha256": "e" * 64},
    }
    return build_runtime_acceptance_manifest(
        sdk=sdk, auth_mode=auth_mode, live_smoke=live_smoke,
        smoke_receipt_path="reports/test/live_smoke_receipt.json", smoke_receipt_sha256="f" * 64,
    )


def _bao_capture(monkeypatch, tmp_path, client, sdk=None, runtime_manifest=None):
    sdk = sdk or {"package": "baostock", "version": "0.9.3", "installed_python_sources_sha256": "sdk-hash"}
    monkeypatch.setattr(bao_source, "package_metadata", lambda: sdk)
    runtime_manifest = runtime_manifest or _runtime_manifest(sdk, client.auth_mode)
    return capture_baostock_daily_update(trade_date=TARGET, client=client, snapshot_root=tmp_path / "snapshots",
                                         tdx_root=tmp_path / "client" / "vipdoc",
                                         observed_at="2026-09-28T09:00:00+00:00",
                                         runtime_acceptance_manifest=runtime_manifest)


def test_dailyupdates_exact_trade_date(monkeypatch, tmp_path):
    client = FakeBaoClient([_daily_row()], [])
    result = _bao_capture(monkeypatch, tmp_path, client)
    assert result["provider_date"] == TARGET
    assert [call[1] for call in client.calls] == [bao_source.DAILY_METHOD, bao_source.FACTOR_METHOD]
    assert all(call[3] == {"date": TARGET} for call in client.calls)


def test_dailyupdates_provider_date_matches_target(monkeypatch, tmp_path):
    client = FakeBaoClient([_daily_row()], [], provider_date="2026-09-27")
    with pytest.raises(BaoStockDailyUpdateError, match="FACTOR_PROVIDER_DATE_MISMATCH"):
        _bao_capture(monkeypatch, tmp_path, client)


def test_dailyupdates_batch_semantics(monkeypatch, tmp_path):
    client = FakeBaoClient([_daily_row(), _daily_row(code="sz.000001")], [])
    result = _bao_capture(monkeypatch, tmp_path, client)
    assert len(client.calls) == 2
    assert all(call[4:] == (20000, 1) for call in client.calls)
    assert result["query_operations"][0]["row_count"] == 2


def test_dailyupdates_adjustment_factor_frozen(monkeypatch, tmp_path):
    factor = _factor_row()
    result = _bao_capture(monkeypatch, tmp_path, FakeBaoClient([_daily_row()], [factor]))
    frozen = json.loads((tmp_path / "snapshots" / "baostock" / "20260928" / result["snapshot_id"] / "daily_update.json").read_text())
    assert frozen["adjustment_factor_rows"] == [factor]
    assert frozen["query_operations"][1]["response_sha256"] == result["query_operations"][1]["response_sha256"]
    assert result["adjustment_factor_role"] == "AUDIT_FACT_NOT_CANONICAL_QFQ_AUTHORITY"


def test_baostock_ohlc_never_substitutes_tdx(monkeypatch, tmp_path):
    result = _bao_capture(monkeypatch, tmp_path, FakeBaoClient([_daily_row()], []))
    assert result["raw_daily_ohlc_authority"] == "TDX_ONLY"
    assert result["bao_stock_ohlc_substitution_permitted"] is False


def test_baostock_tradestatus_crosscheck(monkeypatch, tmp_path):
    row = _daily_row(tradestatus="0", volume="", amount="")
    result = _bao_capture(monkeypatch, tmp_path, FakeBaoClient([row], []))
    assert result["daily_rows"][0]["tradestatus"] == "0"


def test_baostock_isst_crosscheck(monkeypatch, tmp_path):
    row = _daily_row(isST="1")
    result = _bao_capture(monkeypatch, tmp_path, FakeBaoClient([row], []))
    assert result["daily_rows"][0]["isST"] == "1"


def test_baostock_revision_append_only(monkeypatch, tmp_path):
    first = _bao_capture(monkeypatch, tmp_path, FakeBaoClient([_daily_row()], []))
    second = _bao_capture(monkeypatch, tmp_path, FakeBaoClient([_daily_row(close="10.1")], []))
    again = _bao_capture(monkeypatch, tmp_path, FakeBaoClient([_daily_row(close="10.1")], []))
    assert first["snapshot_id"] != second["snapshot_id"]
    assert second["source_revision_id"].endswith("r2")
    assert again["status"] == "NOOP_SOURCE_ALREADY_FROZEN"
    assert again["source_revision_id"] == second["source_revision_id"]


def test_baostock_not_ready_waits(monkeypatch, tmp_path):
    client = FakeBaoClient([], [])
    result = _bao_capture(monkeypatch, tmp_path, client)
    assert result["status"] == "WAIT_BAOSTOCK_DAILY_UPDATE"
    assert [call[1] for call in client.calls] == [bao_source.DAILY_METHOD]


def test_request_budget_enforced(monkeypatch, tmp_path):
    budget = RequestBudget(tmp_path / "ledger.json", hard_limit=1, soft_limit=1)
    client = FakeBaoClient([_daily_row()], [], budget=budget)
    with pytest.raises(BaoStockError, match="SOFT_STOP|HARD_STOP"):
        _bao_capture(monkeypatch, tmp_path, client)


def test_public_sdk_runtime_fingerprint_mismatch_fails_before_query(monkeypatch, tmp_path):
    client = FakeBaoClient([_daily_row()], [])
    changed_sdk = {"package": "baostock", "version": "0.9.4", "installed_python_sources_sha256": "changed-sdk-hash"}
    monkeypatch.setattr(bao_source, "package_metadata", lambda: changed_sdk)
    with pytest.raises(BaoStockDailyUpdateError, match="SDK_FINGERPRINT_MISMATCH"):
        capture_baostock_daily_update(trade_date=TARGET, client=client, snapshot_root=tmp_path / "snapshots",
                                     tdx_root=tmp_path / "client", runtime_acceptance_manifest=_runtime_manifest())
    assert client.calls == []


def test_baostock_runtime_manifest_accepts_fingerprinted_runtime_for_any_auth_mode(monkeypatch, tmp_path):
    sdk = {"package": "baostock", "version": "0.9.5", "installed_python_sources_sha256": "accepted-sdk-hash"}
    client = FakeBaoClient([_daily_row()], [], auth_mode="PUBLIC_ACCOUNT")
    result = _bao_capture(monkeypatch, tmp_path, client, sdk=sdk)
    assert result["sdk"]["version"] == "0.9.5"
    assert result["sdk"]["installed_python_sources_sha256"] == "accepted-sdk-hash"


def test_baostock_runtime_manifest_binds_auth_mode(monkeypatch, tmp_path):
    sdk = {"package": "baostock", "version": "0.9.3", "installed_python_sources_sha256": "sdk-hash"}
    client = FakeBaoClient([_daily_row()], [], auth_mode="PUBLIC_ANONYMOUS")
    manifest = _runtime_manifest(sdk, auth_mode="PUBLIC_ACCOUNT")
    with pytest.raises(BaoStockDailyUpdateError, match="AUTH_MODE_MISMATCH"):
        _bao_capture(monkeypatch, tmp_path, client, sdk=sdk, runtime_manifest=manifest)
    assert client.calls == []


def test_baostock_live_dailyupdates_smoke_receipt_can_activate_dm01(tmp_path):
    seed = _runtime_manifest()
    runtime = seed["runtime"]
    live_smoke = seed["live_smoke"]
    receipt = {
        "contract_id": "BAOSTOCK_DAILY_UPDATE_LIVE_SMOKE_V1",
        "status": "PASS",
        "auth_mode": seed["auth_mode"],
        "runtime": runtime,
        "live_smoke": live_smoke,
    }
    receipt_path = tmp_path / "reports" / "live_smoke_receipt.json"
    receipt_path.parent.mkdir(parents=True)
    receipt_bytes = (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    receipt_path.write_bytes(receipt_bytes)
    manifest = build_runtime_acceptance_manifest(
        sdk=runtime,
        auth_mode=seed["auth_mode"],
        live_smoke=live_smoke,
        smoke_receipt_path="reports/live_smoke_receipt.json",
        smoke_receipt_sha256=hashlib.sha256(receipt_bytes).hexdigest(),
    )
    manifest_path = tmp_path / "reports" / "accepted_runtime_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    loaded = load_runtime_acceptance_manifest(manifest_path, project_root=tmp_path, tdx_root=tmp_path / "tdx-read-only")
    assert runtime_acceptance_error(loaded, sdk=runtime, auth_mode=seed["auth_mode"]) is None


def test_tdx_ready_baostock_not_ready_does_not_promote(tmp_path):
    stage = {"status": "FULL_PASS"}
    tdx = _tdx_ready()
    result = evaluate_daily_source_readiness(trade_date=TARGET, observed_at="2026-09-28T09:00:00+00:00",
                                             official_session_confirmed=True, tdx_capture=tdx,
                                             baostock_capability_accepted=False,
                                             baostock_capture={"status": "WAIT_BAOSTOCK_DAILY_UPDATE"},
                                             gbbq_snapshot=stage, lifecycle_snapshot=stage, special_phase_snapshot=stage)
    assert result["status"] == "WAIT_BAOSTOCK_DAILY_UPDATE"


def test_baostock_ready_tdx_not_ready_does_not_promote():
    result = evaluate_daily_source_readiness(trade_date=TARGET, observed_at="2026-09-28T09:00:00+00:00",
                                             official_session_confirmed=True, tdx_capture={"target_date": TARGET, "update_date": "2026-09-25"},
                                             baostock_capability_accepted=True,
                                             baostock_capture={"status": "BAOSTOCK_DAILY_SNAPSHOT_READY"},
                                             gbbq_snapshot={"status": "READY"}, lifecycle_snapshot={"status": "READY"},
                                             special_phase_snapshot={"status": "READY"})
    assert result["status"] == "WAIT_TDX_PUBLICATION"


def test_local_tdx_tail_cannot_enable_official_source_readiness():
    # The orchestrator has no local-vipdoc date input; without a dated official
    # page/package capture, a BaoStock row or local tail cannot make TDX ready.
    result = evaluate_daily_source_readiness(
        trade_date=TARGET, observed_at="2026-09-28T09:00:00+00:00", official_session_confirmed=True,
        tdx_capture=None, baostock_capture=_bao_ready(), baostock_capability_accepted=True,
        gbbq_snapshot={"status": "READY"}, lifecycle_snapshot={"status": "READY"},
        special_phase_snapshot={"status": "READY"},
    )
    assert result["status"] == "WAIT_TDX_PUBLICATION"


def _source_freeze(delta_sha="delta-sha", snapshot="tdx-snapshot"):
    sources = {}
    for family in (
        "TDX_PAGE_CAPTURE", "TDX_FULL_PACKAGE", "TDX_PACKAGE_DELTA", "OFFICIAL_CALENDAR",
        "BAOSTOCK_DAILY_UPDATE", "BAOSTOCK_ADJUSTMENT_FACTOR", "GBBQ", "IDENTITY_LIFECYCLE", "SPECIAL_PRICE_PHASE",
    ):
        sources[family] = {"source_revision": snapshot if family == "TDX_FULL_PACKAGE" else family + "-r1",
                           "sha256": delta_sha if family == "TDX_PACKAGE_DELTA" else hashlib.sha256(family.encode()).hexdigest(),
                           "bytes": 1}
    return build_source_freeze_manifest_v2(
        trade_date=TARGET, sources=sources, changed_tdx_files=[],
        observed_at="2026-09-28T09:00:00+00:00", ingested_at="2026-09-28T09:00:00+00:00",
        system_available_at="2026-09-28T09:00:00+00:00",
    )


def _all_builders(staging_root):
    result = {}
    for capability in CAPABILITIES:
        def builder(*, capability, **kwargs):
            path = staging_root / f"{capability}.artifact"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(capability, encoding="utf-8")
            return {"contract_id": f"{capability}_INCREMENT_V1", "version": "1.0.0", "status": "FULL_PASS",
                    "artifact": {"path": str(path), "sha256": hashlib.sha256(capability.encode()).hexdigest()}}
        result[capability] = builder
    return result


def _increment_env(tmp_path):
    tdx_root = tmp_path / "read-only-tdx"
    tdx_root.mkdir()
    staging = tmp_path / "staging"
    head = tmp_path / "data_head.json"
    stage = tmp_path / "stage_head.json"
    dev = tmp_path / "dev_head.json"
    head.write_text(json.dumps({"accepted_trade_date": "2026-09-24"}), encoding="utf-8")
    stage.write_text("stage-accepted", encoding="utf-8")
    dev.write_text("dev-baseline", encoding="utf-8")
    return tdx_root, staging, head, stage, dev


def _run_increment(tmp_path, *, postcheck=lambda _: "PASS"):
    tdx_root, staging, head, stage, dev = _increment_env(tmp_path)
    delta = {"status": "READY", "target_date": TARGET, "current_snapshot_id": "tdx-snapshot",
             "delta_sha256": "delta-sha", "target_bars": [{"security_id": "SH.600000", "trade_date": TARGET_NUMBER}]}
    results = run_incremental_components(
        trade_date=TARGET, source_freeze=_source_freeze(), tdx_delta=delta, parent_artifacts={},
        builders=_all_builders(staging), staging_root=staging, head_path=head, stage_head_path=stage,
        dev_baseline_path=dev, independent_postcheck=postcheck, tdx_root=tdx_root,
    )
    return results, head, stage, dev


def test_both_ready_builds_target_session(tmp_path):
    source = {"status": "READY"}
    state = evaluate_daily_source_readiness(
        trade_date=TARGET, observed_at="2026-09-28T09:00:00+00:00", official_session_confirmed=True,
        tdx_capture=_tdx_ready(),
        baostock_capture=_bao_ready(), baostock_capability_accepted=True,
        gbbq_snapshot=source, lifecycle_snapshot=source, special_phase_snapshot=source,
    )
    assert state["status"] == "SOURCE_FREEZE_READY"
    result, head, stage, dev = _run_increment(tmp_path)
    assert result["status"] == "PROMOTED"
    assert json.loads(head.read_text())["accepted_trade_date"] == TARGET
    assert stage.read_text() == "stage-accepted"
    assert dev.read_text() == "dev-baseline"


def test_tdx_baostock_price_conflict_keeps_tdx_authority():
    tdx_rows = [{"security_id": "SH.600000", "close": 10.0, "volume": 1000, "amount": 10000}]
    bao_rows = [{"code": "sh.600000", "close": "9.9", "volume": "1000", "amount": "10000", "tradestatus": "0"}]
    result = crosscheck_tdx_with_baostock(trade_date=TARGET, tdx_rows=tdx_rows, baostock_rows=bao_rows)
    assert result["status"] == "CONFLICTS_FOUND"
    assert result["gate_effect"] == "DIAGNOSTIC_ONLY"
    assert result["data_head_blocking"] is False
    assert result["tdx_remains_canonical_authority"] is True
    assert result["baostock_rows_promoted_to_raw"] is False


def test_suspended_stock_without_tdx_bar_is_valid_with_status_evidence():
    result = classify_trading_status(calendar_is_session=True, lifecycle_active=True, actual_bar_present=False,
                                     dated_provider_tradestatus="0", previous_official_close=10.0)
    assert result["status"] == BAR_STATUS_SUSPENDED
    assert result["close_carry"] == 10.0


def test_missing_trading_stock_tdx_bar_is_source_gap():
    result = classify_trading_status(calendar_is_session=True, lifecycle_active=True, actual_bar_present=False,
                                     dated_provider_tradestatus="1", previous_official_close=10.0)
    assert result["status"] == BAR_STATUS_UNKNOWN


def test_source_revision_rebuilds_affected_scope_only():
    impact = affected_component_scopes({"target_bars": [], "revision_events": [{"security_id": "SH.600000"}]})
    assert impact["historical_revision_components"] == [
        "RAW_DAILY", "ADJUSTED_DAILY", "PERIOD_RAW", "PERIOD_ADJUSTED", "PRICE_LIMIT"
    ]
    assert impact["revision_security_ids"] == ["SH.600000"]
    assert impact["full_history_rebuild"] is False


def test_stage_and_dev_heads_never_move(tmp_path):
    before_stage = b"stage-accepted"
    before_dev = b"dev-baseline"
    result, _head, stage, dev = _run_increment(tmp_path)
    assert result["status"] == "PROMOTED"
    assert stage.read_bytes() == before_stage
    assert dev.read_bytes() == before_dev


def test_atomic_failure_keeps_previous_data_head(tmp_path):
    result, head, _stage, _dev = _run_increment(tmp_path, postcheck=lambda _: "FAIL")
    assert result["status"] == "BLOCKED"
    assert result["data_head_moved"] is False
    assert json.loads(head.read_text())["accepted_trade_date"] == "2026-09-24"


def test_raw_increment_staging_never_uses_baostock(tmp_path):
    delta = {"status": "READY", "target_date": TARGET, "current_snapshot_id": "tdx-snapshot",
             "target_bars": [{"security_id": "SH.600000", "trade_date": TARGET_NUMBER,
                              "open": 10.0, "high": 10.0, "low": 10.0, "close": 10.0,
                              "amount": 10000.0, "volume": 1000}]}
    artifact = build_raw_increment_staging(trade_date=TARGET, source_snapshot_id="tdx-snapshot", delta=delta,
                                           output_path=tmp_path / "raw.jsonl",
                                           tdx_root=tmp_path / "read-only-tdx")
    row = json.loads((tmp_path / "raw.jsonl").read_text().strip())
    assert artifact["bao_stock_ohlc_used"] is False
    assert row["canonical_security_id"] is None
    assert row["source_authority"] == "TDX_OFFICIAL_PACKAGE"


def _gbbq_fixture(tmp_path, *, changed=False, missing_source=False):
    tdx_root = tmp_path / "tdx"
    source_root = tdx_root / "vipdoc" / "cw"
    accepted_root = tmp_path / "project" / "accepted_gbbq"
    output_root = tmp_path / "project" / "source_snapshot_store"
    source_root.mkdir(parents=True)
    accepted_root.mkdir(parents=True)
    contents = {"gbbq": b"accepted-gbbq", "gbbq.map": b"accepted-map"}
    files = {}
    for name, raw in contents.items():
        (accepted_root / name).write_bytes(raw)
        files[name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "path": name}
        if not missing_source:
            current = raw + b"-revision" if changed and name == "gbbq" else raw
            (source_root / name).write_bytes(current)
    (accepted_root / "manifest.json").write_text(json.dumps({
        "contract_id": "V4_02_GBBQ_FORWARD_SNAPSHOT_V1",
        "snapshot_id": "sha256-accepted",
        "files": files,
        "first_eligible_formal_trade_date": TARGET,
        "immutable": True,
    }), encoding="utf-8")
    result = probe_gbbq_source_revision(
        target_date=TARGET,
        current_source_root=source_root,
        accepted_snapshot_root=accepted_root,
        output_snapshot_root=output_root,
        observed_at="2026-09-28T07:00:00+00:00",
        official_sessions_after_target=["2026-09-29"],
        tdx_root=tdx_root,
    )
    return result, source_root, output_root


def test_gbbq_unchanged_revision_reuses_existing_snapshot(tmp_path):
    result, _source_root, output_root = _gbbq_fixture(tmp_path)
    assert result["status"] == "REUSE_ACCEPTED_GBBQ_SNAPSHOT"
    assert result["accepted_snapshot_id"] == "sha256-accepted"
    assert not (output_root / "gbbq").exists()


def test_gbbq_changed_revision_freezes_new_snapshot(tmp_path):
    result, source_root, output_root = _gbbq_fixture(tmp_path, changed=True)
    assert result["status"] == "NEW_GBBQ_REVISION_FROZEN_REQUIRES_ADJUSTMENT_IMPACT"
    assert result["eligible_for_target_date"] is False
    snapshot = output_root / "gbbq" / result["new_snapshot_id"]
    assert (snapshot / "gbbq").read_bytes() == (source_root / "gbbq").read_bytes()
    assert result["tdx_root_write_count"] == 0


def test_gbbq_missing_local_source_does_not_claim_reuse(tmp_path):
    result, _source_root, _output_root = _gbbq_fixture(tmp_path, missing_source=True)
    assert result["status"] == "WAIT_GBBQ_CURRENT_SOURCE_UNAVAILABLE"
    assert set(result["missing_source_files"]) == {"gbbq", "gbbq.map"}


def test_no_special_event_still_produces_valid_source_manifest(tmp_path):
    event_path = tmp_path / "data" / "special_events.jsonl"
    policy_path = tmp_path / "config" / "special_policy.json"
    event_path.parent.mkdir(parents=True)
    policy_path.parent.mkdir(parents=True)
    event_path.write_text("", encoding="utf-8")
    policy_path.write_text(json.dumps({"contract_id": "SPECIAL_PRICE_PHASE_POLICY_V1",
                                      "policies": [{"phase": "REGULAR", "valid_from": "2020-01-01"}]}),
                           encoding="utf-8")
    stage_manifest_path = tmp_path / "reports" / "v402_manifest.json"
    stage_manifest_path.parent.mkdir(parents=True)
    stage_manifest = {"components": {
        "R6_EVENTS": {"path": "data/special_events.jsonl", "sha256": hashlib.sha256(b"").hexdigest(), "bytes": 0},
        "R6_POLICY": {"path": "config/special_policy.json", "sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
                      "bytes": policy_path.stat().st_size},
    }}
    stage_manifest_bytes = (json.dumps(stage_manifest, sort_keys=True, indent=2) + "\n").encode()
    stage_manifest_path.write_bytes(stage_manifest_bytes)
    acceptance_path = tmp_path / "reports" / "v402_acceptance.json"
    acceptance_path.write_text(json.dumps({
        "acceptance_result": {"external_acceptance": "EXTERNALLY_ACCEPTED"},
        "evidence": {"manifest": {"sha256": hashlib.sha256(stage_manifest_bytes).hexdigest()}},
    }), encoding="utf-8")
    lifecycle_artifact = tmp_path / "reports" / "current_lifecycle.json"
    lifecycle_artifact.write_text(json.dumps({"trade_date": TARGET, "active_security_ids": []}), encoding="utf-8")
    lifecycle = {
        "contract_id": "CURRENT_LIFECYCLE_SNAPSHOT_V1",
        "status": "READY",
        "trade_date": TARGET,
        "artifact_path": "reports/current_lifecycle.json",
        "artifact_sha256": hashlib.sha256(lifecycle_artifact.read_bytes()).hexdigest(),
        "source_revision": "lifecycle-r1",
        "active_security_ids": [],
    }
    result = build_special_phase_source_manifest(
        trade_date=TARGET,
        project_root=tmp_path,
        v402_external_acceptance_path=acceptance_path,
        v402_stage_manifest_path=stage_manifest_path,
        event_store_path=event_path,
        policy_path=policy_path,
        lifecycle_snapshot=lifecycle,
        observed_at="2026-09-28T07:00:00+00:00",
        tdx_root=tmp_path / "tdx-read-only",
    )
    assert result["status"] == "READY"
    assert result["event_status"] == "NO_NEW_SPECIAL_PHASE_EVENT"
    assert result["active_event_count"] == 0
    assert len(result["manifest_sha256"]) == 64


def test_no_identity_event_still_produces_valid_lifecycle_snapshot():
    identities = [
        {"source_security_key": "SH.600000", "security_id": "SEC-SH600000", "board": "SH_MAIN",
         "security_type": "A_STOCK", "list_date": "1999-11-10"},
        {"source_security_key": "SZ.000001", "security_id": "SEC-SZ000001", "board": "SZ_MAIN",
         "security_type": "A_STOCK", "list_date": "1991-04-03"},
    ]
    manifest = build_current_lifecycle_snapshot(
        trade_date=TARGET,
        baseline_date="2026-09-24",
        baseline_data_head={
            "accepted_trade_date": "2026-09-24",
            "component_permissions": {"IDENTITY_UNIVERSE": {"cutoff": "2026-09-24", "status": "FULL_PASS"}},
        },
        parent_universe_rows=[{"trade_date": "2026-09-24", "source_security_key": row["source_security_key"]}
                              for row in identities],
        identity_records=identities,
        baostock_snapshot={
            "status": "BAOSTOCK_DAILY_SNAPSHOT_READY", "trade_date": TARGET, "provider_date": TARGET,
            "snapshot_id": "sha256-test-roster", "daily_rows": [
                {"code": "sh.600000", "date": TARGET}, {"code": "sz.000001", "date": TARGET},
            ],
        },
        official_session_bridge={
            "status": "PASS", "latest_completed_official_session": "2026-09-24",
            "official_sessions_after_base_cutoff": [TARGET],
        },
        source_evidence={"baseline_data_head_sha256": "parent-head", "baostock_snapshot_sha256": "bao"},
        observed_at="2026-09-28T07:10:00+00:00",
    )
    assert manifest["status"] == "READY"
    assert manifest["event_status"] == "PASS_NO_IDENTITY_EVENT"
    assert manifest["active_security_ids"] == ["SEC-SH600000", "SEC-SZ000001"]
    assert manifest["absence_is_delisting_evidence"] is False


def test_unmapped_new_lifecycle_candidate_only_degrades_affected_security():
    identities = [
        {"source_security_key": "SH.600000", "security_id": "SEC-SH600000", "board": "SH_MAIN",
         "security_type": "A_STOCK", "list_date": "1999-11-10"},
    ]
    manifest = build_current_lifecycle_snapshot(
        trade_date=TARGET,
        baseline_date="2026-09-24",
        baseline_data_head={
            "accepted_trade_date": "2026-09-24",
            "component_permissions": {"IDENTITY_UNIVERSE": {"cutoff": "2026-09-24", "status": "FULL_PASS"}},
        },
        parent_universe_rows=[{"trade_date": "2026-09-24", "source_security_key": "SH.600000"}],
        identity_records=identities,
        baostock_snapshot={
            "status": "BAOSTOCK_DAILY_SNAPSHOT_READY", "trade_date": TARGET, "provider_date": TARGET,
            "snapshot_id": "sha256-test-roster", "daily_rows": [
                {"code": "sh.600000", "date": TARGET}, {"code": "sh.688999", "date": TARGET},
            ],
        },
        official_session_bridge={
            "status": "PASS", "latest_completed_official_session": "2026-09-24",
            "official_sessions_after_base_cutoff": [TARGET],
        },
        source_evidence={"baseline_data_head_sha256": "parent-head", "baostock_snapshot_sha256": "bao"},
        observed_at="2026-09-28T07:10:00+00:00",
    )
    assert manifest["status"] == "DEGRADED_PASS"
    assert manifest["event_status"] == "NEW_SOURCE_KEYS_ISOLATED_UNKNOWN"
    assert manifest["unknown_source_keys"] == ["SH.688999"]
    assert manifest["active_security_ids"] == ["SEC-SH600000"]


def test_real_independent_postcheck_reads_artifacts(tmp_path):
    families = (
        "TDX_PAGE_CAPTURE", "TDX_FULL_PACKAGE", "TDX_PACKAGE_DELTA", "OFFICIAL_CALENDAR",
        "BAOSTOCK_DAILY_UPDATE", "BAOSTOCK_ADJUSTMENT_FACTOR", "GBBQ", "IDENTITY_LIFECYCLE", "SPECIAL_PRICE_PHASE",
    )
    source_files = {}
    package_sha = "1" * 64
    snapshot_id = "sha256-" + package_sha
    for family in families:
        if family == "TDX_FULL_PACKAGE":
            path = tmp_path / "tdx" / snapshot_id / "hsjday.zip"
            path.parent.mkdir(parents=True)
            content = b"z"
            source_revision = snapshot_id
            source_sha = package_sha
        elif family == "TDX_PAGE_CAPTURE":
            path = tmp_path / f"source_{family}.json"
            content = json.dumps({"target_date": TARGET, "update_date": TARGET, "snapshot_id": snapshot_id,
                                  "download": {"sha256": package_sha}}).encode()
            source_revision = family + "-r1"
            source_sha = hashlib.sha256(content).hexdigest()
        elif family == "TDX_PACKAGE_DELTA":
            path = tmp_path / f"source_{family}.json"
            content = json.dumps({"target_date": TARGET, "current_snapshot_id": snapshot_id,
                                  "delta_sha256": "delta-sha"}).encode()
            source_revision = "delta-sha"
            source_sha = hashlib.sha256(content).hexdigest()
        else:
            path = tmp_path / f"source_{family}.json"
            content = family.encode()
            source_revision = family + "-r1"
            source_sha = hashlib.sha256(content).hexdigest()
        path.write_bytes(content)
        source_files[family] = {
            "path": str(path), "source_revision": source_revision,
            "sha256": source_sha, "bytes": len(content),
        }
    source_freeze = build_source_freeze_manifest_v2(
        trade_date=TARGET, sources=source_files, changed_tdx_files=[],
        observed_at="2026-09-28T09:00:00+00:00", ingested_at="2026-09-28T09:00:00+00:00",
        system_available_at="2026-09-28T09:00:00+00:00",
    )
    keys = [
        {"security_id": "SEC-SH600000", "trade_date": TARGET_NUMBER},
        {"security_id": "SEC-SZ000001", "trade_date": TARGET_NUMBER},
    ]
    component_receipts = {}
    for capability in CAPABILITIES:
        rows = [dict(row) for row in keys]
        if capability == "TRADING_STATUS":
            for row in rows:
                row.update({"status": "TRADING", "actual_bar_present": True})
        if capability == "RAW_DAILY":
            for row in rows:
                row.update({"source_snapshot_id": snapshot_id, "source_authority": "TDX_OFFICIAL_PACKAGE",
                            "bao_stock_ohlc_used": False, "bao_stock_ohlc_substitution_permitted": False})
        if capability == "ADJUSTED_DAILY":
            for row in rows:
                row["adjustment_readiness"] = "READY"
        payload = {"contract_id": f"{capability}_ARTIFACT_V1", "trade_date": TARGET, "rows": rows}
        artifact_path = tmp_path / f"{capability}.json"
        artifact_bytes = json.dumps(payload, sort_keys=True).encode()
        artifact_path.write_bytes(artifact_bytes)
        component_receipts[capability] = {
            "contract_id": f"{capability}_INCREMENT_V1", "version": "1.0.0", "status": "FULL_PASS",
            "trade_date": TARGET, "row_count": len(rows),
            "input_source_revisions": {
                name: source_freeze["source_families"][name]["source_revision"]
                for name in ("TDX_FULL_PACKAGE", "TDX_PACKAGE_DELTA")
            },
            "parent_artifact_revision": None, "elapsed_ms": 1,
            "unknown_or_degraded_rows": [],
            "artifact": {"path": str(artifact_path), "sha256": hashlib.sha256(artifact_bytes).hexdigest()},
        }
    stage_path = tmp_path / "stage_head.json"
    dev_path = tmp_path / "dev_head.json"
    data_path = tmp_path / "data_head.json"
    stage_path.write_text("stage", encoding="utf-8")
    dev_path.write_text("dev", encoding="utf-8")
    data_path.write_text("data", encoding="utf-8")
    stage_hash = hashlib.sha256(b"stage").hexdigest()
    dev_hash = hashlib.sha256(b"dev").hexdigest()
    result = independent_daily_increment_postcheck(
        trade_date=TARGET, source_freeze=source_freeze, component_receipts=component_receipts,
        data_head_path=data_path, stage_head_path=stage_path, dev_baseline_path=dev_path,
        expected_data_head_sha256=hashlib.sha256(b"data").hexdigest(),
        expected_stage_head_sha256=stage_hash, expected_dev_baseline_sha256=dev_hash,
        tdx_root=tmp_path / "tdx-read-only",
    )
    assert result["status"] == "PASS"
    assert result["data_head_promotion_permitted"] is True
    assert result["checks"]["trading_status_covers_raw_bars"] == "PASS"


def test_fake_artifact_builders_do_not_pass_real_postcheck(tmp_path):
    tdx_root, staging, head, stage, dev = _increment_env(tmp_path)
    source_freeze = _source_freeze()
    callback = make_independent_postcheck_callback(
        staging_root=staging, report_root=tmp_path / "postcheck",
        data_head_path=head, stage_head_path=stage, dev_baseline_path=dev,
        source_freeze=source_freeze, tdx_root=tdx_root,
    )
    delta = {"status": "READY", "target_date": TARGET, "current_snapshot_id": "tdx-snapshot",
             "delta_sha256": "delta-sha", "target_bars": [{"security_id": "SH.600000", "trade_date": TARGET_NUMBER}]}
    result = run_incremental_components(
        trade_date=TARGET, source_freeze=source_freeze, tdx_delta=delta, parent_artifacts={},
        builders=_all_builders(staging), staging_root=staging, head_path=head, stage_head_path=stage,
        dev_baseline_path=dev, independent_postcheck=callback, tdx_root=tdx_root,
    )
    assert result["status"] == "BLOCKED"
    assert result["promotion"]["head_moved"] is False
    assert json.loads(head.read_text(encoding="utf-8"))["accepted_trade_date"] == "2026-09-24"
