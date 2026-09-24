"""Rollback-only replay probe for FOCUS_STATISTICS_MATERIALIZATION_V1."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from apply_focus_pg_schema_v1 import _dsn
import psycopg

from focus_tracker.read_api import FocusTrackerReadAPI
from scripts.materialize_focus_statistics import materialize_in_transaction

RUN_ID = "focus-statistics-probe-run"
AS_OF = date(2026, 9, 22)

DDL = (
    "create temp table focus_runs (focus_run_id text,trade_date date,evaluation_basis text,"
    "core_publication_status text,revision int,state_contract_id text)",
    "create temp table focus_episodes (episode_id text,source_family text,entity_type text,"
    "selection_contract_family text)",
    "create temp table focus_episode_anchors (anchor_id text,episode_id text,anchor_type text,"
    "trade_date date,focus_run_id text,price_basis text)",
    "create temp table focus_episode_segments (episode_id text,segment_type text,start_trade_date date,"
    "source_model_contract_id text,state_contract_id text)",
    "create temp table focus_episode_outcomes (anchor_id text,horizon int,target_revision int,"
    "target_trade_date date,status text,evaluation_basis text,forward_return numeric,mfe numeric,mdd numeric,"
    "input_digest char(64))",
    "create temp table focus_outcome_heads (anchor_id text,horizon int,accepted_target_revision int)",
    "create temp table focus_statistics_batches (statistics_batch_id text primary key,focus_run_id text,"
    "as_of_trade_date date,statistics_contract_id text,input_digest char(64),group_count int,outcome_count int,"
    "created_at_utc timestamptz default now(),unique(focus_run_id,statistics_contract_id,input_digest))",
    "create temp table focus_statistics_rows (statistics_batch_id text,source_family text,entity_type text,"
    "selection_contract_family text,source_model_contract_id text,state_contract_id text,anchor_type text,"
    "horizon int,evaluation_basis text,price_basis text,sample_count int,signal_date_count int,"
    "incomplete_count int,gate_status text,p25_return numeric,median_return numeric,p75_return numeric,"
    "max_mfe numeric,worst_mdd numeric,primary key(statistics_batch_id,source_family,entity_type,"
    "selection_contract_family,source_model_contract_id,state_contract_id,anchor_type,horizon,"
    "evaluation_basis,price_basis))",
    "create temp table focus_statistics_heads (focus_run_id text primary key,statistics_batch_id text,"
    "activated_at_utc timestamptz default now())",
)


def _add_group(cur, *, family: str, basis: str, contract: str, count: int, dates: int,
               start: int, future: bool = False, incomplete: bool = False) -> list[str]:
    anchors = []
    episode_id = f"episode-{family}-{basis}-{contract}"
    cur.execute("insert into pg_temp.focus_episodes values (%s,%s,'STOCK','SELECTION_V1')",
                (episode_id, family))
    cur.execute("insert into pg_temp.focus_episode_segments values "
                "(%s,'SOURCE_MODEL',%s,%s,'STATE_V1')",
                (episode_id, date(2026, 1, 1), contract))
    for i in range(count):
        anchor_id = f"anchor-{family}-{basis}-{contract}-{i}"
        anchors.append(anchor_id)
        signal_day = date(2026, 1, 1) + timedelta(days=i % dates)
        target_day = AS_OF
        target_revision = 1
        status = "SOURCE_REVISED" if incomplete and i == count - 1 else "OBSERVED"
        value = Decimal(i + start) / Decimal("1000")
        cur.execute("insert into pg_temp.focus_episode_anchors values (%s,%s,'FIRST_FOCUS',%s,%s,'LOCAL_ADJUSTED')",
                    (anchor_id, episode_id, signal_day, RUN_ID))
        cur.execute("insert into pg_temp.focus_episode_outcomes values "
                    "(%s,5,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (anchor_id, target_revision, target_day, status, basis,
                     value if status == "OBSERVED" else None,
                     Decimal("0.20") if status == "OBSERVED" else None,
                     Decimal("-0.10") if status == "OBSERVED" else None,
                     str(i + start).zfill(64)))
        cur.execute("insert into pg_temp.focus_outcome_heads values (%s,5,%s)", (anchor_id, target_revision))
    if future:
        anchor_id = f"anchor-{family}-{basis}-{contract}-future"
        cur.execute("insert into pg_temp.focus_episode_anchors values (%s,%s,'FIRST_FOCUS',%s,%s,'LOCAL_ADJUSTED')",
                    (anchor_id, episode_id, date(2026, 2, 1), RUN_ID))
        cur.execute("insert into pg_temp.focus_episode_outcomes values "
                    "(%s,5,1,%s,'OBSERVED',%s,0.5,0.2,-0.1,%s)",
                    (anchor_id, date(2026, 9, 23), basis, "a" * 64))
        cur.execute("insert into pg_temp.focus_outcome_heads values (%s,5,1)", (anchor_id,))
    return anchors


def run_probe() -> dict[str, object]:
    with psycopg.connect(_dsn()) as pg:
        try:
            with pg.cursor() as cur:
                for statement in DDL:
                    cur.execute(statement)
            pg.commit()  # Temporary fixture schema only.
            with pg.cursor() as cur:
                cur.execute("insert into pg_temp.focus_runs values (%s,%s,'HISTORICAL_RECONSTRUCTED','ACTIVATED',1,'STATE_V1')",
                            (RUN_ID, AS_OF))
                ready_ids = _add_group(cur, family="READY_HIST", basis="HISTORICAL_RECONSTRUCTED",
                                       contract="SOURCE_A", count=30, dates=5, start=0,
                                       incomplete=True, future=True)
                _add_group(cur, family="READY_REAL", basis="REAL_FORWARD", contract="SOURCE_A",
                           count=30, dates=5, start=100)
                _add_group(cur, family="INSUFFICIENT_ROWS", basis="HISTORICAL_RECONSTRUCTED",
                           contract="SOURCE_A", count=29, dates=5, start=200)
                _add_group(cur, family="INSUFFICIENT_DATES", basis="HISTORICAL_RECONSTRUCTED",
                           contract="SOURCE_B", count=30, dates=4, start=300)
            pg.commit()  # Fixture data is temporary and removed with this session.

            with pg.cursor() as cur:
                cur.execute("set transaction isolation level repeatable read")
                cur.execute("set transaction read write")
                first = materialize_in_transaction(cur, focus_run_id=RUN_ID, apply=True,
                                                   schema_name="pg_temp")
                second = materialize_in_transaction(cur, focus_run_id=RUN_ID, apply=True,
                                                    schema_name="pg_temp")
                assert first["statistics_batch_id"] == second["statistics_batch_id"]
                cur.execute("select statistics_batch_id,source_family,evaluation_basis,source_model_contract_id,"
                            "sample_count,signal_date_count,incomplete_count,gate_status,p25_return,median_return,"
                            "p75_return from pg_temp.focus_statistics_rows order by source_family")
                rows = cur.fetchall()
                cur.execute("select count(*) from pg_temp.focus_statistics_batches")
                batch_count = cur.fetchone()[0]
                assert batch_count == 1, batch_count
                by_family = {row[1]: row for row in rows}
                hist = by_family["READY_HIST"]
                real = by_family["READY_REAL"]
                low_rows = by_family["INSUFFICIENT_ROWS"]
                low_dates = by_family["INSUFFICIENT_DATES"]
                assert hist[4:8] == (29, 5, 1, "INSUFFICIENT_SAMPLES"), hist
                assert hist[8:] == (None, None, None), hist
                assert real[2] == "REAL_FORWARD" and real[4:8] == (30, 5, 0, "READY"), real
                assert all(value is not None for value in real[8:]), real
                assert low_rows[4:8] == (29, 5, 0, "INSUFFICIENT_SAMPLES"), low_rows
                assert low_dates[4:8] == (30, 4, 0, "INSUFFICIENT_SAMPLES"), low_dates
                assert {row[3] for row in rows} == {"SOURCE_A", "SOURCE_B"}
                assert len(rows) == 4

                # Accept a later target revision for one observed row. The input digest
                # and deterministic batch identity must change, while the new head wins.
                revised_anchor = ready_ids[0]
                cur.execute("insert into pg_temp.focus_episode_outcomes values "
                            "(%s,5,2,%s,'OBSERVED','HISTORICAL_RECONSTRUCTED',0.777,0.25,-0.12,%s)",
                            (revised_anchor, AS_OF, "f" * 64))
                cur.execute("update pg_temp.focus_outcome_heads set accepted_target_revision=2 "
                            "where anchor_id=%s and horizon=5", (revised_anchor,))
                revised = materialize_in_transaction(cur, focus_run_id=RUN_ID, apply=True,
                                                     schema_name="pg_temp")
                assert revised["input_digest"] != first["input_digest"]
                assert revised["statistics_batch_id"] != first["statistics_batch_id"]
                cur.execute("select statistics_batch_id from pg_temp.focus_statistics_heads where focus_run_id=%s",
                            (RUN_ID,))
                assert cur.fetchone()[0] == revised["statistics_batch_id"]
                cur.execute("select count(*) from pg_temp.focus_statistics_batches")
                assert cur.fetchone()[0] == 2
                pg.rollback()

            with pg.cursor() as cur:
                cur.execute("select (select count(*) from pg_temp.focus_statistics_batches),"
                            "(select count(*) from pg_temp.focus_statistics_rows),"
                            "(select count(*) from pg_temp.focus_statistics_heads)")
                persisted = cur.fetchone()
                assert persisted == (0, 0, 0), persisted
            pg.rollback()
            return {"contract": "FOCUS_STATISTICS_REPLAY_PROBE_V1",
                    "ready_hist_observed_count": hist[4], "ready_hist_incomplete_count": hist[6],
                    "minimum_ready_sample_count": real[4], "minimum_ready_signal_dates": real[5],
                    "real_forward_separate_group": real[2], "row_gate": low_rows[7],
                    "date_gate": low_dates[7], "future_target_excluded": True,
                    "same_input_idempotent": True, "accepted_revision_changes_digest": True,
                    "groups_per_batch": len(rows), "persisted_changes": sum(persisted)}
        finally:
            pg.rollback()


if __name__ == "__main__":
    print(run_probe())
