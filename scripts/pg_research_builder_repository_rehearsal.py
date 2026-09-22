"""Rehearse the PostgreSQL boundary used by the research builder.

This probe exercises ResearchRunStore start/fail and start/complete/visible,
plus PG-backed research-state reads. It never runs the research calculator.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import uuid

from workbench_db.research_builder_repository import PostgresResearchBuilderRepository
from workbench_service.research_runs import ResearchRunStore


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "runtime/postgres_migration/20260922/pg_research_builder_repository_rehearsal_report.json"


def atomic_write(payload: dict[str, object]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(REPORT.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(temporary, REPORT)


def main() -> int:
    dsn = os.environ.get("WORKBENCH_PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    checks: dict[str, object] = {}
    failures: list[str] = []
    probe_ids: list[str] = []
    try:
        repo = PostgresResearchBuilderRepository(dsn)
        with repo.connect() as connection:
            # These reads deliberately hit PG, not the analytical DuckDB
            # connection, so timestamptz/JSONB behavior is covered.
            checks["research_state_read"] = connection.execute("select 1 from research_runs limit 1").fetchone() is not None
            checks["research_state_fetch_df"] = "list_type" in list(connection.execute("select list_type from research_shortlist limit 1").fetch_df().columns)
            store = ResearchRunStore(connection)
            body = {
                "job_type": "BUILD_RESEARCH_V3",
                "publication_id": "probe-pub-" + uuid.uuid4().hex,
                "trade_date": "2099-01-01",
                "algorithm_version": "probe",
                "parameter_hash": "probe",
                "snapshot_id": "probe-snapshot",
                "membership_snapshot_id": "probe-membership",
                "dependency_bindings": {"probe": True},
            }
            failed = store.start(body)
            probe_ids.append(failed["run_id"])
            store.fail(failed["run_id"], "PROBE_ROLLBACK")
            checks["start_fail"] = connection.execute("select status from research_runs where run_id=?", [failed["run_id"]]).fetchone()[0] == "FAILED"

            complete = store.start({**body, "publication_id": "probe-pub-" + uuid.uuid4().hex})
            probe_ids.append(complete["run_id"])
            result = store.complete(complete["run_id"])
            visible = store.visible(complete["run_id"])
            checks["complete_visible"] = result["status"] == "COMPLETE" and visible["status"] == "COMPLETE"
            for run_id in probe_ids:
                connection.execute("delete from research_runs where run_id=?", [run_id])
    except Exception as exc:  # pragma: no cover - external database evidence
        checks["error"] = f"{type(exc).__name__}:{exc}"
        failures.append("postgres_research_builder_boundary")
    for name in ("research_state_read", "research_state_fetch_df", "start_fail", "complete_visible"):
        if checks.get(name) is not True:
            failures.append(name)
    payload = {
        "contract_version": "PG_RESEARCH_BUILDER_REPOSITORY_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dsn_target": "market_research@127.0.0.1:5432 (password omitted)",
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "checks": checks,
        "failures": sorted(set(failures)),
        "status": "PASS" if not failures else "BLOCKED",
        "acceptance": "DEGRADED_PASS_RESEARCH_BUILDER_REPOSITORY" if not failures else "BLOCKED",
        "next_stage": "observe_direct_pg_research_jobs" if not failures else "repair_research_builder_repository",
    }
    atomic_write(payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
