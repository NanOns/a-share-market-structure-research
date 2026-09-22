"""Compare the frozen DuckDB snapshot with PostgreSQL workbench tables."""
from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import psycopg
from psycopg import sql


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "runtime/postgres_migration/20260922/market_research.source.duckdb"


def dq(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")
    os.replace(temp, path)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    p.add_argument("--dsn", default=None)
    p.add_argument("--report", type=Path, default=ROOT / "runtime/postgres_migration/20260922/shadow_read_report.json")
    args = p.parse_args()
    source = duckdb.connect(str(args.source), read_only=True)
    dsn = args.dsn or os.environ.get("PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    result: dict[str, Any] = {"contract": "POSTGRES_SHADOW_READ_V1", "checked_at_utc": datetime.now(timezone.utc).isoformat(), "source": str(args.source), "tables": [], "status": "PASS"}
    try:
        with psycopg.connect(dsn) as pg:
            names = [r[0] for r in source.execute("select table_name from information_schema.tables where table_schema='main' and table_type='BASE TABLE' order by table_name").fetchall()]
            for table in names:
                source_count = int(source.execute(f"select count(*) from main.{dq(table)}").fetchone()[0])
                with pg.cursor() as cur:
                    cur.execute(sql.SQL("select count(*) from workbench.{}").format(sql.Identifier(table)))
                    target_count = int(cur.fetchone()[0])
                status = "PASS" if source_count == target_count else "FAIL"
                if status == "FAIL":
                    result["status"] = "FAIL"
                result["tables"].append({"table": table, "source_row_count": source_count, "target_row_count": target_count, "status": status})
    finally:
        source.close()
    write_atomic(args.report, result)
    print(json.dumps({"status": result["status"], "tables": len(result["tables"]), "failures": sum(1 for x in result["tables"] if x["status"] == "FAIL"), "report": str(args.report)}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
