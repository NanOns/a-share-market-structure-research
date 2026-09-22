"""Compare immutable membership entries for the latest research snapshot."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_db.postgres_repository import PostgresRepository  # noqa: E402

REPORT = ROOT / "runtime/postgres_migration/20260922/membership_entries_pg_shadow_report.json"


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


def digest(rows) -> str:
    payload = json.dumps(normalize(rows), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    with duckdb.connect(str(ROOT / "data/database/market_research.duckdb"), read_only=True) as con:
        snapshot_id = con.execute("select membership_snapshot_id from research_runs where status='COMPLETE' order by trade_date desc,completed_at desc,run_id desc limit 1").fetchone()[0]
        duck_rows = con.execute("select membership_snapshot_id,sector_id,security_id,payload_json from membership_entries where membership_snapshot_id=? order by sector_id,security_id", [snapshot_id]).fetchall()
    with PostgresRepository() as repo:
        pg_rows = repo.membership_entry_rows(str(snapshot_id))
    duck_digest = digest(duck_rows); pg_digest = digest(pg_rows); match = duck_digest == pg_digest and len(duck_rows) == len(pg_rows)
    status = "DEGRADED_PASS_EMPTY_SOURCE" if match and not duck_rows else ("PASS" if match else "FAIL")
    report = {"contract_version": "MEMBERSHIP_ENTRIES_PG_SHADOW_V1", "generated_at_utc": datetime.now(timezone.utc).isoformat(), "membership_snapshot_id": str(snapshot_id), "duckdb_count": len(duck_rows), "postgres_count": len(pg_rows), "duckdb_digest": duck_digest, "postgres_digest": pg_digest, "rows_match": match, "status": status, "note": "The selected current relation snapshot has no membership_entries rows; production member fallback uses relation_edge_intervals and requires a separate shadow.", "online_switch_performed": False, "data_generation_triggered": False}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    tmp = REPORT.with_suffix(REPORT.suffix + ".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if match else 2


if __name__ == "__main__":
    raise SystemExit(main())
