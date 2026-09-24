"""Print a read-only snapshot of overdue Focus outcome settlement work."""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from psycopg import sql

from scripts.apply_focus_pg_schema_v1 import _dsn
from src.focus_tracker.contracts import SOURCE_AUTHORITY_CONTRACT
from src.focus_tracker.materialize import read_full_master_calendar
from src.focus_tracker.outcome_monitor import settlement_monitor_snapshot
from src.workbench_db.postgres_repository import PostgresRepository


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED_PATH = ROOT / "data/normalized/adjusted_daily.parquet"
NORMALIZED_RELATIVE_PATH = "data/normalized/adjusted_daily.parquet"


def report(*, as_of_trade_date: date | None = None,
           detail_limit: int = 200) -> dict[str, object]:
    with PostgresRepository(dsn=_dsn()) as repository:
        if repository.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        schema = sql.Identifier(repository.schema)
        with repository.connection.cursor() as cur:
            cur.execute("set transaction read only")
            if as_of_trade_date is None:
                cur.execute(sql.SQL("select r.focus_run_id,r.trade_date "
                                    "from {}.focus_trade_date_heads h "
                                    "join {}.focus_runs r on r.focus_run_id=h.accepted_focus_run_id "
                                    "where h.source_authority_contract_id=%s "
                                    "and h.lineage_state='VALID' "
                                    "and r.core_publication_status='ACTIVATED' "
                                    "order by h.trade_date desc limit 1").format(schema, schema),
                            (SOURCE_AUTHORITY_CONTRACT,))
            else:
                cur.execute(sql.SQL("select r.focus_run_id,r.trade_date "
                                    "from {}.focus_trade_date_heads h "
                                    "join {}.focus_runs r on r.focus_run_id=h.accepted_focus_run_id "
                                    "where h.source_authority_contract_id=%s "
                                    "and h.lineage_state='VALID' "
                                    "and r.core_publication_status='ACTIVATED' "
                                    "and h.trade_date=%s").format(schema, schema),
                            (SOURCE_AUTHORITY_CONTRACT, as_of_trade_date))
            accepted = cur.fetchone()
            if accepted is None:
                repository.connection.rollback()
                return {"contract_id": "FOCUS_OUTCOME_OVERDUE_MONITOR_V1",
                        "status": "NO_VALID_ACCEPTED_FOCUS_HEAD",
                        "as_of_trade_date": str(as_of_trade_date) if as_of_trade_date else None,
                        "writes": 0}
            focus_run_id, resolved_date = str(accepted[0]), accepted[1]
            cur.execute("select sha256 from workbench_meta.artifact_catalog "
                        "where relative_path=%s and availability='AVAILABLE' "
                        "order by discovered_at desc limit 1",
                        (NORMALIZED_RELATIVE_PATH,))
            artifact = cur.fetchone()
        repository.connection.rollback()
        if artifact is None:
            raise RuntimeError("NO_AVAILABLE_NORMALIZED_ARTIFACT")
        artifact_sha = str(artifact[0]).strip()
        calendar = read_full_master_calendar(
            normalized_path=NORMALIZED_PATH,
            expected_sha256=artifact_sha,
            trade_date=resolved_date)
        with repository.connection.cursor() as cur:
            cur.execute("set transaction read only")
        result = settlement_monitor_snapshot(
            repository, calendar=calendar, as_of_trade_date=resolved_date,
            detail_limit=detail_limit)
        result.update({"status": "OK", "focus_run_id": focus_run_id,
                       "normalized_artifact_sha256": artifact_sha, "writes": 0})
        repository.connection.rollback()
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of-date", type=date.fromisoformat,
                        help="valid accepted Focus head date; defaults to latest")
    parser.add_argument("--detail-limit", type=int, default=200)
    args = parser.parse_args()
    print(json.dumps(report(as_of_trade_date=args.as_of_date,
                            detail_limit=args.detail_limit),
                     ensure_ascii=False, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
