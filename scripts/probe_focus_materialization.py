"""Read-only, one-security FOCUS-02 local adjusted artifact probe."""
from __future__ import annotations

from pathlib import Path

from scripts.apply_focus_pg_schema_v1 import _dsn
from src.focus_tracker.materialize import materialize_stock_facts
from src.focus_tracker.source_reader import read_accepted_sources
from src.workbench_db.postgres_repository import PostgresRepository


def main() -> int:
    with PostgresRepository(dsn=_dsn()) as repo:
        with repo.connection.cursor() as cur:
            cur.execute("set transaction read only")
            cur.execute("select max(trade_date) from workbench.publication_heads")
            trade_date = cur.fetchone()[0]
            accepted = read_accepted_sources(repo, trade_date)
            sid = next(row.key.entity_id for row in accepted.rows
                       if row.key.source_family == "V3_SHORTLIST_STOCK")
            cur.execute("""select sha256 from workbench_meta.artifact_catalog
                           where relative_path=%s and availability='AVAILABLE'
                           order by discovered_at desc limit 1""",
                        ("data/normalized/adjusted_daily.parquet",))
            artifact = cur.fetchone()
            if artifact is None:
                raise RuntimeError("NO_AVAILABLE_NORMALIZED_ARTIFACT")
            source_hash = str(artifact[0])
        repo.connection.rollback()
    normalized = Path("data/normalized/adjusted_daily.parquet")
    facts = materialize_stock_facts(normalized_path=normalized,
                                    expected_sha256=source_hash,
                                    trade_date=trade_date, starts={sid: trade_date})
    fact = facts[0]
    print({"trade_date": str(trade_date), "security_id": sid,
           "normalized_sha256": source_hash,
           "quality_status": fact.quality_status,
           "missing_state": fact.missing_state,
           "adjustment_version": fact.adjustment_version,
           "input_digest": fact.input_digest})
    return 0 if fact.quality_status == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
