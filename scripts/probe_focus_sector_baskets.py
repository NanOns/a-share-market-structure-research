"""Read-only sector basket authority probe for the accepted publication."""
from __future__ import annotations

from collections import Counter

from scripts.apply_focus_pg_schema_v1 import _dsn
from src.focus_tracker.contracts import digest
from src.focus_tracker.sector_basket import baskets_from_accepted_publication
from src.focus_tracker.source_reader import read_accepted_sources
from src.workbench_db.postgres_repository import PostgresRepository


def main() -> int:
    with PostgresRepository(dsn=_dsn()) as repo:
        with repo.connection.cursor() as cur:
            cur.execute("set transaction read only")
            cur.execute("select max(trade_date) from workbench.publication_heads")
            trade_date = cur.fetchone()[0]
        accepted = read_accepted_sources(repo, trade_date)
        sectors = {row.key.entity_id for row in accepted.rows
                   if row.key.source_family == "V3_SECTOR_TRACK"}
        baskets = baskets_from_accepted_publication(repo, accepted.publication_id, sectors)
        repo.connection.rollback()
    print({"trade_date": str(trade_date), "sector_count": len(baskets),
           "source_kinds": dict(Counter(item.source_kind for item in baskets)),
           "membership_min": min(map(lambda item: len(item.security_ids), baskets)),
           "membership_max": max(map(lambda item: len(item.security_ids), baskets)),
           "basket_set_digest": digest([(item.sector_id, item.basket_digest)
                                         for item in baskets])})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
