"""Compare raw research-sector state rows between DuckDB and PostgreSQL."""
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
REPORT = ROOT / "runtime/postgres_migration/20260922/research_sector_state_pg_shadow_report.json"


def normalize(value):
    if isinstance(value, str) and value[:1] in "[{":
        try:
            return normalize(json.loads(value))
        except (TypeError, ValueError, json.JSONDecodeError):
            return value
    if isinstance(value, dict):
        return {str(key): normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in value]
    return value


def canonical_rows(rows):
    return json.dumps(normalize(rows), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def main() -> int:
    with duckdb.connect(str(ROOT / "data/database/market_research.duckdb"), read_only=True) as con:
        run_id = con.execute("select run_id from research_runs where status='COMPLETE' order by trade_date desc,completed_at desc,run_id desc limit 1").fetchone()[0]
        columns = "run_id,sector_id,current_eligible,potential_eligible,potential_branch,potential_branches,current_rank,potential_rank,m1,b1,rel1,p1,q5,q20,dq5_3,b_delta3,ma20_width,ma20_delta3,early_width,amount_a,top1_positive_share,member_count,quote_valid_count,feature_valid_count,early_count,positive_count,quote_coverage,feature_coverage,risk_coverage,quality,reason_codes,evidence,input_members_hash,rank_universe_hash"
        duck_rows = con.execute(f"select {columns} from research_sector_states where run_id=? order by coalesce(current_rank,potential_rank,999999),sector_id", [run_id]).fetchall()
    with PostgresRepository() as repo:
        pg_rows = repo.research_sector_state_rows(str(run_id))
    report = {"contract_version": "RESEARCH_SECTOR_STATE_PG_SHADOW_V1", "generated_at_utc": datetime.now(timezone.utc).isoformat(), "run_id": str(run_id), "duckdb_count": len(duck_rows), "postgres_count": len(pg_rows), "rows_match": canonical_rows(duck_rows) == canonical_rows(pg_rows), "status": "PASS" if len(duck_rows) == len(pg_rows) and canonical_rows(duck_rows) == canonical_rows(pg_rows) else "FAIL", "online_switch_performed": False, "data_generation_triggered": False}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    tmp = REPORT.with_suffix(REPORT.suffix + ".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
