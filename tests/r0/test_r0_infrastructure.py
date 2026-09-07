import json
import os
import time
from pathlib import Path

import pandas as pd
import pytest

from common.identity import computation_identity, render_identity, source_identity
from common.run_lock import ActiveRunLock, RunLock
from common.snapshot_reader import assert_no_future_rows, read_snapshot
from production.daily import freshness_decision, validate_universe_binding
from production.release import PublicationValidationError, atomic_write_json, build_pointer, publish_generation


def test_multidate_snapshot_reader_and_future_guard(tmp_path):
    path = tmp_path / "daily.parquet"
    pd.DataFrame({"date": [20260903, 20260904], "id": ["old", "a"]}).to_parquet(path)
    assert read_snapshot(path, "20260904").id.tolist() == ["a"]
    pd.DataFrame({"date": [20260904, 20260905], "id": ["a", "b"]}).to_parquet(path)
    with pytest.raises(ValueError, match="FUTURE_SNAPSHOT"):
        assert_no_future_rows(path, "20260904")


def test_dynamic_universe_is_exact_set_not_count():
    frame = pd.DataFrame({"security_id": ["SH.000001", "SZ.000001"]})
    snap = __import__("production.daily", fromlist=["universe_snapshot"]).universe_snapshot(frame, "20260904", "g")
    assert snap["count"] == 2
    assert validate_universe_binding(snap, ["SZ.000001", "SH.000001"])
    with pytest.raises(RuntimeError, match="IDENTITY_MISMATCH"):
        validate_universe_binding(snap, ["SH.000001", "BJ.000001"])


def test_identity_revision_is_not_no_new_data():
    old = {"cutoff_date": "20260904", "source_fingerprint": "s",
           "computation_identity": {"sha256": "old"}, "render_identity": {"sha256": "same"}}
    current = {"source_fingerprint": "s", "computation_identity": {"sha256": "new"},
               "render_identity": {"sha256": "same"}}
    assert freshness_decision(True, "20260904", old, current) == "SAME_CUTOFF_COMPUTATION_REVISION"


def test_single_writer_and_stale_recovery(tmp_path):
    path = tmp_path / "daily.lock"
    first = RunLock(path, run_id="one")
    first.acquire()
    with pytest.raises(ActiveRunLock):
        RunLock(path, run_id="two").acquire()
    first.release()
    path.write_text(json.dumps({"pid": 999999999, "run_id": "stale"}), encoding="utf8")
    os.utime(path, (time.time() - 100, time.time() - 100))
    recovered = RunLock(path, run_id="three", stale_after_seconds=1)
    recovered.acquire()
    recovered.release()


def test_generation_validation_failure_does_not_touch_old_pointer(tmp_path):
    generation = tmp_path / "release"
    generation.mkdir()
    old_pointer = tmp_path / "current.json"
    atomic_write_json(old_pointer, {"run_id": "old"})
    with pytest.raises(PublicationValidationError):
        publish_generation(generation, old_pointer, {"run_id": "new"})
    assert json.loads(old_pointer.read_text("utf8"))["run_id"] == "old"
