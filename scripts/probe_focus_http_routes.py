"""HTTP smoke probe for the Focus page route and PostgreSQL fail-closed edge."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen

from workbench_db import WorkbenchRepository
from workbench_service import app

ROOT = Path(__file__).resolve().parents[1]


def _fetch(url: str) -> tuple[int, str, dict | None]:
    try:
        with urlopen(url, timeout=5) as response:
            body = response.read().decode("utf-8")
            try:
                payload = json.loads(body) if "application/json" in response.headers.get("Content-Type", "") else None
            except json.JSONDecodeError:
                payload = None
            return response.status, body, payload
    except HTTPError as error:
        body = error.read().decode("utf-8")
        return error.code, body, json.loads(body)


def _request(handler, url_path: str) -> tuple[int, str, dict | None]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        return _fetch(f"http://127.0.0.1:{server.server_port}{url_path}")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def run_probe() -> dict[str, object]:
    old_backend = os.environ.get("WORKBENCH_API_BACKEND")
    old_dsn = os.environ.get("WORKBENCH_PG_DSN")
    os.environ["WORKBENCH_API_BACKEND"] = "duckdb"
    try:
        with tempfile.TemporaryDirectory(prefix="focus-http-probe-") as temp_dir:
            database = Path(temp_dir) / "probe.duckdb"
            with WorkbenchRepository(ROOT, database):
                pass

            if old_dsn:
                os.environ.pop("WORKBENCH_PG_DSN", None)
            page_status, page, _ = _request(
                app.make_handler(ROOT, database), "/v3/focus-tracker")
            page_markers = ("/api/v3/focus-tracker", "持续观察总览",
                            "原支持板块 / 当前支持板块", "观察场景", "变化记录",
                            "观察详情", "历史结果复盘", 'id="sector-dialog"',
                            "page_size:state.sectorPageSize")
            missing_markers = [marker for marker in page_markers if marker not in page]
            if ('placeholder="sector_id"' in page or "JSON.stringify(value,null,2)" in page
                    or 'id="run-date"' in page or "每日记录" in page
                    or "展开关联个股" in page):
                missing_markers.append("旧版不友好筛选或原始 JSON 输出仍存在")
            if page_status != 200 or missing_markers:
                raise AssertionError((page_status, "FOCUS_PAGE_ROUTE_MISSING", missing_markers))

            root_status, root_page, _ = _request(app.make_handler(ROOT, database), "/")
            if (root_status != 200 or 'id="focus-tracker-nav"' not in root_page
                    or 'id="focus-tracker-inline"' not in root_page
                    or '<a class="nav-item" href="/v3/focus-tracker"' in root_page):
                raise AssertionError((root_status, "FOCUS_INLINE_WORKBENCH_ENTRY_MISSING"))

            api_status, _body, api_payload = _request(
                app.make_handler(ROOT, database), "/api/v3/focus-tracker/summary")
            if api_status != 200 or api_payload is None or api_payload.get("status") not in (
                    "AVAILABLE", "NO_ACCEPTED_RUN", "REPLAY_REQUIRED"):
                raise AssertionError((api_status, api_payload))

            os.environ["WORKBENCH_PG_DSN"] = (
                "postgresql://focus-probe:invalid@127.0.0.1:1/probe?connect_timeout=1")
            down_status, _body, down_payload = _request(
                app.make_handler(ROOT, database), "/api/v3/focus-tracker/summary")
            if down_status != 503 or not down_payload or down_payload.get("status") != "PG_UNAVAILABLE":
                raise AssertionError((down_status, down_payload))
            if down_payload.get("retryable") is not True:
                raise AssertionError(down_payload)
            return {"contract": "FOCUS_HTTP_ROUTE_SMOKE_V1", "page_status": page_status,
                    "inline_workbench_entry": True,
                    "list_context_markers": len(page_markers),
                    "empty_head_status": api_payload["status"], "pg_down_status": down_status,
                    "pg_down_code": down_payload["status"], "fallback_used": False,
                    "temporary_duckdb_removed": True}
    finally:
        if old_backend is None:
            os.environ.pop("WORKBENCH_API_BACKEND", None)
        else:
            os.environ["WORKBENCH_API_BACKEND"] = old_backend
        if old_dsn is None:
            os.environ.pop("WORKBENCH_PG_DSN", None)
        else:
            os.environ["WORKBENCH_PG_DSN"] = old_dsn


if __name__ == "__main__":
    print(run_probe())
