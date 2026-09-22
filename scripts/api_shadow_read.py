"""Run a small API-vs-PostgreSQL shadow read without changing the service path."""
from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import psycopg


ROOT = Path(__file__).resolve().parents[1]


def normalize(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(k): normalize(v) for k, v in value.items()}
    return value


def get_json(base: str, path: str, params: dict[str, str]) -> Any:
    query = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{base}{path}?{query}", timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:28765")
    parser.add_argument("--dsn", default=None)
    parser.add_argument("--report", type=Path, default=ROOT / "runtime/postgres_migration/20260922/api_shadow_read_report.json")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    with psycopg.connect(dsn) as pg:
        with pg.cursor() as cur:
            cur.execute("""
                select h.trade_date::text,h.publication_id,p.revision,p.production_version
                from workbench.publication_heads h join workbench.publications p using(publication_id)
                where p.status='SUCCESS' and (p.production_version not like 'm4-%' or exists (select 1 from workbench.publication_analysis_snapshots a where a.publication_id=p.publication_id and a.domain='LOCAL_RECONSTRUCTED'))
                order by h.trade_date desc
            """)
            rows = cur.fetchall()
    expected = {"items": [{"trade_date": row[0], "publication_id": row[1]} for row in rows], "latest_publication_id": rows[0][1] if rows else None}
    actual = get_json(args.base_url, "/api/publications", {"include_analysis": "0"})
    result = {"contract": "API_SHADOW_READ_V1", "checked_at_utc": datetime.now(timezone.utc).isoformat(), "endpoint": "/api/publications?include_analysis=0", "status": "PASS" if normalize(actual) == normalize(expected) else "FAIL", "expected": expected, "actual": actual}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    temp = args.report.with_suffix(args.report.suffix + ".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(args.report)
    print(json.dumps({"status": result["status"], "items": len(rows), "report": str(args.report)}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
