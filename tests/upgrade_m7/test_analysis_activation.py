import time
from pathlib import Path

import duckdb
import pytest

from workbench_service.analysis_activation import AnalysisActivationError, AnalysisActivationService
from workbench_service.app import Api
from workbench_service.history_jobs import HistoryJobService
from test_history_jobs import _request, _setup


def _successful_job(tmp_path):
    database = _setup(tmp_path)
    with duckdb.connect(str(database)) as con:
        con.execute("insert into publication_heads values ('2026-09-07','pub-1')")
    service = HistoryJobService(tmp_path, database)
    submitted = service.submit(_request(["slice-0"]))
    deadline = time.monotonic() + 5
    while service.status(submitted["job_id"])["status"] in {"QUEUED", "RUNNING"} and time.monotonic() < deadline:
        time.sleep(0.02)
    assert service.status(submitted["job_id"])["status"] == "SUCCESS"
    return database, submitted["job_id"]


def test_activation_creates_new_revision_and_is_idempotent(tmp_path):
    database, job_id = _successful_job(tmp_path)
    service = AnalysisActivationService(tmp_path, database)
    first = service.activate(job_id, expected_head_id="pub-1", idempotency_key="activate-1")
    second = service.activate(job_id, expected_head_id="pub-1", idempotency_key="activate-1")
    assert first["status"] == "SUCCESS" and first["reused"] is False
    assert second["publication_id"] == first["publication_id"] and second["reused"] is True
    with duckdb.connect(str(database), read_only=True) as con:
        assert con.execute("select publication_id from publication_heads where trade_date='2026-09-07'").fetchone()[0] == first["publication_id"]
        assert con.execute("select status from analysis_snapshots where snapshot_id=?", [first["analysis_snapshot_id"]]).fetchone()[0] == "SUCCESS"
        assert con.execute("select count(*) from publication_analysis_snapshots where publication_id=? and domain='LOCAL_RECONSTRUCTED'", [first["publication_id"]]).fetchone()[0] == 1
        assert con.execute("select count(*) from publication_analysis_snapshots where publication_id='pub-1'").fetchone()[0] == 0
    config = tmp_path / "config"
    config.mkdir(exist_ok=True)
    config.joinpath("history_windows.yaml").write_text(Path("config/history_windows.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    api = Api(database, root=tmp_path)
    identity = api.identity(first["publication_id"], include_analysis=True)
    assert identity["analysis_snapshot_id"] == first["analysis_snapshot_id"]
    assert identity["capabilities"]["history_analysis"] == "AVAILABLE"


def test_activation_checks_head_and_identity_conflicts(tmp_path):
    database, job_id = _successful_job(tmp_path)
    service = AnalysisActivationService(tmp_path, database)
    with pytest.raises(AnalysisActivationError, match="EXPECTED_HEAD_MISMATCH"):
        service.activate(job_id, expected_head_id="wrong-head", idempotency_key="activate-1")
    service.activate(job_id, expected_head_id="pub-1", idempotency_key="activate-1")
    with pytest.raises(AnalysisActivationError, match="ACTIVATION_IDENTITY_CONFLICT"):
        service.activate(job_id, expected_head_id="pub-1", idempotency_key="activate-2")


def test_prepare_rejects_conflicting_existing_snapshot_entry(tmp_path):
    database, job_id = _successful_job(tmp_path)
    service = AnalysisActivationService(tmp_path, database)
    prepared = service.prepare(job_id)
    with duckdb.connect(str(database)) as con:
        entry = con.execute("select domain,trade_date from analysis_snapshot_entries where snapshot_id=?", [prepared["snapshot_id"]]).fetchone()
        con.execute("delete from analysis_snapshot_entries where snapshot_id=?", [prepared["snapshot_id"]])
        original = list(con.execute("select * from analysis_slices where slice_id='slice-0'").fetchone())
        original[0] = "slice-conflict"
        con.execute("insert into analysis_slices values (?,?,?,?,?,?,?,?,?,?,?,?)", original)
        con.execute("insert into analysis_snapshot_entries values (?,?,?,?)", [prepared["snapshot_id"], entry[0], entry[1], "slice-conflict"])
    with pytest.raises(AnalysisActivationError, match="SNAPSHOT_ENTRY_IDENTITY_CONFLICT"):
        service.prepare(job_id)
