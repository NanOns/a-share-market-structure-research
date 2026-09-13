from __future__ import annotations

import json
import threading
import urllib.request

import workbench_service.app as app

from test_p09_03_ext01_ladder_slice import ROOT, _db


def _serve(db):
    server = __import__("http.server").server.ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler(ROOT, db))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_evidence_page_contract_has_modal_focus_escape_overlay_and_source_time(tmp_path):
    db = _db(tmp_path)
    server, thread = _serve(db)
    try:
        response = urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/v3/events")
        page = response.read().decode("utf-8")
        assert response.status == 200
        for marker in (
            "evidenceModal",
            "source_as_of",
            "source_time",
            "evidenceClose.focus()",
            "event.key==='Escape'",
            "event.target===modal",
            "state.lastEvidenceButton.focus()",
            "/api/v3/events/ladder/",
        ):
            assert marker in page
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_evidence_page_keeps_explicit_empty_state_and_pagination_contract(tmp_path):
    db = tmp_path / "empty-events.duckdb"
    from workbench_db import WorkbenchRepository

    with WorkbenchRepository(ROOT, db):
        pass
    server, thread = _serve(db)
    try:
        api_response = urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/api/v3/events/ladder?page=2&page_size=2")
        payload = json.loads(api_response.read().decode("utf-8"))
        assert payload["status"] == "UNAVAILABLE"
        assert payload["empty_state"]["code"] == "EVENT_BUNDLE_UNAVAILABLE"
        page_response = urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/v3/events")
        page = page_response.read().decode("utf-8")
        assert page_response.status == 200
        assert "当前无法读取在线事件批次，不以本地数据冒充在线事实。" in page
        assert "state.hasMore=!!result.has_more" in page
        assert "next.disabled=!state.hasMore" in page
        assert "第 '+state.page+' 页 · 返回 '" in page
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
