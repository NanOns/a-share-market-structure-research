import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from workbench_db import WorkbenchRepository
import workbench_service.app as app


ROOT = Path(__file__).resolve().parents[2]


def test_build_lock_keeps_reads_closed_and_exposes_active_jobs(tmp_path):
    database = tmp_path / "api.duckdb"
    with WorkbenchRepository(ROOT, database):
        pass
    handler_type = app.make_handler(ROOT, database)
    cells = dict(zip(handler_type.do_GET.__code__.co_freevars, handler_type.do_GET.__closure__))
    lock = cells["database_subprocess_active"].cell_contents
    jobs = cells["research_jobs"].cell_contents
    jobs["research-job-test"] = {
        "job_id": "research-job-test",
        "job_type": "BUILD_RESEARCH_V3",
        "status": "RUNNING",
        "progress": {"status": "BUILDING_RESEARCH_V3"},
    }
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_type)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        lock.set()
        active = json.load(urllib.request.urlopen(base + "/api/jobs?active=1"))
        assert [item["job_id"] for item in active["items"]] == ["research-job-test"]
        status = json.load(urllib.request.urlopen(base + "/api/jobs?job_id=research-job-test"))
        assert status["status"] == "RUNNING"
        operations = json.load(urllib.request.urlopen(base + "/api/operations/status"))
        assert operations["database_access"] == "SUSPENDED_FOR_BUILD"
        assert operations["active_job_count"] == 1
        with __import__("pytest").raises(urllib.error.HTTPError) as busy:
            urllib.request.urlopen(base + "/api/publications")
        assert busy.value.code == 503
        assert json.load(busy.value)["code"] == "DATABASE_BUILD_IN_PROGRESS"
        lock.clear()
        status = json.load(urllib.request.urlopen(base + "/api/jobs?job_id=research-job-test"))
        assert status["status"] == "RUNNING"
    finally:
        lock.clear()
        jobs.pop("research-job-test", None)
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_v3_busy_ui_retries_catalog_and_does_not_report_data_failure():
    app_js = (ROOT / "src/workbench_service/static/v2/app.js").read_text(encoding="utf-8")
    v3_js = (ROOT / "src/workbench_service/static/v2/v3-unified.js").read_text(encoding="utf-8")
    assert "DATABASE_BUILD_IN_PROGRESS" in app_js
    assert "loadPublicationCatalog, 5000" in app_js
    assert "retryWhenDatabaseReady('home-context', loadHome)" in v3_js
    assert "retryWhenDatabaseReady('priority-research'" in v3_js
    assert "get('/api/jobs?active=1')" in v3_js
