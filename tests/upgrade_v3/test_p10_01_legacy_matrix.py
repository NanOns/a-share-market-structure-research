import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import duckdb

from workbench_db import WorkbenchRepository
import workbench_service.app as app
from workbench_service.legacy_feature_matrix import CONTRACT_ID, build_legacy_matrix


ROOT = Path(__file__).resolve().parents[2]


def test_p10_01_matrix_covers_every_v3_section_2_row_without_silent_hide():
    result = build_legacy_matrix("pub-p10", "2026-09-10")
    assert result["api_contract"] == CONTRACT_ID
    assert result["total"] == 19
    items = result["items"]
    assert len({item["feature_id"] for item in items}) == 19
    for item in items:
        assert item["decision"] in {"RETAIN", "REPLACE", "EXCLUDE", "DEFER"}
        assert item["status"]
        assert item["evidence"]["path"] or item["decision"] in {"EXCLUDE", "DEFER"}
        assert "暂时" not in item["note"]
    assert result["acceptance"]["historical_routes_are_context_bound"] is True


def test_p10_01_matrix_preserves_legacy_routes_and_v3_semantic_relabels():
    items = {item["feature_id"]: item for item in build_legacy_matrix("pub-p10", "2026-09-10")["items"]}
    assert items["LEGACY-02"]["decision"] == "REPLACE"
    assert "/api/candidates" in items["LEGACY-03"]["legacy_compatibility"]["apis"]
    assert items["LEGACY-06"]["new_entry"]["label"] == "中期主线背景"
    assert items["LEGACY-07"]["new_entry"]["label"] == "原结构强成员 / 历史代表"
    assert items["LEGACY-10"]["new_entry"]["label"] == "全部结构候选 / 结构证据"
    assert items["LEGACY-13"]["status"] == "V2_HISTORY_ONLY_REMOVED_FROM_V3"
    assert items["LEGACY-18"]["status"] == "EXPLICITLY_EXCLUDED"
    assert items["LEGACY-19"]["status"] == "EXPLICITLY_DEFERRED"
    assert "publication_id=pub-p10" in items["LEGACY-05"]["evidence"]["path"]
    assert "trade_date=2026-09-10" in items["LEGACY-05"]["evidence"]["path"]


def test_p10_01_api_query_is_read_only_and_returns_all_rows(tmp_path):
    db = tmp_path / "api.duckdb"
    with WorkbenchRepository(ROOT, db):
        pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler(ROOT, db))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        response = urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/api/v3/legacy-matrix")
        payload = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert payload["api_contract"] == CONTRACT_ID
        assert payload["total"] == 19
        assert payload["storage"]["database_written"] is False
        history_response = urllib.request.urlopen(
            f"http://127.0.0.1:{server.server_port}/v2?page=sectors&subpage=mainlines&publication_id=historic-p10&trade_date=2026-09-10"
        )
        assert history_response.status == 200
        assert "中期主线背景" in history_response.read().decode("utf-8")
        with duckdb.connect(str(db), read_only=True) as connection:
            assert connection.execute("select count(*) from information_schema.tables where table_name='research_runs'").fetchone()[0] == 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_p10_01_page_exposes_matrix_and_context_preserving_legacy_entry():
    page = (ROOT / "src/workbench_service/static/research-v3.html").read_text(encoding="utf-8")
    for marker in ("legacy-matrix", "/api/v3/legacy-matrix", "中期主线背景", "历史代表", "全部结构候选", "V2_HISTORY_ONLY_REMOVED_FROM_V3"):
        assert marker in page
