"""Compare the Today Research read model backed by DuckDB and PostgreSQL."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_db.postgres_repository import PostgresRepository  # noqa: E402
from workbench_service.today_research_bundle import TodayResearchBundleReader  # noqa: E402


REPORT = ROOT / "runtime/postgres_migration/20260922/today_research_pg_shadow_report.json"


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def atomic_write(payload: dict) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    tmp = REPORT.with_suffix(REPORT.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, REPORT)


def main() -> int:
    duck = TodayResearchBundleReader(ROOT, database_path=ROOT / "data/database/market_research.duckdb")
    duck_list = duck.list(page=1, page_size=25)
    first_id = str(duck_list.get("items", [{}])[0].get("security_id", "")) if duck_list.get("items") else ""
    duck_detail = duck.detail(first_id, expected_digest=str(duck_list.get("context", {}).get("output_digest", ""))) if first_id else None
    with PostgresRepository() as repository:
        pg = TodayResearchBundleReader(ROOT, repository=repository)
        pg_list = pg.list(page=1, page_size=25)
        pg_detail = pg.detail(first_id, expected_digest=str(pg_list.get("context", {}).get("output_digest", ""))) if first_id else None
    list_match = canonical(duck_list) == canonical(pg_list)
    detail_match = canonical(duck_detail) == canonical(pg_detail)
    report = {
        "contract_version": "TODAY_RESEARCH_PG_SHADOW_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "request": {"list": {"page": 1, "page_size": 25}, "detail_security_id": first_id},
        "list_match": list_match,
        "detail_match": detail_match,
        "duckdb_context": duck_list.get("context"),
        "postgres_context": pg_list.get("context"),
        "duckdb_total": duck_list.get("total"),
        "postgres_total": pg_list.get("total"),
        "status": "PASS" if list_match and detail_match else "FAIL",
        "online_switch_performed": False,
        "data_generation_triggered": False,
    }
    atomic_write(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
