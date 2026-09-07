from __future__ import annotations

from datetime import date
import inspect
import json
import os
from pathlib import Path
import struct

import pandas as pd
import pytest

from common.identity import computation_identity
from common.run_lock import ActiveRunLock, RunLock
from common.snapshot_reader import read_snapshot
from production import daily
from production.daily import (
    EXIT_BINDING,
    EXIT_NOT_READY,
    EXIT_PUBLICATION,
    FailureRecord,
    build_reports,
    freshness_decision,
    latest_resolution,
    universe_snapshot,
    validate_universe_binding,
)
from production.release import (
    PublicationValidationError,
    atomic_write_json,
    publish_generation,
    sha256,
    validate_release_generation,
)


FAILURE_POINTS = (
    "FAIL_BEFORE_REPORT_BUILD",
    "FAIL_AFTER_SECTORS_CSV",
    "FAIL_AFTER_STOCKS_CSV",
    "FAIL_AFTER_CANDIDATES_CSV",
    "FAIL_AFTER_HTML",
    "FAIL_BEFORE_MANIFEST",
    "FAIL_AFTER_MANIFEST",
    "FAIL_BEFORE_RECEIPT",
    "FAIL_AFTER_RECEIPT",
    "FAIL_BEFORE_POINTER_SWAP",
    "FAIL_DURING_POINTER_SWAP",
)


def _release_files(path: Path, run_id: str) -> None:
    path.mkdir(parents=True)
    payloads = {
        "market_summary.html": b"<html>local</html>",
        "sectors.csv": b"sector_id\n",
        "stocks.csv": b"security_id\n",
        "candidates.csv": b"security_id\n",
        "run_audit.json": b"{}\n",
        "PERFORMANCE_AUDIT.json": b"{}\n",
        "INPUT_SNAPSHOT_MANIFEST.json": b"{}\n",
    }
    for name, payload in payloads.items():
        (path / name).write_bytes(payload)
    manifest = {
        "production_version": "daily-production-v1.2",
        "files": [
            {"filename": name, "sha256": sha256(path / name)}
            for name in payloads
        ],
    }
    atomic_write_json(path / "manifest.json", manifest)
    atomic_write_json(
        path / "PRODUCTION_RECEIPT.json",
        {"run_id": run_id, "manifest_sha256": sha256(path / "manifest.json")},
    )


def _simulate_failed_publication(root: Path, point: str) -> dict:
    old = root / "old"
    _release_files(old, "old")
    pointer = root / "current.json"
    atomic_write_json(pointer, {"run_id": "old", "release_path": str(old)})
    before = pointer.read_bytes()
    new = root / "new"

    def fail(label: str) -> None:
        if label == point:
            raise PublicationValidationError("INJECTED_FAILURE:" + label)

    try:
        fail("FAIL_BEFORE_REPORT_BUILD")
        new.mkdir()
        for name, label, payload in (
            ("sectors.csv", "FAIL_AFTER_SECTORS_CSV", b"sector_id\n"),
            ("stocks.csv", "FAIL_AFTER_STOCKS_CSV", b"security_id\n"),
            ("candidates.csv", "FAIL_AFTER_CANDIDATES_CSV", b"security_id\n"),
            ("market_summary.html", "FAIL_AFTER_HTML", b"<html>local</html>"),
        ):
            (new / name).write_bytes(payload)
            fail(label)
        (new / "run_audit.json").write_text("{}\n", encoding="utf8")
        (new / "PERFORMANCE_AUDIT.json").write_text("{}\n", encoding="utf8")
        (new / "INPUT_SNAPSHOT_MANIFEST.json").write_text("{}\n", encoding="utf8")
        fail("FAIL_BEFORE_MANIFEST")
        manifest = {
            "production_version": "daily-production-v1.2",
            "files": [
                {"filename": name, "sha256": sha256(new / name)}
                for name in (
                    "market_summary.html", "sectors.csv", "stocks.csv",
                    "candidates.csv", "run_audit.json", "PERFORMANCE_AUDIT.json",
                    "INPUT_SNAPSHOT_MANIFEST.json",
                )
            ],
        }
        atomic_write_json(new / "manifest.json", manifest)
        fail("FAIL_AFTER_MANIFEST")
        fail("FAIL_BEFORE_RECEIPT")
        atomic_write_json(
            new / "PRODUCTION_RECEIPT.json",
            {"run_id": "new", "manifest_sha256": sha256(new / "manifest.json")},
        )
        fail("FAIL_AFTER_RECEIPT")
        publish_generation(new, pointer, {"run_id": "new", "release_path": str(new)}, failure_hook=fail)
    except PublicationValidationError as exc:
        return {
            "exception": str(exc),
            "old_release_exists": old.exists(),
            "old_pointer_unchanged": pointer.read_bytes() == before,
            "new_invalid_release_not_current": json.loads(pointer.read_text("utf8"))["run_id"] != "new",
            "reader_visible_generation": "FULL_OLD" if validate_release_generation(old) else "PARTIAL",
        }
    raise AssertionError("failure injection did not fire: " + point)


