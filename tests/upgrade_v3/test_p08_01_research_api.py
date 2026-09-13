import duckdb
import pytest
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from workbench_db import WorkbenchRepository
import workbench_service.app as app
from workbench_service.research_context import ResearchContextError, ResearchContextReader
from workbench_service.research_queries import ResearchQueryError, ResearchQueries
from workbench_service.research_runs import ResearchRunStore


def body(**updates):
    value = {
        "job_type": "BUILD_RESEARCH_V3",
        "publication_id": "pub-api",
        "trade_date": "2026-09-10",
        "algorithm_version": "RESEARCH_V3_PREVIEW_1",
        "parameter_hash": "hash",
        "snapshot_id": "snap",
        "membership_snapshot_id": "members",
        "dependency_bindings": {"technical": "slice-a"},
    }
    value.update(updates)
    return value


def ready_store():
    connection = duckdb.connect(":memory:")
    runs = ResearchRunStore(connection)
    started = runs.start(body())
    runs.complete(
        started["run_id"],
        sector_states=[
            {"sector_id": "A", "current_eligible": True, "current_rank": 1, "member_count": 2, "quality": "READY", "reason_codes": ["CURRENT_QUALIFIED"]},
            {"sector_id": "B", "potential_eligible": True, "potential_branch": "BREADTH_BUILD", "potential_rank": 1, "member_count": 1, "quality": "READY"},
        ],
        member_roles=[{"sector_id": "A", "security_id": "S1", "role": "TODAY_LEADER", "role_rank": 1, "today_rank": 1}],
        shortlists=[{"list_type": "CURRENT_FOCUS", "security_id": "S1", "rank": 1, "primary_sector_id": "A"}],
    )
    return connection, started["run_id"]


def test_context_is_not_built_without_complete_run_and_unknown_id_is_rejected():
    connection = duckdb.connect(":memory:")
    reader = ResearchContextReader()
    not_built = reader.resolve_request("missing", "2026-09-10", connection=connection)
    assert not_built["status"] == "NOT_BUILT"
    with pytest.raises(ResearchContextError, match="CONTEXT_NOT_FOUND"):
        reader.resolve_id("ctx-does-not-exist", connection=connection)
    connection.close()


def test_context_and_sector_queries_only_expose_complete_run_and_total_precedes_page():
    connection, _run_id = ready_store()
    queries = ResearchQueries()
    context = queries.contexts.resolve_request("pub-api", "2026-09-10", connection=connection)
    assert context["status"] == "READY"
    result = queries.list_sectors(context["context_id"], track="ALL", page=1, page_size=1, connection=connection)
    assert result["status"] == "READY"
    assert result["total"] == 2
    assert result["returned_count"] == 1
    assert result["has_more"] is True
    assert result["context"]["run_id"] == context["run_id"]
    member_result = queries.sector_members(context["context_id"], "A", role="TODAY_LEADER", connection=connection)
    assert member_result["total"] == 1
    assert member_result["items"][0]["security_id"] == "S1"
    shortlist = queries.shortlist(context["context_id"], connection=connection)
    assert shortlist["items"][0]["security_id"] == "S1"
    connection.close()


def test_context_date_and_filter_contracts_fail_closed():
    connection, _run_id = ready_store()
    queries = ResearchQueries()
    context = queries.contexts.resolve_request("pub-api", "2026-09-10", connection=connection)
    with pytest.raises(ResearchQueryError, match="PAGINATION_INVALID"):
        queries.list_sectors(context["context_id"], page=0, connection=connection)
    with pytest.raises(ResearchQueryError, match="TRACK_UNSUPPORTED"):
        queries.list_sectors(context["context_id"], track="UNKNOWN", connection=connection)
    with pytest.raises(ResearchContextError, match="CONTEXT_NOT_FOUND"):
        queries.list_sectors("ctx-other-date", connection=connection)
    connection.close()


def test_context_http_route_returns_not_built_without_starting_a_build(tmp_path):
    root = Path(__file__).resolve().parents[2]
    db = tmp_path / "api.duckdb"
    with WorkbenchRepository(root, db):
        pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler(root, db))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/v3/research/context?publication_id=missing&trade_date=2026-09-10&mode=CLOSE"
        payload = json.loads(urllib.request.urlopen(url).read())
        assert payload["status"] == "NOT_BUILT"
        assert payload["context"]["capabilities"]["research"] == "NOT_BUILT"
        with duckdb.connect(str(db)) as connection:
            assert connection.execute("select count(*) from information_schema.tables where table_name='research_runs'").fetchone()[0] == 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
