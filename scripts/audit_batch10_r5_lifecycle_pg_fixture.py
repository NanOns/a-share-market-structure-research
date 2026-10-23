"""Exercise lifecycle/bar identity rules in a session-local development PG fixture."""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidence/functional_r8_implementation_20261021/supporting/BATCH10_R5_LIFECYCLE_PG_TEMP_FIXTURE.json"


def configured_dsn() -> str:
    values = {}
    for line in (ROOT / "config/.env").read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.partition("=")
        if sep:
            values[key.strip()] = value.strip().strip('"').strip("'")
    dsn = values.get("WORKBENCH_PG_DSN")
    if not dsn:
        raise RuntimeError("WORKBENCH_PG_DSN_REQUIRED")
    import psycopg.conninfo
    identity = psycopg.conninfo.conninfo_to_dict(dsn)
    if (identity.get("host"), identity.get("port"), identity.get("dbname")) != (
            "127.0.0.1", "5432", "market_research"):
        raise ValueError("R5_LIFECYCLE_PG_TARGET_MISMATCH")
    return dsn


def run() -> dict:
    with psycopg.connect(configured_dsn(), connect_timeout=5) as pg:
        pg.execute("SET TRANSACTION READ WRITE")
        identity = pg.execute("""select current_database(),
            (select oid from pg_database where datname=current_database()),
            current_setting('server_version_num'), current_setting('transaction_read_only')""").fetchone()
        if identity[0] != "market_research" or identity[3] != "off":
            raise ValueError("R5_LIFECYCLE_PG_SESSION_IDENTITY_MISMATCH")
        pg.execute("""CREATE TEMP TABLE r5_lifecycle_fixture (
            security_id text PRIMARY KEY, trade_date date NOT NULL, status text NOT NULL
        ) ON COMMIT DROP""")
        pg.execute("""CREATE TEMP TABLE r5_raw_bar_fixture (
            security_id text NOT NULL, trade_date date NOT NULL,
            PRIMARY KEY (security_id, trade_date)
        ) ON COMMIT DROP""")
        with pg.cursor() as cur:
            cur.executemany("INSERT INTO r5_lifecycle_fixture VALUES (%s,%s,%s)", [
            ("sid-actual-no-raw", "2026-10-22", "ACTUAL_TRADED"),
            ("sid-suspended-no-raw", "2026-10-22", "SUSPENDED"),
            ("sid-actual-same-raw", "2026-10-22", "ACTUAL_TRADED"),
            ("sid-actual-wrong-day-raw", "2026-10-22", "ACTUAL_TRADED"),
            ("sid-suspended-same-raw", "2026-10-22", "SUSPENDED"),
            ])
            cur.executemany("INSERT INTO r5_raw_bar_fixture VALUES (%s,%s)", [
            ("sid-actual-same-raw", "2026-10-22"),
            ("sid-actual-wrong-day-raw", "2026-10-21"),
            ("sid-suspended-same-raw", "2026-10-22"),
            ])
        rows = pg.execute("""SELECT l.security_id, l.status,
            EXISTS (SELECT 1 FROM r5_raw_bar_fixture b
                    WHERE b.security_id=l.security_id AND b.trade_date=l.trade_date) AS actual_bar_present,
            (EXISTS (SELECT 1 FROM r5_raw_bar_fixture b
                     WHERE b.security_id=l.security_id AND b.trade_date=l.trade_date)
             IS DISTINCT FROM (l.status='ACTUAL_TRADED')) AS status_conflict
            FROM r5_lifecycle_fixture l ORDER BY l.security_id""").fetchall()
        cases = [dict(security_id=r[0], status=r[1], actual_bar_present=r[2], status_conflict=r[3])
                 for r in rows]
        expected = {
            "sid-actual-no-raw": ("ACTUAL_TRADED", False, True),
            "sid-suspended-no-raw": ("SUSPENDED", False, False),
            "sid-actual-same-raw": ("ACTUAL_TRADED", True, False),
            "sid-actual-wrong-day-raw": ("ACTUAL_TRADED", False, True),
            "sid-suspended-same-raw": ("SUSPENDED", True, True),
        }
        actual = {r[0]: (r[1], r[2], r[3]) for r in rows}
        if actual != expected:
            raise ValueError("R5_LIFECYCLE_PG_TEMP_FIXTURE_MISMATCH")
        evidence = dict(
            contract_id="BATCH10_R5_LIFECYCLE_BAR_RECEIPT_PG_FIXTURE_R1",
            status="REAL_PG_TEMP_FIXTURE_PASS",
            database=dict(database=identity[0], database_oid=identity[1],
                          server_version_num=identity[2], transaction_read_only=identity[3]),
            scope="SESSION_LOCAL_TEMP_TABLES_ONLY_ON_COMMIT_DROP",
            rows=cases,
            permanent_schema_or_table_changes=False,
            formal_head_changed=False,
            production_accepted=False,
            generated_at=datetime.now().astimezone().isoformat(),
        )
        tmp = OUT.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, OUT)
        return evidence


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, sort_keys=True))
