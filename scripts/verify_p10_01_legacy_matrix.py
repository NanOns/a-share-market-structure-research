"""Verify and seal the P10-01 legacy-feature matrix without touching production data."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import threading
import urllib.request
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_db import WorkbenchRepository  # noqa: E402
import workbench_service.app as app  # noqa: E402
from workbench_service.legacy_feature_matrix import CONTRACT_ID, build_legacy_matrix  # noqa: E402


SPEC = ROOT / "docs" / "WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
REPORT = ROOT / "reports" / "upgrade_v3" / "P10-01-LEGACY-MATRIX.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _api_smoke() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="p10_01_") as temporary:
        db = Path(temporary) / "api.duckdb"
        with WorkbenchRepository(ROOT, db):
            pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler(ROOT, db))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/api/v3/legacy-matrix"
            with urllib.request.urlopen(url) as response:
                payload = json.loads(response.read().decode("utf-8"))
            with duckdb.connect(str(db), read_only=True) as connection:
                table_count = connection.execute(
                    "select count(*) from information_schema.tables where table_name='research_runs'"
                ).fetchone()[0]
            return {
                "http_status": response.status,
                "api_contract": payload.get("api_contract"),
                "total": payload.get("total"),
                "database_written": payload.get("storage", {}).get("database_written"),
                "research_runs_table_count": table_count,
            }
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


def _write_atomic(payload: dict[str, object]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(REPORT.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, REPORT)


def main() -> int:
    matrix = build_legacy_matrix("p10-01", "2026-09-10")
    page = (ROOT / "src/workbench_service/static/research-v3.html").read_text(encoding="utf-8")
    legacy_page = (ROOT / "src/workbench_service/static/v2/index.html").read_text(encoding="utf-8")
    checks = {
        "contract_id": matrix["api_contract"] == CONTRACT_ID,
        "complete_19_rows": matrix["total"] == 19 and len(matrix["items"]) == 19,
        "unique_feature_ids": len({item["feature_id"] for item in matrix["items"]}) == 19,
        "each_row_has_decision_and_evidence": all(
            item["decision"] and item["status"] and (item["evidence"]["path"] or item["decision"] in {"EXCLUDE", "DEFER"})
            for item in matrix["items"]
        ),
        "historical_links_context_bound": matrix["acceptance"]["historical_routes_are_context_bound"],
        "v3_matrix_page_bound": all(marker in page for marker in ("legacy-matrix", "/api/v3/legacy-matrix", "本地估算切换")),
        "legacy_semantic_labels": all(marker in legacy_page for marker in ("历史强势板块参考", "中期主线背景", "历史代表个股", "全部结构候选")),
        "api_smoke_read_only": False,
    }
    api_smoke = _api_smoke()
    checks["api_smoke_read_only"] = (
        api_smoke["http_status"] == 200
        and api_smoke["api_contract"] == CONTRACT_ID
        and api_smoke["total"] == 19
        and api_smoke["database_written"] is False
        and api_smoke["research_runs_table_count"] == 0
    )
    with duckdb.connect(str(ROOT / "data/database/market_research.duckdb"), read_only=True) as connection:
        historical_publications = connection.execute(
            "select publication_id, cast(trade_date as varchar) from publications where status='SUCCESS' order by trade_date desc limit 5"
        ).fetchall()
    status = "FULL_PASS" if all(checks.values()) else "BLOCKED"
    payload = {
        "receipt_id": "P10-01-LEGACY-MATRIX",
        "stage": "P10-01",
        "status": status,
        "engineering_status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stage_contract": {
            "contract_id": CONTRACT_ID,
            "spec_sha256": _sha256(SPEC),
            "spec_section": "§2、§18.13、§20.3–§20.8",
            "scope": "逐项登记旧功能的保留、替换、排除或后置处置，并提供 V3 入口、旧兼容 API、历史入口和验收查询。",
        },
        "checks": checks,
        "matrix": {"total": matrix["total"], "feature_ids": [item["feature_id"] for item in matrix["items"]]},
        "evidence": {
            "api_smoke": api_smoke,
            "historical_publications_read_only": [
                {"publication_id": publication_id, "trade_date": trade_date}
                for publication_id, trade_date in historical_publications
            ],
            "targeted_tests": "pytest -q tests/upgrade_v3/test_p10_01_legacy_matrix.py",
            "javascript_syntax": "node vm.Script research-v3.html inline script",
            "static_check": "python -m compileall -q src scripts; git diff --check",
        },
        "acceptance": (
            "P10-01 FULL_PASS：§2 19 行均有明确去留、入口/兼容/查询证据；矩阵 API 与页面查询只读。"
            if status == "FULL_PASS"
            else "P10-01 BLOCKED：至少一项矩阵或只读验收检查失败。"
        ),
        "known_limits": [
            "本阶段使用查询契约和静态入口证据，不把数据库样本数量或页面截图当作算法效果证据。",
            "P10-02 名称选择、集合筛选和跨页上下文联动尚未实现。",
            "P10-03 前瞻结果和基线观察尚未实现；本回执不声称预测效果。",
        ],
        "next_stage": "P10-02" if status == "FULL_PASS" else "P10-01-REPAIR",
        "tdx_inputs_modified": False,
        "production_database_written": False,
    }
    _write_atomic(payload)
    print(json.dumps({"status": status, "checks": checks, "next_stage": payload["next_stage"]}, ensure_ascii=False))
    return 0 if status == "FULL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

