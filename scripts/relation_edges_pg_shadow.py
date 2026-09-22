"""Compare publication-bound relation edges between DuckDB and PostgreSQL."""
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

REPORT = ROOT / "runtime/postgres_migration/20260922/relation_edges_pg_shadow_report.json"


def digest(rows) -> str:
    raw = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    publication_id = "m4-9540768dfa3c23169cac2e2b2da25711"
    query = """select b.publication_id,b.source_scope,b.revision_no,e.sector_id,e.security_id,e.source_kind,e.from_revision,e.to_revision
               from relation_publication_bindings b join relation_edge_intervals e on e.source_scope=b.source_scope
                and e.from_revision<=b.revision_no and (e.to_revision is null or b.revision_no<e.to_revision)
              where b.publication_id=? order by b.source_scope,e.sector_id,e.security_id,e.source_kind"""
    with duckdb.connect(str(ROOT / "data/database/market_research.duckdb"), read_only=True) as con:
        duck_rows = con.execute(query, [publication_id]).fetchall()
    with PostgresRepository() as repo:
        pg_rows = repo.relation_edges_for_publication(publication_id)
    duck_digest = digest(duck_rows); pg_digest = digest(pg_rows); match = len(duck_rows) == len(pg_rows) and duck_digest == pg_digest
    report = {"contract_version": "RELATION_EDGES_PG_SHADOW_V1", "generated_at_utc": datetime.now(timezone.utc).isoformat(), "publication_id": publication_id, "duckdb_count": len(duck_rows), "postgres_count": len(pg_rows), "duckdb_digest": duck_digest, "postgres_digest": pg_digest, "rows_match": match, "status": "PASS" if match else "FAIL", "online_switch_performed": False, "data_generation_triggered": False}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    tmp = REPORT.with_suffix(REPORT.suffix + ".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if match else 2


if __name__ == "__main__":
    raise SystemExit(main())
