"""Plan an exact-date Focus head without changing accepted history."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from psycopg import sql

from .contracts import SOURCE_AUTHORITY_CONTRACT


CONTRACT_ID = "FOCUS_DAILY_HEAD_PLAN_V1"


@dataclass(frozen=True)
class DailyHeadPlan:
    trade_date: date
    revision: int
    predecessor_trade_date: date | None
    predecessor_focus_run_id: str | None
    accepted_focus_run_id: str | None
    status: str


def classify_head_plan(*, trade_date: date,
                       prior: tuple[date, str, str] | None,
                       same_day: tuple[str, int, str] | None,
                       oldest_replay: date | None) -> DailyHeadPlan:
    """Reject stale lineage and distinguish initial, next-day, and revision work."""
    if oldest_replay is not None and oldest_replay < trade_date:
        raise ValueError("FOCUS_REPLAY_REQUIRED_BEFORE_DAILY_RUN")
    if prior is not None:
        prior_date, prior_run, lineage = prior
        if prior_date >= trade_date or lineage != "VALID":
            raise ValueError("FOCUS_PREDECESSOR_HEAD_NOT_VALID")
    else:
        prior_date, prior_run = None, None
    if same_day is not None:
        accepted_run, revision, lineage = same_day
        if lineage not in {"VALID", "REPLAY_REQUIRED"} or revision < 1:
            raise ValueError("FOCUS_SAME_DAY_HEAD_INVALID")
        return DailyHeadPlan(trade_date, revision + 1, prior_date, prior_run,
                             accepted_run, "REVISION_REQUIRED")
    return DailyHeadPlan(trade_date, 1, prior_date, prior_run, None,
                         "NEXT_DAY" if prior_run else "INITIAL_DAY")


def read_daily_head_plan(repository, *, trade_date: date) -> DailyHeadPlan:
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL(
            "select trade_date,accepted_focus_run_id,lineage_state "
            "from {}.focus_trade_date_heads "
            "where trade_date<%s and source_authority_contract_id=%s "
            "order by trade_date desc limit 1").format(schema),
            (trade_date, SOURCE_AUTHORITY_CONTRACT))
        prior = cur.fetchone()
        cur.execute(sql.SQL(
            "select accepted_focus_run_id,accepted_revision,lineage_state "
            "from {}.focus_trade_date_heads "
            "where trade_date=%s and source_authority_contract_id=%s").format(schema),
            (trade_date, SOURCE_AUTHORITY_CONTRACT))
        same_day = cur.fetchone()
        cur.execute(sql.SQL(
            "select min(trade_date) from {}.focus_trade_date_heads "
            "where source_authority_contract_id=%s and lineage_state='REPLAY_REQUIRED'"
        ).format(schema), (SOURCE_AUTHORITY_CONTRACT,))
        oldest_replay = cur.fetchone()[0]
    return classify_head_plan(
        trade_date=trade_date,
        prior=(prior[0], str(prior[1]), str(prior[2])) if prior else None,
        same_day=(str(same_day[0]), int(same_day[1]), str(same_day[2])) if same_day else None,
        oldest_replay=oldest_replay)
