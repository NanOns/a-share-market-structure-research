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
from workbench_analysis.daily_source_freeze import build_source_freeze_manifest_v2
from workbench_analysis.daily_source_orchestrator import evaluate_daily_source_readiness
from workbench_analysis.tdx_official_daily_source import TDXSourceError
from workbench_analysis.tdx_snapshot_delta import TDXDeltaError, build_tdx_package_delta


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
    def __init__(self, daily_rows=None, factor_rows=None, *, provider_date=TARGET, budget=None):
        self.logged_in = True
        self.sdk = FakeSDK()
        self.auth_mode = "PUBLIC_ANONYMOUS"
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


def _bao_capture(monkeypatch, tmp_path, client):
    monkeypatch.setattr(bao_source, "package_metadata", lambda: {
        "package": "baostock", "version": "0.9.3", "installed_python_sources_sha256": "sdk-hash"
    })
    return capture_baostock_daily_update(trade_date=TARGET, client=client, snapshot_root=tmp_path / "snapshots",
                                         tdx_root=tmp_path / "client" / "vipdoc",
                                         observed_at="2026-09-28T09:00:00+00:00")


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


def test_public_sdk_runtime_pin_mismatch_fails_before_query(monkeypatch, tmp_path):
    client = FakeBaoClient([_daily_row()], [])
    monkeypatch.setattr(bao_source, "package_metadata", lambda: {
        "package": "baostock", "version": "0.9.4", "installed_python_sources_sha256": "sdk-hash"
    })
    with pytest.raises(BaoStockDailyUpdateError, match="RUNTIME_AUTH_PIN_MISMATCH"):
        capture_baostock_daily_update(trade_date=TARGET, client=client, snapshot_root=tmp_path / "snapshots",
                                     tdx_root=tmp_path / "client")
    assert client.calls == []


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
