"""Compare publication sector metadata and stock-name projections."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_db.postgres_repository import PostgresRepository  # noqa: E402

REPORT = ROOT / "runtime/postgres_migration/20260922/research_metadata_pg_shadow_report.json"


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def main() -> int:
    publication_id = "m4-9540768dfa3c23169cac2e2b2da25711"
    with duckdb.connect(str(ROOT / "data/database/market_research.duckdb"), read_only=True) as con:
        sector_rows = [{"sector_id": str(a), "sector_name": str(b or a), "sector_type": str(c or "LOCAL")} for a, b, c in con.execute("select sector_id,sector_name,sector_type from sector_daily where publication_id=? order by sector_id", [publication_id]).fetchall()]
        stock_rows = {str(a): str(b or a) for a, b in con.execute("select security_id,security_name from stock_daily where publication_id=? order by security_id", [publication_id]).fetchall()}
    with PostgresRepository() as repo:
        pg_sector_rows = repo.sector_metadata(publication_id)
        pg_stock_rows = repo.research_security_names(publication_id)
    checks = {
        "sector_metadata_match": canonical(sector_rows) == canonical(pg_sector_rows),
        "stock_names_match": canonical(stock_rows) == canonical(pg_stock_rows),
        "sector_count": {"duckdb": len(sector_rows), "postgres": len(pg_sector_rows)},
        "stock_count": {"duckdb": len(stock_rows), "postgres": len(pg_stock_rows)},
    }
    report = {"contract_version": "RESEARCH_METADATA_PG_SHADOW_V1", "generated_at_utc": datetime.now(timezone.utc).isoformat(), "publication_id": publication_id, "checks": checks, "status": "PASS" if checks["sector_metadata_match"] and checks["stock_names_match"] else "FAIL", "online_switch_performed": False, "data_generation_triggered": False}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    tmp = REPORT.with_suffix(REPORT.suffix + ".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
