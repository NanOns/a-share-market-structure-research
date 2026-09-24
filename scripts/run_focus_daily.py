"""Exact-date Focus daily orchestration with explicit preflight and apply.

The current core writer only accepts an empty Focus head. Existing heads are
rejected before batch construction until the multi-day writer is available.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from scripts.apply_focus_pg_schema_v1 import _dsn
from scripts.run_focus_core_publication import prepare
from scripts.run_focus_initial_core_transaction import main as publish_initial_day
from scripts.run_focus_continuation_core_transaction import publish_next_day
from scripts.run_focus_outcome_settlement import run as settle_outcomes
from src.focus_tracker.daily_builder import build_focus_daily_batch
from src.focus_tracker.daily_head_plan import read_daily_head_plan
from src.focus_tracker.input_manifest import write_manifest
from src.focus_tracker.release_gate import require_core_publication_ready
from src.focus_tracker.source_reader import read_accepted_sources
from src.workbench_db.postgres_repository import PostgresRepository


CONTRACT_ID = "FOCUS_DAILY_RUNNER_V1"
ROOT = Path(__file__).resolve().parents[1]


def _head_plan(trade_date: date):
    with PostgresRepository(dsn=_dsn()) as repository:
        connection = repository.connection
        assert connection is not None
        with connection.cursor() as cur:
            cur.execute("set transaction isolation level repeatable read read only")
            plan = read_daily_head_plan(repository, trade_date=trade_date)
        connection.rollback()
    return plan


def _prepare_next_day(trade_date: date) -> dict[str, object]:
    manifest, sources, plan, stock_facts, observations, baskets, closure = build_focus_daily_batch(
        evaluation_basis="REAL_FORWARD", expected_trade_date=trade_date)
    if len(observations) != len(plan.episode_tracking or plan.decisions):
        raise ValueError("FOCUS_CONTINUATION_OBSERVATION_SET_INCOMPLETE")
    with PostgresRepository(dsn=_dsn()) as repository:
        connection = repository.connection
        assert connection is not None
        with connection.cursor() as cur:
            cur.execute("set transaction isolation level repeatable read read only")
        live = read_accepted_sources(repository, trade_date)
        if live.source_identity_digest != sources.source_identity_digest:
            raise RuntimeError("FOCUS_ACCEPTED_SOURCE_CHANGED_DURING_PREFLIGHT")
        require_core_publication_ready(
            manifest=manifest, sources=live, plan=plan,
            expected_trade_date=trade_date, repository=repository)
        connection.rollback()
    target = (ROOT / "runtime/focus_staging" / trade_date.strftime("%Y%m%d") /
              f"input-manifest-{manifest.sha256}.json")
    write_manifest(output_path=target, manifest=manifest)
    return {"manifest_sha256": manifest.sha256,
            "publication_id": sources.publication_id,
            "source_rows": len(sources.rows),
            "tracking_keys": len(plan.tracking_keys),
            "tracking_episodes": len(plan.episode_tracking or plan.decisions),
            "observation_count": len(observations),
            "predecessor_focus_run_id": _head_plan(trade_date).predecessor_focus_run_id,
            "manifest_path": str(target)}


def run(*, trade_date: date, apply: bool = False) -> dict[str, object]:
    """Run the supported first-day path; fail closed on multi-day input."""
    head_plan = _head_plan(trade_date)
    if head_plan.status == "INITIAL_DAY":
        preflight = prepare(trade_date=trade_date)
    elif head_plan.status == "NEXT_DAY":
        preflight = _prepare_next_day(trade_date)
    else:
        raise RuntimeError("FOCUS_DAILY_" + head_plan.status + "_WRITER_PENDING")
    result: dict[str, object] = {
        "contract_id": CONTRACT_ID,
        "trade_date": trade_date.isoformat(),
        "mode": "APPLY" if apply else "PREFLIGHT",
        "head_plan_status": head_plan.status,
        "planned_revision": head_plan.revision,
        "publication_id": preflight["publication_id"],
        "core_status": "PREFLIGHT_READY",
        "manifest_sha256": preflight["manifest_sha256"],
        "source_rows": preflight["source_rows"],
        "tracking_keys": preflight["tracking_keys"],
        "tracking_episodes": preflight.get("tracking_episodes",
                                           preflight["tracking_keys"]),
        "observation_count": preflight["observation_count"],
        "outcome_status": "NOT_RUN",
    }
    if not apply:
        return result
    if head_plan.status == "INITIAL_DAY":
        publish_initial_day(commit=True, expected_trade_date=trade_date,
                            expected_manifest_digest=str(preflight["manifest_sha256"]))
    else:
        publication = publish_next_day(
            trade_date=trade_date,
            expected_manifest_digest=str(preflight["manifest_sha256"]), commit=True)
        result["core_publication"] = publication
    result["core_status"] = "ACTIVATED"
    try:
        settlement = settle_outcomes(trade_date=trade_date, apply=True)
        result["outcome_status"] = settlement.get("status", "UNKNOWN")
        result["outcome_result"] = settlement
    except Exception as exc:
        # Core activation is already committed; report the independent outcome
        # failure rather than pretending the Focus head was rolled back.
        result["outcome_status"] = "DEGRADED"
        result["outcome_error"] = type(exc).__name__
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trade-date", required=True, type=date.fromisoformat)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preflight", action="store_true", help="read-only preflight (default)")
    mode.add_argument("--apply", action="store_true", help="commit supported core day, then settle outcomes")
    args = parser.parse_args()
    try:
        report = run(trade_date=args.trade_date, apply=args.apply)
    except (RuntimeError, ValueError) as exc:
        report = {"contract_id": CONTRACT_ID, "trade_date": args.trade_date.isoformat(),
                  "mode": "APPLY" if args.apply else "PREFLIGHT",
                  "core_status": "BLOCKED", "reason": str(exc), "outcome_status": "NOT_RUN"}
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, default=str))
    return 0 if report["outcome_status"] != "DEGRADED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
