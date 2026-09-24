"""Preflight or atomically publish the first REAL_FORWARD Focus day.

Default mode is read-only apart from the content-addressed staging manifest.
PostgreSQL Focus business rows are written only with the explicit --apply flag.
This entry point intentionally accepts only an empty Focus head; subsequent
daily revision/replay orchestration remains a separate contract.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path

from scripts.apply_focus_pg_schema_v1 import _dsn
from src.focus_tracker.daily_builder import build_focus_daily_batch
from scripts.run_focus_initial_core_transaction import main as publish_initial_day
from src.focus_tracker.contracts import canonical_bytes
from src.focus_tracker.input_manifest import write_manifest
from src.focus_tracker.release_gate import require_core_publication_ready
from src.focus_tracker.source_reader import read_accepted_sources
from src.workbench_db.postgres_repository import PostgresRepository


ROOT = Path(__file__).resolve().parents[1]


def prepare(*, trade_date: date) -> dict[str, object]:
    """Build, verify, and atomically stage one exact-date REAL_FORWARD input."""
    with PostgresRepository(dsn=_dsn()) as repository:
        connection = repository.connection
        assert connection is not None
        with connection.cursor() as cur:
            cur.execute("set transaction isolation level repeatable read read only")
            cur.execute("""select h.publication_id,p.status
                           from workbench.publication_heads h
                           join workbench.publications p using(publication_id)
                           where h.trade_date=%s""", (trade_date,))
            exact_head = cur.fetchall()
        if len(exact_head) != 1 or exact_head[0][1] != "SUCCESS":
            raise RuntimeError("NO_ACCEPTED_PUBLICATION_FOR_EXPECTED_TRADE_DATE")
        connection.rollback()

    manifest, sources, plan, stock_facts, observations, baskets, closure = build_focus_daily_batch(
        evaluation_basis="REAL_FORWARD", expected_trade_date=trade_date)
    if sources.trade_date != trade_date or manifest.trade_date != trade_date:
        raise ValueError("FOCUS_EXPECTED_TRADE_DATE_MISMATCH")
    if any(decision.phase != "NEW" or decision.parent_episode_id is not None
           for decision in plan.decisions):
        raise ValueError("FOCUS_FIRST_FORWARD_RUN_REQUIRES_NEW_EPISODES_ONLY")
    if not observations or len(observations) != len(sources.rows):
        raise ValueError("FOCUS_FIRST_FORWARD_OBSERVATION_SOURCE_SET_MISMATCH")

    # Re-read accepted source identity while checking the frozen release gates.
    # Apply repeats these checks under the writer transaction and additionally
    # compares the freshly rebuilt manifest digest to this preflight digest.
    with PostgresRepository(dsn=_dsn()) as repository:
        connection = repository.connection
        assert connection is not None
        with connection.cursor() as cur:
            cur.execute("set transaction isolation level repeatable read read only")
        current = read_accepted_sources(repository, trade_date)
        if current.source_identity_digest != sources.source_identity_digest:
            raise RuntimeError("FOCUS_ACCEPTED_SOURCE_CHANGED_DURING_PREFLIGHT")
        require_core_publication_ready(
            manifest=manifest, sources=current, plan=plan,
            expected_trade_date=trade_date, repository=repository)
        with connection.cursor() as cur:
            cur.execute("select count(*) from workbench.focus_trade_date_heads")
            existing_heads = int(cur.fetchone()[0])
        if existing_heads:
            raise RuntimeError("FOCUS_FIRST_FORWARD_PUBLICATION_REQUIRES_EMPTY_HEAD")
        connection.rollback()

    target = (ROOT / "runtime/focus_staging" / trade_date.strftime("%Y%m%d") /
              f"input-manifest-{manifest.sha256}.json")
    write_manifest(output_path=target, manifest=manifest)
    return {
        "contract_id": "FOCUS_FIRST_FORWARD_PUBLICATION_V1",
        "mode": "PREFLIGHT_READY",
        "trade_date": trade_date.isoformat(),
        "evaluation_basis": manifest.payload["evaluation_basis"],
        "publication_id": sources.publication_id,
        "source_identity_digest": sources.source_identity_digest,
        "source_rows": len(sources.rows),
        "source_capabilities": sources.capabilities,
        "tracking_keys": len(plan.tracking_keys),
        "observation_count": len(observations),
        "stock_fact_count": len(stock_facts),
        "entry_basket_count": len(baskets),
        "observation_quality": dict(Counter(
            item.observation.quality_status for item in observations)),
        "closure_digest": closure.input_digest,
        "manifest_sha256": manifest.sha256,
        "manifest_path": str(target),
        "release_gate_reasons": list(manifest.release_gate_reasons),
        "focus_business_rows_written": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trade-date", required=True, type=date.fromisoformat,
                        help="exact accepted publication trade date (YYYY-MM-DD)")
    parser.add_argument("--apply", action="store_true",
                        help="commit the first REAL_FORWARD Focus run and activate its head")
    args = parser.parse_args()

    report = prepare(trade_date=args.trade_date)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if not args.apply:
        return 0
    publish_initial_day(commit=True, expected_trade_date=args.trade_date,
                        expected_manifest_digest=str(report["manifest_sha256"]))
    print(json.dumps({"contract_id": "FOCUS_FIRST_FORWARD_PUBLICATION_V1",
                      "mode": "APPLY_COMMITTED",
                      "trade_date": args.trade_date.isoformat(),
                      "manifest_sha256": report["manifest_sha256"]},
                     ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
