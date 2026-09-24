"""Read-only inventory of accepted daily fact fields for Focus materialization."""
from __future__ import annotations

import psycopg

from scripts.apply_focus_pg_schema_v1 import _dsn


def main() -> int:
    with psycopg.connect(_dsn()) as pg:
        with pg.transaction():
            pg.execute("set transaction read only")
            with pg.cursor() as cur:
                cur.execute("""select h.trade_date,h.publication_id from workbench.publication_heads h
                               order by h.trade_date desc limit 1""")
                date, publication = cur.fetchone()
                cur.execute("""select security_id,payload_json from workbench.stock_daily
                               where publication_id=%s order by security_id limit 1""", (publication,))
                stock = cur.fetchone()
                cur.execute("""select result_payload from workbench.research_candidates_v3_3 c
                               join workbench.research_bundle_heads b using(bundle_digest)
                               where b.trade_date=%s order by c.security_id limit 1""", (date,))
                candidate = cur.fetchone()
                cur.execute("""select table_name from information_schema.tables
                               where table_schema='workbench' and
                                 (table_name like '%%daily%%' or table_name like '%%bar%%'
                                  or table_name like '%%adjust%%') order by table_name""")
                tables = [row[0] for row in cur.fetchall()]
                cur.execute("""select artifact_id,sha256,availability from workbench_meta.artifact_catalog
                               where relative_path=%s order by discovered_at desc limit 3""",
                            ("data/normalized/adjusted_daily.parquet",))
                artifacts = [tuple(str(x) for x in row) for row in cur.fetchall()]
                print({"trade_date": str(date), "stock_daily_sample_id": stock[0] if stock else None,
                       "stock_payload_keys": sorted(stock[1]) if stock and isinstance(stock[1], dict) else None,
                       "candidate_payload_keys": sorted(candidate[0]) if candidate and isinstance(candidate[0], dict) else None,
                       "candidate_factor_keys": sorted(candidate[0].get("factor_evidence", {}))
                         if candidate and isinstance(candidate[0], dict)
                         and isinstance(candidate[0].get("factor_evidence"), dict) else None,
                       "potential_fact_tables": tables,
                       "normalized_artifacts": artifacts})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
