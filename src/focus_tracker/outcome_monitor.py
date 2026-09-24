"""Read-only operational summaries for due and overdue outcome settlement."""
from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any, Sequence

from psycopg import sql

from .contracts import SOURCE_AUTHORITY_CONTRACT
from .settlement import (due_anchor_plan, pending_settlement_tasks)


CONTRACT_ID = "FOCUS_OUTCOME_OVERDUE_MONITOR_V1"


def settlement_monitor_snapshot(repository, *, calendar: Sequence[date],
                                as_of_trade_date: date,
                                detail_limit: int = 200) -> dict[str, Any]:
    """Summarize open outcomes and retry state without changing PostgreSQL."""
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    if not calendar or list(calendar) != sorted(set(calendar)) or as_of_trade_date not in calendar:
        raise ValueError("complete frozen calendar through as-of date required")
    if not 1 <= detail_limit <= 2000:
        raise ValueError("monitor detail limit outside 1..2000")

    session_index = {day: index for index, day in enumerate(calendar)}
    due = due_anchor_plan(repository, calendar=calendar,
                          as_of_date=as_of_trade_date)
    records = []
    for item in due:
        state = "SOURCE_REVISED" if item.source_revised else (item.current_status or "UNSETTLED")
        late_sessions = max(0, session_index[as_of_trade_date] -
                            session_index[item.target_date])
        records.append({"episode_id": item.episode_id,
                        "anchor_id": item.anchor_id,
                        "anchor_type": item.anchor_type,
                        "entity_type": item.entity_type,
                        "entity_id": item.entity_id,
                        "horizon": item.horizon,
                        "target_trade_date": item.target_date.isoformat(),
                        "status": state,
                        "overdue": late_sessions > 0,
                        "late_sessions": late_sessions,
                        "evaluation_basis": item.evaluation_basis})
    records.sort(key=lambda row: (-row["late_sessions"], row["target_trade_date"],
                                  row["entity_type"], row["entity_id"],
                                  row["anchor_type"], row["horizon"]))

    retry_due = pending_settlement_tasks(repository, limit=1000)
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL("select count(*),min(t.next_retry_at_utc) "
                            "from {}.focus_outcome_settlement_tasks t "
                            "join {}.focus_runs r using(focus_run_id) "
                            "join {}.focus_trade_date_heads h on h.trade_date=t.as_of_trade_date "
                            "and h.accepted_focus_run_id=t.focus_run_id "
                            "and h.source_authority_contract_id=%s and h.lineage_state='VALID' "
                            "where t.status='RETRY_PENDING' "
                            "and r.core_publication_status='ACTIVATED' "
                            "and t.next_retry_at_utc>clock_timestamp()")
                    .format(schema, schema, schema), (SOURCE_AUTHORITY_CONTRACT,))
        waiting_count, next_retry = cur.fetchone()

    return {"contract_id": CONTRACT_ID,
            "as_of_trade_date": as_of_trade_date.isoformat(),
            "evaluation_calendar_sessions": len(calendar),
            "due_open_count": len(records),
            "overdue_count": sum(row["overdue"] for row in records),
            "status_counts": dict(sorted(Counter(row["status"] for row in records).items())),
            "retry_ready_count": len(retry_due),
            "retry_backoff_count": int(waiting_count),
            "next_retry_at_utc": next_retry.isoformat() if next_retry else None,
            "details_truncated": len(records) > detail_limit,
            "details": records[:detail_limit]}
