"""Run the controlled FOCUS-04 outcome task for one accepted core head.

Preview is read-only. Persisting outcomes requires the explicit ``--apply`` flag.
The outcome writer itself opens its own transaction and never changes core heads.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
import os
from pathlib import Path
import tempfile

from psycopg import sql

from scripts.apply_focus_pg_schema_v1 import _dsn
from src.focus_tracker.basket_store import read_accepted_entry_basket
from src.focus_tracker.contracts import SOURCE_AUTHORITY_CONTRACT
from src.focus_tracker.materialize import (read_full_master_calendar,
                                           read_verified_slice)
from src.focus_tracker.settlement import (due_anchor_plan,
                                          materialize_due_outcomes,
                                          pending_settlement_tasks,
                                          read_target_data_audits,
                                          read_target_input_seals,
                                          settle_due_outcomes)
from src.workbench_db.postgres_repository import PostgresRepository


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED_PATH = ROOT / "data/normalized/adjusted_daily.parquet"
NORMALIZED_RELATIVE_PATH = "data/normalized/adjusted_daily.parquet"


def _atomic_write_report(path: Path, report: dict[str, object]) -> Path:
    target = path.resolve()
    if not target.is_relative_to(ROOT) or target == ROOT:
        raise ValueError("outcome report must be written inside the project")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", newline="\n", dir=target.parent,
                prefix="." + target.name + ".", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(report, handle, ensure_ascii=False, sort_keys=True,
                      indent=2, default=str)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        return target
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def run(*, trade_date: date | None = None, apply: bool = False) -> dict[str, object]:
    with PostgresRepository(dsn=_dsn()) as repository:
        if repository.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        schema = sql.Identifier(repository.schema)
        retry_task = None
        with repository.connection.cursor() as cur:
            if trade_date is None:
                for candidate in pending_settlement_tasks(repository, limit=100):
                    cur.execute(sql.SQL(
                        "select r.focus_run_id,r.trade_date,r.evaluation_basis "
                        "from {}.focus_trade_date_heads h join {}.focus_runs r "
                        "on r.focus_run_id=h.accepted_focus_run_id "
                        "where h.source_authority_contract_id=%s and h.lineage_state='VALID' "
                        "and r.core_publication_status='ACTIVATED' "
                        "and r.focus_run_id=%s and h.trade_date=%s").format(schema, schema),
                        (SOURCE_AUTHORITY_CONTRACT, candidate["focus_run_id"],
                         candidate["as_of_trade_date"]))
                    accepted_run = cur.fetchone()
                    if accepted_run is not None:
                        retry_task = candidate
                        break
                if retry_task is None:
                    cur.execute(sql.SQL(
                        "select r.focus_run_id,r.trade_date,r.evaluation_basis "
                        "from {}.focus_trade_date_heads h join {}.focus_runs r "
                        "on r.focus_run_id=h.accepted_focus_run_id "
                        "where h.source_authority_contract_id=%s and h.lineage_state='VALID' "
                        "and r.core_publication_status='ACTIVATED' "
                        "order by h.trade_date desc limit 1").format(schema, schema),
                        (SOURCE_AUTHORITY_CONTRACT,))
                    accepted_run = cur.fetchone()
            else:
                cur.execute(sql.SQL(
                    "select r.focus_run_id,r.trade_date,r.evaluation_basis "
                    "from {}.focus_trade_date_heads h join {}.focus_runs r "
                    "on r.focus_run_id=h.accepted_focus_run_id "
                    "where h.source_authority_contract_id=%s and h.lineage_state='VALID' "
                    "and r.core_publication_status='ACTIVATED' and h.trade_date=%s").format(
                        schema, schema), (SOURCE_AUTHORITY_CONTRACT, trade_date))
                accepted_run = cur.fetchone()
            if accepted_run is None:
                repository.connection.rollback()
                return {"mode": "PREVIEW" if not apply else "APPLY",
                        "status": "NO_VALID_ACCEPTED_FOCUS_HEAD",
                        "trade_date": str(trade_date) if trade_date else None}
            focus_run_id, as_of, basis = str(accepted_run[0]), accepted_run[1], str(accepted_run[2])
            cur.execute("select sha256 from workbench_meta.artifact_catalog "
                        "where relative_path=%s and availability='AVAILABLE' "
                        "order by discovered_at desc limit 1",
                        (NORMALIZED_RELATIVE_PATH,))
            artifact = cur.fetchone()
        repository.connection.rollback()
        if artifact is None:
            raise RuntimeError("NO_AVAILABLE_NORMALIZED_ARTIFACT")
        artifact_sha = str(artifact[0]).strip()

        calendar = read_full_master_calendar(normalized_path=NORMALIZED_PATH,
                                             expected_sha256=artifact_sha,
                                             trade_date=as_of)
        due = due_anchor_plan(repository, calendar=calendar, as_of_date=as_of)
        if not due:
            return {"mode": "PREVIEW" if not apply else "APPLY",
                    "status": "NO_DUE_OUTCOMES", "focus_run_id": focus_run_id,
                    "trade_date": str(as_of), "evaluation_basis": basis,
                    "normalized_artifact_sha256": artifact_sha,
                    "due_anchor_horizons": 0, "writes": 0}

        target_dates = {item.target_date for item in due}
        seals = read_target_input_seals(repository, target_dates=target_dates,
                                        normalized_artifact_sha256=artifact_sha,
                                        evaluation_basis=basis)
        audits = read_target_data_audits(repository, due_anchors=due,
                                         target_seals=seals,
                                         normalized_artifact_sha256=artifact_sha)
        baskets = {}
        security_ids = {item.entity_id for item in due if item.entity_type == "STOCK"}
        for episode_id in sorted({item.episode_id for item in due
                                  if item.entity_type == "SECTOR"}):
            basket = read_accepted_entry_basket(repository, episode_id)
            baskets[episode_id] = basket
            security_ids.update(basket.security_ids)
        if not security_ids:
            raise RuntimeError("DUE_OUTCOMES_HAVE_NO_PRICE_SECURITIES")
        minimum_date = min(item.anchor_date for item in due)
        repository.connection.rollback()
        normalized = read_verified_slice(
            normalized_path=NORMALIZED_PATH, expected_sha256=artifact_sha,
            minimum_date=minimum_date, trade_date=as_of,
            security_ids=security_ids)
        preview = materialize_due_outcomes(
            repository, calendar=calendar, as_of_trade_date=as_of,
            normalized=normalized, target_seals=seals,
            baskets_by_episode=baskets, target_audits=audits)
        counts = dict(sorted(Counter(item.status for item in preview).items()))
        reason_counts = dict(sorted(Counter(
            code for item in preview for code in item.reason_codes).items()))
        detail = []
        for anchor, outcome in zip(due, preview, strict=True):
            seal = seals.get(anchor.target_date)
            evidence = outcome.evidence
            detail.append({
                "episode_id": anchor.episode_id,
                "anchor_id": anchor.anchor_id,
                "anchor_type": anchor.anchor_type,
                "entity_type": anchor.entity_type,
                "entity_id": anchor.entity_id,
                "horizon": anchor.horizon,
                "anchor_date": anchor.anchor_date.isoformat(),
                "target_date": anchor.target_date.isoformat(),
                "status": outcome.status,
                "reason_code": outcome.reason_codes[0],
                "target_input_accepted": bool(seal and seal.accepted),
                "target_input_sealed": bool(seal and seal.sealed),
                "target_source_identity_kind": (seal.source_identity_kind if seal else
                                                 "NO_ACCEPTED_TARGET_HEAD"),
                "path_quality_status": evidence.get("path_quality_status"),
                "target_data_state": evidence.get("target_data_state"),
                "path_complete": bool(evidence.get("path_complete")),
                "path_gap_count": int(evidence.get("path_gap_count", 0)),
                "path_suspended_sessions": int(evidence.get("path_suspended_sessions", 0)),
                "path_unverified_gap_count": int(evidence.get("path_unverified_gap_count", 0)),
            })
        summary: dict[str, object] = {
            "mode": "APPLY" if apply else "PREVIEW",
            "status": "READY" if apply else "PREVIEW_READY",
            "focus_run_id": focus_run_id, "trade_date": str(as_of),
            "evaluation_basis": basis,
            "normalized_artifact_sha256": artifact_sha,
            "due_anchor_horizons": len(due), "status_counts": counts,
            "reason_code_counts": reason_counts,
            "target_input_seal_counts": {
                "accepted": sum(bool(row["target_input_accepted"]) for row in detail),
                "sealed": sum(bool(row["target_input_sealed"]) for row in detail),
                "identity_kinds": dict(sorted(Counter(
                    row["target_source_identity_kind"] for row in detail).items())),
            },
            "path_quality_counts": dict(sorted(Counter(
                str(row["path_quality_status"]) for row in detail).items())),
            "target_data_state_counts": dict(sorted(Counter(
                str(row["target_data_state"]) for row in detail).items())),
            "target_dates": sorted(str(day) for day in target_dates),
            "details": detail,
            "retry_task": retry_task,
            "writes": None if apply else 0}
        if apply:
            repository.connection.rollback()
            result = settle_due_outcomes(
                repository, focus_run_id=focus_run_id,
                as_of_trade_date=as_of, evaluation_basis=basis,
                normalized_artifact_sha256=artifact_sha,
                calendar=calendar, normalized=normalized,
                baskets_by_episode=baskets)
            summary["settlement"] = result
            if result.get("status") == "RETRY_BACKOFF":
                summary["status"] = "RETRY_BACKOFF"
        return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trade-date", type=date.fromisoformat,
                        help="accepted Focus head date; defaults to an eligible retry task, then latest valid head")
    parser.add_argument("--apply", action="store_true",
                        help="persist the prepared batch; default mode is read-only preview")
    parser.add_argument("--report", type=Path,
                        help="atomically write the complete JSON report inside the project")
    args = parser.parse_args()
    report = run(trade_date=args.trade_date, apply=args.apply)
    if args.report is not None:
        report["report_path"] = str(_atomic_write_report(args.report, report))
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
