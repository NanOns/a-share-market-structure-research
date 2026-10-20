from __future__ import annotations

import json
import os
import subprocess
import struct
from pathlib import Path

import pytest

from workbench_analysis.tdx_local_snapshot import (
    LocalSnapshotError,
    build_local_snapshot,
    build_local_native_dev_candidate,
    verify_local_snapshot,
)


def fixture_root(root: Path) -> Path:
    tdx = root / "tdx"
    for relative, value in (("vipdoc/sh/lday/sh600000.day", b"sh-bars"),
                            ("vipdoc/sz/lday/sz000001.day", b"sz-bars")):
        path = tdx / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    return tdx


def test_local_tdx_snapshot_is_content_addressed_outside_input_and_repeatable(tmp_path: Path, monkeypatch):
    import workbench_analysis.tdx_local_snapshot as snapshots

    def reject_implicit_pg(*args, **kwargs):
        raise AssertionError("snapshot operation must not access PostgreSQL by default")

    monkeypatch.setattr(snapshots, "_persist_manifest_pg", reject_implicit_pg)
    monkeypatch.setattr(snapshots, "_read_manifest_pg", reject_implicit_pg)
    source = fixture_root(tmp_path)
    output = tmp_path / "project/data/v4/local_tdx_snapshots"
    result = build_local_snapshot(source, output)
    assert result["status"] == "SNAPSHOT_CREATED"
    assert Path(result["manifest_path"]).is_relative_to(output / result["snapshot_id"])
    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["source_root_read_only"] is True
    assert manifest["copied_outside_source_root"] is True
    assert manifest["file_count"] == 2
    assert result["pg_binding"] is None
    verified = verify_local_snapshot(output, result["snapshot_id"])
    assert verified["status"] == "PASS"
    assert verified["pg_binding"] is None
    second = build_local_snapshot(source, output)
    assert second["status"] == "REUSED_IDENTICAL_SNAPSHOT"
    assert second["snapshot_id"] == result["snapshot_id"]


def test_snapshot_fails_if_existing_content_addressed_copy_was_mutated(tmp_path: Path):
    source = fixture_root(tmp_path)
    output = tmp_path / "project/data/v4/local_tdx_snapshots"
    result = build_local_snapshot(source, output)
    stored = output / result["snapshot_id"] / "sh/lday/sh600000.day"
    stored.write_bytes(b"tampered")
    with pytest.raises(LocalSnapshotError, match="IMMUTABLE_SNAPSHOT_CONTENT_CHANGED"):
        build_local_snapshot(source, output)


def test_symlink_input_is_rejected(tmp_path: Path):
    source = fixture_root(tmp_path)
    link = source / "vipdoc/sh/lday/sh600001.day"
    target = tmp_path / "outside.day"
    target.write_bytes(b"outside")
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        if os.name!='nt':raise
        directory=tmp_path/'outside_directory';directory.mkdir()
        subprocess.run(['cmd','/c','mklink','/J',str(link),str(directory)],check=True,capture_output=True)
        assert link.is_junction()
    with pytest.raises(LocalSnapshotError, match="TDX_INPUT_SYMLINK_REJECTED"):
        build_local_snapshot(source, tmp_path / "project/data/v4/local_tdx_snapshots")


def test_local_native_dev_candidate_binds_pg_identity_and_suspension_evidence(tmp_path: Path):
    source = tmp_path / "tdx"
    day_file = source / "vipdoc/sh/lday/sh600000.day"
    day_file.parent.mkdir(parents=True)
    day_file.write_bytes(struct.pack("<IIIIIfII", 20260910, 922, 936, 919, 935, 555882176.0, 59774256, 0))
    identities = {
        "sh.600000": {"source_security_key": "sh.600000", "security_id": "SEC-1",
                      "board_scope": "SH_MAIN", "identity_status": "PG_CANDIDATE_ONLY",
                      "identity_quality": "TEST_CANDIDATE", "identity_source_revision_id": "rev-1",
                      "identity_system_available_at": "2026-10-20T00:00:00+00:00",
                      "security_type": "A_STOCK", "listing_from": "1999-11-10", "listing_to": None},
        "sz.000001": {"source_security_key": "sz.000001", "security_id": "SEC-2",
                      "board_scope": "SZ_MAIN", "identity_status": "PG_CANDIDATE_ONLY",
                      "identity_quality": "TEST_CANDIDATE", "identity_source_revision_id": "rev-2",
                      "identity_system_available_at": "2026-10-20T00:00:00+00:00",
                      "security_type": "A_STOCK", "listing_from": "1991-04-03", "listing_to": None},
    }
    bao = [
        {"date": "2026-09-10", "code": "sh.600000", "close": "9.35", "volume": "59774256",
         "amount": "555882176", "tradestatus": "1"},
        {"date": "2026-09-10", "code": "sz.000001", "close": "11.85", "volume": "",
         "amount": "", "tradestatus": "0"},
    ]
    record = build_local_native_dev_candidate(
        source_root=source, trade_date="2026-09-10", identity_candidates=identities,
        baostock_rows=bao, observed_at_utc="2026-10-20T01:00:00Z", contract_sha256="a" * 64,
    )
    manifest = record["manifest"]
    assert manifest["target_bar_count"] == 1
    assert manifest["universe_count"] == 2
    assert manifest["target_bars"][0]["security_id"] == "SEC-1"
    assert manifest["universe"][1]["t0_status"] == "SUSPENDED_NO_TDX_BAR"
    assert manifest["formal_source_acceptance"] is False
    assert manifest["PIT_ELIGIBLE"] is False


def test_local_native_dev_candidate_rejects_unexplained_active_universe_gap(tmp_path: Path):
    source = tmp_path / "tdx"
    (source / "vipdoc/sh/lday").mkdir(parents=True)
    identities = {"sh.600000": {"source_security_key": "sh.600000", "security_id": "SEC-1",
                 "board_scope": "SH_MAIN", "identity_status": "PG_CANDIDATE_ONLY",
                 "identity_quality": "TEST", "identity_source_revision_id": "rev",
                 "identity_system_available_at": "2026-10-20T00:00:00+00:00", "security_type": "A_STOCK",
                 "listing_from": "1999-11-10", "listing_to": None}}
    with pytest.raises(LocalSnapshotError, match="LOCAL_NATIVE_DEV_T0_BAR_GAP_WITHOUT_SUSPENSION_PROOF"):
        build_local_native_dev_candidate(
            source_root=source, trade_date="2026-09-10", identity_candidates=identities,
            baostock_rows=[], observed_at_utc="2026-10-20T01:00:00Z", contract_sha256="a" * 64,
        )
