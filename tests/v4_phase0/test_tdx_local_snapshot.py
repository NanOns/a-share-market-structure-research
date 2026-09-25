from __future__ import annotations

import json
from pathlib import Path

import pytest

from workbench_analysis.tdx_local_snapshot import LocalSnapshotError, build_local_snapshot


def fixture_root(root: Path) -> Path:
    tdx = root / "tdx"
    for relative, value in (("vipdoc/sh/lday/sh600000.day", b"sh-bars"),
                            ("vipdoc/sz/lday/sz000001.day", b"sz-bars")):
        path = tdx / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    return tdx


def test_local_tdx_snapshot_is_content_addressed_outside_input_and_repeatable(tmp_path: Path):
    source = fixture_root(tmp_path)
    output = tmp_path / "project/data/v4/local_tdx_snapshots"
    result = build_local_snapshot(source, output)
    assert result["status"] == "SNAPSHOT_CREATED"
    assert Path(result["manifest_path"]).is_relative_to(output / result["snapshot_id"])
    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["source_root_read_only"] is True
    assert manifest["copied_outside_source_root"] is True
    assert manifest["file_count"] == 2
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
        pytest.skip("symlink creation unavailable")
    with pytest.raises(LocalSnapshotError, match="TDX_INPUT_SYMLINK_REJECTED"):
        build_local_snapshot(source, tmp_path / "project/data/v4/local_tdx_snapshots")