@pytest.mark.parametrize("point", FAILURE_POINTS)
def test_all_release_failure_points_preserve_old_pointer(tmp_path, point):
    result = _simulate_failed_publication(tmp_path, point)
    assert result["old_release_exists"]
    assert result["old_pointer_unchanged"]
    assert result["new_invalid_release_not_current"]
    assert result["reader_visible_generation"] == "FULL_OLD"


def test_successful_pointer_swap_exposes_full_new_and_has_no_post_swap_veto(tmp_path):
    old = tmp_path / "old"
    new = tmp_path / "new"
    _release_files(old, "old")
    _release_files(new, "new")
    pointer = tmp_path / "current.json"
    atomic_write_json(pointer, {"run_id": "old", "release_path": str(old)})
    publish_generation(new, pointer, {"run_id": "new", "release_path": str(new)})
    visible = json.loads(pointer.read_text("utf8"))
    assert visible["run_id"] == "new"
    assert validate_release_generation(visible["release_path"])["receipt"]["run_id"] == "new"
    source_after_commit = inspect.getsource(publish_generation).split("atomic_write_json(pointer", 1)[1]
    assert "validate_release_generation" not in source_after_commit
    assert "failure_hook" not in source_after_commit


def _write_day(tdx: Path, market: str, code: str, session: int) -> None:
    path = tdx / "vipdoc" / market.lower() / "lday" / f"{market.lower()}{code}.day"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(struct.pack("<8I", session, 1, 1, 1, 1, 1, 1, 1))


def _calendar_root(tmp_path: Path, master: int, extra_rows=()) -> Path:
    root = tmp_path / "project"
    target = root / "reports" / "phase0_1"
    target.mkdir(parents=True)
    rows = [{"calendar_date": master, "is_market_open": True}]
    rows.extend(extra_rows)
    pd.DataFrame(rows).to_csv(target / "MASTER_TRADING_CALENDAR.csv", index=False)
    return root


def _complete_market(tdx: Path, session: int, *, suspended: tuple[str, str] | None = None) -> None:
    codes = {
        "SH": ("000001", "600001", "600002"),
        "SZ": ("399001", "000001", "000002"),
        "BJ": ("430001", "430002", "430003"),
    }
    for market, market_codes in codes.items():
        for code in market_codes:
            value = session - 3 if suspended == (market, code) else session
            _write_day(tdx, market, code, value)


