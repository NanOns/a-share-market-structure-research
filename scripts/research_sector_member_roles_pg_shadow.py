"""Compare research-sector member role rows between DuckDB and PostgreSQL."""
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

REPORT = ROOT / "runtime/postgres_migration/20260922/research_sector_member_roles_pg_shadow_report.json"


def normalize(value):
    if isinstance(value, str) and value[:1] in "[{":
        try:
            return normalize(json.loads(value))
        except (TypeError, ValueError, json.JSONDecodeError):
            return value
    if isinstance(value, dict):
        return {str(k): normalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize(v) for v in value]
    return value


def canonical(value):
    return json.dumps(normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def main() -> int:
    with duckdb.connect(str(ROOT / "data/database/market_research.duckdb"), read_only=True) as con:
        run_id = con.execute("select run_id from research_runs where status='COMPLETE' order by trade_date desc,completed_at desc,run_id desc limit 1").fetchone()[0]
        duck_rows = con.execute("select run_id,sector_id,security_id,role,role_rank,today_rank,role_reason_codes,evidence from research_sector_member_roles where run_id=? order by sector_id,role_rank,security_id,role", [run_id]).fetchall()
    with PostgresRepository() as repo:
        pg_rows = repo.research_sector_member_role_rows(str(run_id))
    match = canonical(duck_rows) == canonical(pg_rows)
    report = {"contract_version": "RESEARCH_SECTOR_MEMBER_ROLES_PG_SHADOW_V1", "generated_at_utc": datetime.now(timezone.utc).isoformat(), "run_id": str(run_id), "duckdb_count": len(duck_rows), "postgres_count": len(pg_rows), "rows_match": match, "status": "PASS" if match else "FAIL", "online_switch_performed": False, "data_generation_triggered": False}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    tmp = REPORT.with_suffix(REPORT.suffix + ".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if match else 2


if __name__ == "__main__":
    raise SystemExit(main())
