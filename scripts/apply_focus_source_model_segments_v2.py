"""Install SOURCE_MODEL segment revision bindings transactionally."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import psycopg

from scripts.apply_focus_pg_schema_v1 import _dsn


CONTRACT_ID = "FOCUS_SOURCE_MODEL_SEGMENTS_V2"
DDL = Path(__file__).resolve().parents[1] / "src/workbench_db/focus_source_model_segments_v2.sql"


def install(*, apply: bool = False) -> dict[str, object]:
    statement = DDL.read_text("utf-8")
    checksum = hashlib.sha256(statement.encode("utf-8")).hexdigest()
    with psycopg.connect(_dsn()) as con:
        try:
            with con.cursor() as cur:
                cur.execute("select pg_advisory_xact_lock(hashtext(%s))", (CONTRACT_ID,))
                cur.execute(statement)
                cur.execute("""select count(*),count(selection_contract_family)
                    from workbench.focus_episode_segments""")
                total, bound = (int(value) for value in cur.fetchone())
                if total != bound:
                    raise RuntimeError("FOCUS_SOURCE_MODEL_SEGMENT_BACKFILL_INCOMPLETE")
            if apply:
                con.commit()
            else:
                con.rollback()
        except Exception:
            con.rollback()
            raise
    return {"contract_id": CONTRACT_ID, "ddl_sha256": checksum,
            "mode": "APPLIED" if apply else "ROLLBACK_REHEARSAL",
            "segment_count": total, "bound_selection_contract_count": bound}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(install(apply=args.apply))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
