"""Reproduce the scoped Lane L lifecycle fixture in a TEMP PostgreSQL table.

Example:
  python audit_r4_lane_lifecycle_pg_temp.py --candidate-root G:/codex_tmp/v4_daily_candidate_chain_20261020 --generation c5b78de8646af0db95c444cfe00f1e940cadffbe59ec45592e632484b930c381

The script reads the existing candidate files, adds one synthetic lifecycle-only
DATA_GAP row, inserts only into a session-local TEMP table, reads it back, and
closes the connection. It never writes a permanent database object.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path


REPO = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "config" / ".env").is_file() and (parent / "src").is_dir()
)
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from scripts.run_batch10_r2_d0_release import _load_local_dsn
from workbench_analysis.r43_structure_replay import conserve_lifecycle_status_rows


def read_gzip_rows(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-root", required=True, type=Path)
    parser.add_argument("--generation", required=True)
    parser.add_argument("--trade-date", default="2026-10-21")
    args = parser.parse_args()

    generation = args.candidate_root / "data/v4/dynamic_daily_owners" / args.trade_date / args.generation
    owner = generation / "owner_v3/owners" / args.trade_date
    lifecycle_path = generation / "sources" / args.trade_date / "lifecycle.json"
    lifecycle = json.loads(lifecycle_path.read_text(encoding="utf-8"))["source_rows"]
    statuses = read_gzip_rows(owner / "status.jsonl.gz")
    profiles = read_gzip_rows(owner / "profiles.jsonl.gz")
    core = read_gzip_rows(owner / "core.jsonl.gz")
    raw = read_gzip_rows(owner / "raw.jsonl.gz")
    identity = lambda rows: {row["security_id"] for row in rows if row.get("security_id")}

    synthetic = {
        "security_id": "SEC-R4-LIFECYCLE-FIXTURE-ONLY",
        "trade_date": args.trade_date,
        "status": "DATA_GAP",
    }
    projected = conserve_lifecycle_status_rows(statuses, lifecycle + [synthetic], trade_date=args.trade_date)
    source_by_id = {row["security_id"]: row for row in lifecycle + [synthetic]}
    core_ids = identity(core)
    profile_ids = identity(profiles)
    raw_ids = identity(raw)

    _load_local_dsn(REPO)
    import os
    import psycopg

    connection = psycopg.connect(os.environ["V4_NATIVE_PG_DSN"])
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "CREATE TEMP TABLE r4_lifecycle_fixture ("
                "security_id text PRIMARY KEY, trade_date date NOT NULL, source_status text NOT NULL, "
                "projected_status text NOT NULL, lifecycle_only boolean NOT NULL, core_present boolean NOT NULL, "
                "profile_present boolean NOT NULL, raw_present boolean NOT NULL, actual_bar_present boolean NOT NULL"
                ") ON COMMIT DROP"
            )
            cursor.executemany(
                "INSERT INTO r4_lifecycle_fixture VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                [
                    (
                        row["security_id"], row["trade_date"], source_by_id[row["security_id"]]["status"],
                        row["status"], bool(row.get("lifecycle_only")), row["security_id"] in core_ids,
                        row["security_id"] in profile_ids, row["security_id"] in raw_ids,
                        bool(row.get("actual_bar_present")),
                    )
                    for row in projected
                ],
            )
            cursor.execute(
                "SELECT count(*), count(DISTINCT security_id), "
                "count(*) FILTER (WHERE projected_status='ACTUAL_TRADED' AND NOT actual_bar_present), "
                "count(*) FILTER (WHERE lifecycle_only), "
                "count(*) FILTER (WHERE security_id='SEC-R4-LIFECYCLE-FIXTURE-ONLY' "
                "AND projected_status='DATA_GAP' AND NOT actual_bar_present "
                "AND NOT core_present AND NOT profile_present AND NOT raw_present) "
                "FROM r4_lifecycle_fixture"
            )
            counts = cursor.fetchone()
            cursor.execute(
                "SELECT security_id,source_status,projected_status,lifecycle_only,core_present,"
                "profile_present,raw_present,actual_bar_present FROM r4_lifecycle_fixture "
                "WHERE security_id='SEC-R4-LIFECYCLE-FIXTURE-ONLY'"
            )
            synthetic_readback = cursor.fetchone()
        connection.commit()
    finally:
        connection.close()

    print(json.dumps({
        "contract": "BATCH10_R4_LANE_L_TEMP_PG_FIXTURE_R1",
        "trade_date": args.trade_date,
        "source_counts": {
            "lifecycle": len(lifecycle), "status": len(statuses), "profile": len(profiles),
            "core": len(core), "raw": len(raw),
            "lifecycle_ids_missing_from_current_status": len(identity(lifecycle) - identity(statuses)),
        },
        "pg_temp_fixture": {
            "scope": "TEMP only; ON COMMIT DROP; connection closed after readback",
            "table_rows": counts[0], "distinct_ids": counts[1],
            "false_actual_bar_claims": counts[2], "lifecycle_only_rows": counts[3],
            "synthetic_fixture_readback": synthetic_readback,
        },
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
