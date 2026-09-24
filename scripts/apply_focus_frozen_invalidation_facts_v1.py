"""Install and backfill immutable V3.3 episode facts from accepted first sources."""
from __future__ import annotations

import argparse
from pathlib import Path

import psycopg

from scripts.apply_focus_pg_schema_v1 import _dsn
from src.focus_tracker.frozen_invalidation_facts import (derive_frozen_facts,
                                                         insert_episode_facts,
                                                         verify_episode_facts)
from src.focus_tracker.tracking_context import read_first_source_rows


DDL = Path(__file__).resolve().parents[1] / "src/workbench_db/focus_frozen_invalidation_facts_v1.sql"
REVISION_DDL = Path(__file__).resolve().parents[1] / "src/workbench_db/focus_frozen_fact_revisions_v1.sql"


def install(*, apply: bool = False, repair_initial_encoding: bool = False) -> dict[str, object]:
    with psycopg.connect(_dsn()) as con:
        try:
            with con.cursor() as cur:
                cur.execute("select pg_advisory_xact_lock(hashtext(%s))",
                            ("FOCUS_FROZEN_INVALIDATION_FACTS_V1",))
                cur.execute(DDL.read_text("utf-8"))
                cur.execute(REVISION_DDL.read_text("utf-8"))
                cur.execute("""select episode_id from workbench.focus_episodes
                    where source_family='V3_3_TODAY_CANDIDATE' order by episode_id""")
                episodes = {str(r[0]) for r in cur.fetchall()}
                # read_first_source_rows requires a repository-like connection holder.
                holder = type("ReadOnlyRepository", (), {"connection": con,
                                                           "schema": "workbench"})()
                first_rows = read_first_source_rows(holder, episode_ids=episodes)
                added = 0
                repaired = 0
                versioned = 0
                for episode in sorted(episodes):
                    cur.execute("""select e.first_trade_date,h.accepted_revision
                        from workbench.focus_episodes e join workbench.focus_trade_date_heads h
                          on h.trade_date=e.first_trade_date and h.lineage_state='VALID'
                        where e.episode_id=%s""", (episode,))
                    source_head = cur.fetchone()
                    if source_head is None:
                        raise ValueError("FROZEN_FACT_SOURCE_DATE_HEAD_UNAVAILABLE")
                    source_date, source_revision = source_head[0], int(source_head[1])
                    cur.execute("select count(*) from workbench.focus_episode_frozen_facts where episode_id=%s",
                                (episode,))
                    count = int(cur.fetchone()[0])
                    if repair_initial_encoding and count == 4:
                        expected = derive_frozen_facts(first_rows[episode])
                        if any(fact.value is not None for fact in expected):
                            cur.execute("""select fact_key from workbench.focus_episode_frozen_facts
                                where episode_id=%s and fact_value is not null""", (episode,))
                            if cur.fetchall():
                                raise ValueError("REPAIR_REFUSES_NONEMPTY_EXISTING_FACT")
                            cur.execute("""delete from workbench.focus_episode_frozen_facts
                                where episode_id=%s and contract_id=%s""",
                                (episode, "FOCUS_V33_FROZEN_INVALIDATION_FACTS_V1"))
                            if cur.rowcount != 4:
                                raise ValueError("REPAIR_REFUSES_INCOMPLETE_INITIAL_ROWS")
                            count = 0
                            repaired += 1
                    if count == 0:
                        insert_episode_facts(cur, episode_id=episode, row=first_rows[episode],
                                             source_revision=source_revision)
                        added += 1
                    cur.execute("""select count(*) from workbench.focus_episode_frozen_fact_revisions
                        where episode_id=%s and source_trade_date=%s and source_revision=%s""",
                        (episode, source_date, source_revision))
                    revision_count = int(cur.fetchone()[0])
                    if revision_count == 0:
                        if count == 0:
                            # The insert above created this version already.
                            cur.execute("""select count(*) from workbench.focus_episode_frozen_fact_revisions
                                where episode_id=%s and source_trade_date=%s and source_revision=%s""",
                                (episode, source_date, source_revision))
                            revision_count = int(cur.fetchone()[0])
                        else:
                            insert_episode_facts(cur, episode_id=episode,
                                                 row=first_rows[episode],
                                                 source_revision=source_revision,
                                                 insert_legacy=False)
                            versioned += 1
                    verify_episode_facts(cur, episode_id=episode,
                                         first_row=first_rows[episode])
                cur.execute("select count(*) from workbench.focus_episode_frozen_facts")
                fact_count = int(cur.fetchone()[0])
            if apply:
                con.commit()
            else:
                con.rollback()
        except Exception:
            con.rollback()
            raise
    return {"contract_id": "FOCUS_V33_FROZEN_INVALIDATION_FACTS_V1",
            "mode": "APPLIED" if apply else "ROLLBACK_REHEARSAL",
            "episodes": len(episodes), "backfilled_episodes": added,
            "versioned_episodes": versioned,
            "repaired_initial_encoding_episodes": repaired,
            "fact_rows": fact_count}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--repair-initial-encoding", action="store_true")
    args = parser.parse_args()
    print(install(apply=args.apply, repair_initial_encoding=args.repair_initial_encoding))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