@pytest.mark.parametrize(
    "master,new_session",
    ((20260904, 20260907), (20260907, 20260908)),
)
def test_normal_new_trading_day_is_not_ambiguous(tmp_path, master, new_session):
    root = _calendar_root(tmp_path, master)
    tdx = tmp_path / "tdx"
    _complete_market(tdx, new_session)
    result = latest_resolution(root, tdx, as_of=date(new_session // 10000, (new_session // 100) % 100, new_session % 100))
    assert result["cutoff_status"] == "NORMAL_NEW_TRADING_DAY"
    assert result["resolved_cutoff_date"] == str(new_session)


def test_weekend_and_holiday_no_new_data(tmp_path):
    tdx = tmp_path / "tdx"
    _complete_market(tdx, 20260904)
    weekend_root = _calendar_root(tmp_path / "weekend", 20260904)
    weekend = latest_resolution(weekend_root, tdx, as_of=date(2026, 9, 6))
    assert weekend["cutoff_status"] == "WEEKEND_NO_NEW_DATA"
    holiday_root = _calendar_root(
        tmp_path / "holiday", 20260904,
        ({"calendar_date": 20260907, "is_market_open": False},),
    )
    holiday = latest_resolution(holiday_root, tdx, as_of=date(2026, 9, 7))
    assert holiday["cutoff_status"] == "HOLIDAY_NO_NEW_DATA"


@pytest.mark.parametrize("updated_market", ("SH", "SZ", "BJ"))
def test_partial_market_update_is_blocked(tmp_path, updated_market):
    root = _calendar_root(tmp_path, 20260904)
    tdx = tmp_path / "tdx"
    _complete_market(tdx, 20260904)
    codes = {"SH": ("000001", "600001", "600002"), "SZ": ("399001", "000001", "000002"), "BJ": ("430001", "430002", "430003")}
    for code in codes[updated_market]:
        _write_day(tdx, updated_market, code, 20260907)
    result = latest_resolution(root, tdx, as_of=date(2026, 9, 7))
    assert result["cutoff_status"] == "PARTIAL_UPDATE"
    assert result["resolved_cutoff_date"] == "20260904"


def test_small_future_outlier_is_invalid(tmp_path):
    root = _calendar_root(tmp_path, 20260904)
    tdx = tmp_path / "tdx"
    _complete_market(tdx, 20260904)
    _write_day(tdx, "SH", "600002", 20260908)
    result = latest_resolution(root, tdx, as_of=date(2026, 9, 7))
    assert result["cutoff_status"] == "INVALID_FUTURE_OUTLIER"
    assert result["resolved_cutoff_date"] == "20260904"


def test_new_listing_and_suspended_file_do_not_block_broad_update(tmp_path):
    root = _calendar_root(tmp_path, 20260904)
    tdx = tmp_path / "tdx"
    _complete_market(tdx, 20260907, suspended=("BJ", "430003"))
    _write_day(tdx, "SH", "605999", 20260907)  # new listing with only the latest bar
    result = latest_resolution(root, tdx, as_of=date(2026, 9, 7))
    assert result["cutoff_status"] == "NORMAL_NEW_TRADING_DAY"


def test_input_not_ready_when_all_sources_lag_calendar(tmp_path):
    root = _calendar_root(tmp_path, 20260907)
    tdx = tmp_path / "tdx"
    _complete_market(tdx, 20260904)
    result = latest_resolution(root, tdx, as_of=date(2026, 9, 7))
    assert result["cutoff_status"] == "INPUT_NOT_READY"


@pytest.mark.parametrize("count", (5460, 5461, 5462))
def test_dynamic_universe_accepts_variable_valid_counts(count):
    ids = [f"SH.{value:06d}" for value in range(count)]
    snap = universe_snapshot(pd.DataFrame({"security_id": ids}), "20260904", "generation-a")
    assert snap["count"] == count
    assert validate_universe_binding(snap, reversed(ids), "generation-a")


def test_dynamic_universe_rejects_all_identity_binding_failures():
    ids = ["SH.000001", "SZ.000001"]
    snap = universe_snapshot(pd.DataFrame({"security_id": ids}), "20260904", "generation-a")
    with pytest.raises(RuntimeError, match="IDENTITY_MISMATCH"):
        validate_universe_binding(snap, ["SH.000001", "BJ.000001"])
    with pytest.raises(RuntimeError, match="DUPLICATE"):
        validate_universe_binding(snap, ["SH.000001", "SH.000001"])
    with pytest.raises(RuntimeError, match="IDENTITY_MISMATCH"):
        validate_universe_binding(snap, ["SH.000001"])
    with pytest.raises(RuntimeError, match="IDENTITY_MISMATCH"):
        validate_universe_binding(snap, [*ids, "BJ.000001"])
    with pytest.raises(RuntimeError, match="GENERATION_MISMATCH"):
        validate_universe_binding(snap, ids, "generation-b")


def test_multidate_single_two_three_revision_and_future(tmp_path):
    path = tmp_path / "snap.parquet"
    for dates in ([20260904], [20260903, 20260904], [20260902, 20260903, 20260904]):
        pd.DataFrame({"date": dates, "value": range(len(dates))}).to_parquet(path)
        current = read_snapshot(path, 20260904)
        assert len(current) == 1
        assert len(pd.read_parquet(path)) == len(dates)
    pd.DataFrame({"date": [20260903, 20260904], "value": [1, 7]}).to_parquet(path)
    assert read_snapshot(path, 20260904).value.tolist() == [7]
    pd.DataFrame({"date": [20260903, 20260904, 20260905], "value": [1, 2, 3]}).to_parquet(path)
    with pytest.raises(ValueError, match="FUTURE_SNAPSHOT"):
        read_snapshot(path, 20260904)


def test_all_identity_decisions_and_computation_contents(tmp_path):
    same = {"sha256": "same"}
    old = {"cutoff_date": "20260904", "source_fingerprint": "source", "source_identity": same, "computation_identity": same, "render_identity": same}
    current = {"source_fingerprint": "source", "source_identity": same, "computation_identity": same, "render_identity": same}
    assert freshness_decision(True, "20260904", old, current) == "VERIFIED_NO_NEW_DATA"
    assert freshness_decision(True, "20260904", old, {**current, "source_fingerprint": "changed"}) == "SAME_CUTOFF_SOURCE_REVISION"
    assert freshness_decision(True, "20260904", old, {**current, "computation_identity": {"sha256": "changed"}}) == "SAME_CUTOFF_COMPUTATION_REVISION"
    assert freshness_decision(True, "20260904", old, {**current, "render_identity": {"sha256": "changed"}}) == "SAME_CUTOFF_RENDER_REVISION"

    identity = computation_identity(Path.cwd())
    required = {
        "src/phase1_runner.py", "src/phase2_runner.py", "src/phase3_runner.py",
        "src/phase4_runner.py", "src/phase5_runner.py", "src/factors/engine.py",
        "src/sector/phase2.py", "src/scanner/sector_scanner.py",
        "src/scanner/stock_scanner.py", "src/candidates/research_priority.py",
        "config/factors.yaml", "config/sector_scanner.yaml", "config/stock_scanner.yaml",
        "config/research_priority.yaml",
    }
    assert required <= set(identity["files"])
    assert identity["environment"]["dependencies"]
    assert len(identity["sha256"]) == 64


def test_single_cutoff_authority_is_passed_to_phase1():
    phase_source = inspect.getsource(__import__("phase1_runner"))
    production_source = inspect.getsource(daily.run_phases)
    assert "resolved_cutoff_date=None" in phase_source
    assert "cutoff=int(str(resolved_cutoff_date)" in phase_source
    assert "resolved_cutoff_date=resolved_cutoff_date" in production_source
    assert "TDX_RUN_CALENDAR" in phase_source


def test_single_writer_records_owner_and_recovers_crash_lock(tmp_path):
    path = tmp_path / "daily.lock"
    first = RunLock(path, run_id="run-a")
    owner = first.acquire()
    assert owner["pid"] == os.getpid() and owner["run_id"] == "run-a"
    second = RunLock(path, run_id="run-b")
    with pytest.raises(ActiveRunLock):
        second.acquire()
    assert second.last_decision["decision"] == "REJECT_ACTIVE"
    assert json.loads(path.read_text("utf8"))["run_id"] == "run-a"
    first.release()
    path.write_text(json.dumps({"pid": 999999999, "run_id": "crashed"}), encoding="utf8")
    old = 1
    os.utime(path, (old, old))
    recovered = RunLock(path, run_id="run-c", stale_after_seconds=1)
    recovered.acquire()
    assert recovered.last_decision["decision"] == "RECOVER_STALE"
    assert recovered.last_decision["owner"]["run_id"] == "crashed"
    recovered.release()


def _minimal_daily_mocks(monkeypatch, root: Path, failure: Exception):
    resolution = {
        "resolved_cutoff_date": "20260904", "cutoff_status": "NORMAL_NEW_TRADING_DAY",
        "calendar_generation": "cal", "calendar_sha256": "hash", "run_calendar_rows": [],
    }
    monkeypatch.setattr(daily, "readiness", lambda *_: (resolution, []))
    monkeypatch.setattr(daily, "source_fingerprint", lambda *_: {"source_fingerprint": "s", "source_fingerprint_components": {}, "source_fingerprint_version": "v", "source_fingerprint_seconds": 0, "day_fingerprint_seconds": 0})
    monkeypatch.setattr(daily, "source_identity", lambda *_: {"sha256": "s"})
    monkeypatch.setattr(daily, "computation_identity", lambda *_: {"sha256": "c"})
    monkeypatch.setattr(daily, "render_identity", lambda *_: {"sha256": "r"})
    monkeypatch.setattr(daily, "tdx_hashes", lambda *_: {})
    monkeypatch.setattr(daily, "run_phases", lambda *_: (_ for _ in ()).throw(failure))


@pytest.mark.parametrize(
    "failure,expected",
    ((RuntimeError("PHASE1_HASH_MISMATCH"), EXIT_BINDING), (RuntimeError("PHASE_FAILURE"), 1)),
)
def test_failure_handler_preserves_phase_and_hash_errors(tmp_path, monkeypatch, failure, expected):
    _minimal_daily_mocks(monkeypatch, tmp_path, failure)
    code, result = daily._run_daily_unlocked(tmp_path, tmp_path / "tdx", run_id="failure-case")
    assert code == expected == result["exit_code"]
    assert str(failure) in result["message"] and str(failure) in result["traceback"]


def test_missing_input_and_report_failure_exit_codes(tmp_path, monkeypatch):
    code, missing = daily._run_daily_unlocked(tmp_path / "missing", tmp_path / "tdx", run_id="missing")
    assert code == EXIT_NOT_READY and missing["exception_type"] == "FileNotFoundError"
    _minimal_daily_mocks(monkeypatch, tmp_path, RuntimeError("unused"))
    monkeypatch.setattr(daily, "run_phases", lambda *_: [])
    monkeypatch.setattr(daily, "build_reports", lambda *_: (_ for _ in ()).throw(PublicationValidationError("REPORT_FAILURE")))
    code, report = daily._run_daily_unlocked(tmp_path, tmp_path / "tdx", run_id="report")
    assert code == EXIT_PUBLICATION and "REPORT_FAILURE" in report["traceback"]


def test_pointer_failure_preserves_old_pointer_and_original_error(tmp_path, monkeypatch):
    _minimal_daily_mocks(monkeypatch, tmp_path, RuntimeError("unused"))
    monkeypatch.setattr(daily, "run_phases", lambda *_: [])
    pointer = tmp_path / "reports/current/20260904.json"
    atomic_write_json(pointer, {"run_id": "old", "release_path": str(tmp_path / "old")})
    before = pointer.read_bytes()

    def fake_build(_root, stage, *_args):
        stage.mkdir(parents=True)
        for name, payload in (
            ("market_summary.html", "<html>local</html>"),
            ("sectors.csv", "sector_id\n"),
            ("stocks.csv", "security_id\n"),
            ("candidates.csv", "security_id\n"),
            ("run_audit.json", "{}\n"),
            ("PERFORMANCE_AUDIT.json", "{}\n"),
            ("RUN_UNIVERSE_SNAPSHOT.json", '{"generation":"g","sha256":"u","count":0}\n'),
        ):
            (stage / name).write_text(payload, encoding="utf8")
        return ({index: {"generation": f"g{index}"} for index in range(1, 6)}, {}, {"sectors": 0, "stocks": 0, "candidates": 0})

    monkeypatch.setattr(daily, "build_reports", fake_build)
    monkeypatch.setattr(daily, "verify_directory", lambda *_: {"pass": True})
    monkeypatch.setattr(daily, "publish_generation", lambda *_args, **_kwargs: (_ for _ in ()).throw(PublicationValidationError("POINTER_FAILURE")))
    code, result = daily._run_daily_unlocked(tmp_path, tmp_path / "tdx", run_id="pointer")
    assert code == EXIT_PUBLICATION == result["exit_code"]
    assert pointer.read_bytes() == before
    assert "POINTER_FAILURE" in result["message"] and "POINTER_FAILURE" in result["traceback"]


def test_failure_log_write_failure_cannot_mask_original(tmp_path, monkeypatch):
    try:
        raise ValueError("ORIGINAL_ERROR")
    except ValueError as exc:
        original = FailureRecord(stage="TEST", exc=exc, run_id="x").as_dict()
    monkeypatch.setattr(daily, "atomic_write_json", lambda *_: (_ for _ in ()).throw(OSError("LOG_WRITE_FAILED")))
    errors = daily._safe_failure_write(tmp_path, "x", original, tmp_path)
    assert original["message"] == "ORIGINAL_ERROR"
    assert "ORIGINAL_ERROR" in original["traceback"]
    assert errors and all("LOG_WRITE_FAILED" in item for item in errors)
    assert "UnboundLocalError" not in original["traceback"]


def test_empty_candidate_pool_writes_fixed_schema_and_html(tmp_path, monkeypatch):
    cutoff = "20260904"
    cutoff_date = date(2026, 9, 4)
    (tmp_path / "data/market").mkdir(parents=True)
    (tmp_path / "data/scanner").mkdir(parents=True)
    (tmp_path / "data/candidates").mkdir(parents=True)
    market_fields = [
        "normal_universe_count", "breadth_ret5_pos", "breadth_ret20_pos", "breadth_ret60_pos",
        "breadth_above_ma20", "breadth_above_ma60", "market_ret5_median", "market_ret20_median",
        "market_ret60_median", "mdd20_median", "amount_ratio_5_20_median",
    ]
    pd.DataFrame([{"date": cutoff_date, **{name: 0 for name in market_fields}}]).to_parquet(tmp_path / "data/market/market_regime_daily.parquet")
    sector = {"date": cutoff_date, "sector_id": "I:1", "sector_name": "sector", "sector_type": "INDUSTRY", "primary_pattern": "NONE", "scanner_hits": ""}
    for name in ("sector_rs5_pct", "sector_rs20_pct", "sector_rs60_pct", "sector_breadth_ret5_pos", "sector_ret5_median", "sector_ret20_median", "sector_mdd20_median", "sector_amount_ratio_median"):
        sector[name] = 0.0
    for name in ("breadth_expansion", "high_concentration", "low_coverage"):
        sector[name] = False
    pd.DataFrame([sector]).to_parquet(tmp_path / "data/scanner/sector_scanner_daily.parquet")
    stock = {"date": cutoff_date, "security_id": "SH.000001", **{name: False for name in ("steady_trend", "strong_pullback", "breakout_prep", "sector_leader", "early_mover")}}
    pd.DataFrame([stock]).to_parquet(tmp_path / "data/scanner/stock_scanner_daily.parquet")
    candidate_columns = {
        "date": pd.Series([], dtype="object"), "security_id": pd.Series([], dtype="str"),
        "primary_leader_sector": pd.Series([], dtype="str"), "primary_leader_pattern": pd.Series([], dtype="str"),
        "effective_pattern": pd.Series([], dtype="str"), "research_priority_pct": pd.Series([], dtype="float64"),
        "priority_score": pd.Series([], dtype="float64"), "research_priority": pd.Series([], dtype="str"),
        "best_sector_name": pd.Series([], dtype="str"), "security_name": pd.Series([], dtype="str"),
        "primary_pattern": pd.Series([], dtype="str"), "warning_codes": pd.Series([], dtype="str"),
        "priority_reason_codes": pd.Series([], dtype="str"),
    }
    pd.DataFrame(candidate_columns).to_parquet(tmp_path / "data/candidates/candidate_pool_daily.parquet")
    receipts = {index: {"generation": f"g{index}"} for index in range(1, 6)}
    bound_hashes = {
        "data/factors/factors_daily.parquet": "factor",
        "data/normalized/adjusted_daily.parquet": "normalized",
        "data/market/market_regime_daily.parquet": "market",
        "data/sectors/sector_factors_daily.parquet": "sector",
        "data/scanner/sector_scanner_daily.parquet": "sector-scanner",
        "data/scanner/stock_scanner_daily.parquet": "stock-scanner",
        "data/candidates/candidate_pool_daily.parquet": "candidates",
    }
    monkeypatch.setattr(daily, "receipt_chain", lambda *_: (receipts, bound_hashes))
    stage = tmp_path / "release"
    _, _, counts = build_reports(
        tmp_path, stage, cutoff, "empty", "start", [], {"calendar_generation": "cal"},
        {"source_fingerprint": "s"}, "FRESH_CUTOFF", [],
    )
    candidates = pd.read_csv(stage / "candidates.csv", encoding="utf-8-sig")
    html = (stage / "market_summary.html").read_text("utf8")
    assert counts["candidates"] == 0 and len(candidates) == 0
    assert {"security_id", "research_priority", "priority_score"} <= set(candidates.columns)
    assert all(f">{grade}<" in html and ">0<" in html for grade in ("甲加级", "甲级", "乙级", "丙级"))
    assert "本日无符合当前规则的候选" in html
