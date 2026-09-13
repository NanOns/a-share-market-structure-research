import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from workbench_db import WorkbenchRepository
import workbench_service.app as app


ROOT = Path(__file__).resolve().parents[2]


def test_v3_page_has_two_tracks_member_preview_and_race_protection():
    html = (ROOT / "src/workbench_service/static/research-v3.html").read_text(encoding="utf-8")
    for marker in ("current-cards", "potential-cards", "page_size=6", "/api/v3/research/sectors/", "AbortController", "memberRole:'TODAY_LEADER'", "EARLY_WATCH"):
        assert marker in html
    assert "grid-template-columns:1fr" in html
    assert "slice(0,6)" in html
    assert "slice(0,3)" in html


def test_v3_route_serves_page_without_touching_research_storage(tmp_path):
    db = tmp_path / "api.duckdb"
    with WorkbenchRepository(ROOT, db):
        pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler(ROOT, db))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        response = urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/v3")
        html = response.read().decode("utf-8")
        assert response.status == 200
        assert "V3 本地研究预览" in html
        with app.duckdb.connect(str(db)) as connection:
            assert connection.execute("select count(*) from information_schema.tables where table_name='research_runs'").fetchone()[0] == 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
