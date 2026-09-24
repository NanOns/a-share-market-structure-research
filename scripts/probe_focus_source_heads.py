"""Read-only authority audit for the latest PostgreSQL research publication."""
from __future__ import annotations

import psycopg

from apply_focus_pg_schema_v1 import _dsn


def main() -> int:
    with psycopg.connect(_dsn()) as pg:
        with pg.transaction():
            pg.execute("set transaction read only")
            with pg.cursor() as cur:
                cur.execute("""select h.trade_date,h.publication_id,p.status
                               from workbench.publication_heads h
                               join workbench.publications p using(publication_id)
                               order by h.trade_date desc limit 1""")
                head = cur.fetchone()
                if not head:
                    raise RuntimeError("NO_PUBLICATION_HEAD")
                trade_date, publication_id, status = head
                cur.execute("""select run_id,status,algorithm_version,history_basis
                               from workbench.research_runs
                               where trade_date=%s and publication_id=%s
                               order by run_id""", (trade_date, publication_id))
                v3_runs = cur.fetchall()
                cur.execute("""select b.bundle_digest,b.research_run_id,r.status,r.result_count
                               from workbench.research_bundle_heads b
                               join workbench.research_runs_v3_3 r using(bundle_digest)
                               where b.trade_date=%s and b.publication_id=%s""",
                            (trade_date, publication_id))
                v33 = cur.fetchall()
                print({"trade_date": str(trade_date), "publication_id": str(publication_id),
                       "publication_status": str(status),
                       "v3_runs": [tuple(str(x) for x in row) for row in v3_runs],
                       "v3_3_head": [tuple(str(x) for x in row) for row in v33]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
