import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from workbench_db import WorkbenchRepository
import workbench_service.app as app


ROOT = Path(__file__).resolve().parents[2]


def test_v3_is_the_single_unified_workbench_entry(tmp_path):
    db = tmp_path / "entry.duckdb"
    with WorkbenchRepository(ROOT, db):
        pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler(ROOT, db))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        response = urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/v3")
        page = response.read().decode("utf-8")
        assert response.status == 200
        assert 'data-workbench-mode="v3"' in page
        assert 'data-workbench-base="/v3"' in page
        assert "统一研究工作台 · V3" in page
        assert "V3 单一入口" in page
        for label in ("研究首页", "板块研究", "个股研究", "联动筛选", "市场与事件", "数据 / 运维"):
            assert label in page
        assert "旧功能 / 历史工作台" not in page
        assert "/v2?page=" not in page
        assert "/v2/v3-unified.js" in page
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
