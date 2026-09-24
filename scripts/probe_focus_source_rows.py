"""Read-only FOCUS-02 source extraction check for an accepted PG date head."""
from __future__ import annotations

from collections import Counter

from src.focus_tracker.source_reader import read_accepted_sources
from src.workbench_db.postgres_repository import PostgresRepository
from scripts.apply_focus_pg_schema_v1 import _dsn


def main() -> int:
    with PostgresRepository(dsn=_dsn()) as repo:
        with repo.connection.cursor() as cur:
            cur.execute("set transaction read only")
            cur.execute("select max(trade_date) from workbench.publication_heads")
            trade_date = cur.fetchone()[0]
        if trade_date is None:
            raise RuntimeError("NO_PUBLICATION_HEAD")
        result = read_accepted_sources(repo, trade_date)
        counts = Counter(row.key.source_family for row in result.rows)
        print({"trade_date": str(result.trade_date),
               "publication_id": result.publication_id,
               "capabilities": result.capabilities,
               "row_counts": dict(counts),
               "source_contract_ids": sorted({(row.key.source_family, row.source_contract_id)
                                              for row in result.rows}),
               "source_identity_digest": result.source_identity_digest})
        repo.connection.rollback()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
