"""Preview or apply an ordered Focus historical replay chain."""
from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from scripts.apply_focus_pg_schema_v1 import _dsn
from scripts.run_focus_daily import run as run_daily
from src.focus_tracker.replay import pending_replay_chain
from src.workbench_db.postgres_repository import PostgresRepository


CONTRACT_ID = "FOCUS_ORDERED_REPLAY_WRITER_V1"
ROOT = Path(__file__).resolve().parents[1]


def replay_chain(*, apply: bool = False, max_days: int = 100) -> dict[str, object]:
    if not 1 <= max_days <= 1000:
        raise ValueError("FOCUS_REPLAY_MAX_DAYS_OUT_OF_RANGE")
    with PostgresRepository(dsn=_dsn()) as repository:
        items = pending_replay_chain(repository)
        repository.connection.rollback()
    dates = [item.trade_date for item in items]
    if len(dates) > max_days:
        raise ValueError("FOCUS_REPLAY_CHAIN_EXCEEDS_BOUND")
    if not apply:
        return {"contract_id": CONTRACT_ID, "status": "PREVIEW",
                "trade_dates": [day.isoformat() for day in dates],
                "revisions": [item.accepted_revision + 1 for item in items],
                "write_count": 0}

    results = []
    for expected in items:
        with PostgresRepository(dsn=_dsn()) as repository:
            current = pending_replay_chain(repository)
            repository.connection.rollback()
        if not current or current[0].trade_date != expected.trade_date:
            raise RuntimeError("FOCUS_REPLAY_CHAIN_CHANGED_DURING_APPLY")
        result = run_daily(trade_date=expected.trade_date, apply=True)
        if result.get("core_status") != "ACTIVATED":
            raise RuntimeError("FOCUS_REPLAY_DATE_NOT_ACTIVATED:" + expected.trade_date.isoformat())
        results.append(result)
    with PostgresRepository(dsn=_dsn()) as repository:
        remaining = pending_replay_chain(repository)
        repository.connection.rollback()
    if remaining:
        raise RuntimeError("FOCUS_REPLAY_CHAIN_REMAINS_PENDING")
    report = {"contract_id": CONTRACT_ID, "status": "PASS",
              "trade_dates": [item["trade_date"] for item in results],
              "revisions": [item["planned_revision"] for item in results],
              "results": results, "write_count": len(results),
              "remaining_replay_dates": []}
    report["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    target_dir = ROOT / "reports/focus/replay"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / ("ordered-replay-" +
                          datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
    temp = target.with_name(target.name + "." + uuid.uuid4().hex + ".tmp")
    temp.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True,
                               indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(temp, target)
    report["receipt_path"] = str(target)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="commit each replay date in order")
    parser.add_argument("--max-days", type=int, default=100)
    args = parser.parse_args()
    try:
        report = replay_chain(apply=args.apply, max_days=args.max_days)
    except (RuntimeError, ValueError) as exc:
        report = {"contract_id": CONTRACT_ID, "status": "BLOCKED", "reason": str(exc),
                  "write_count": 0}
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
