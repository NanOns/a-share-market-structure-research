"""Rehearse the PostgreSQL research-run identity and rollback contract."""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_db.postgres_repository import PostgresRepository  # noqa: E402
from workbench_db.postgres_research_repository import PostgresResearchRepository  # noqa: E402


REPORT = ROOT / "runtime/postgres_migration/20260922/pg_research_write_contract_rehearsal_report.json"


class RollbackProbe(Exception):
    pass


def main() -> int:
    probe = uuid.uuid4().hex
    run_id = "research-boundary-probe-" + probe
    checks: dict[str, object] = {"run_id": run_id}
    failures: list[str] = []
    try:
        with PostgresRepository() as repository:
            heads = repository.publication_heads()
            latest = heads["items"][0]
            writer = PostgresResearchRepository(repository)
            body = {
                "job_type": "BUILD_RESEARCH_V3",
                "publication_id": latest["publication_id"],
                "trade_date": latest["trade_date"],
                "algorithm_version": "RESEARCH_WRITE_BOUNDARY_PROBE_V1",
                "parameter_hash": "probe-parameter-hash",
                "snapshot_id": "probe-snapshot-" + probe,
                "membership_snapshot_id": "probe-membership-" + probe,
                "dependency_bindings": {"probe": probe, "analysis_slices": []},
            }
            try:
                with repository.transaction():
                    first = writer.start(body)
                    second = writer.start(body)
                    checks["start_first"] = first
                    checks["start_repeat"] = second
                    sector = {
                        "sector_id": "PROBE:SECTOR",
                        "current_eligible": True,
                        "potential_eligible": False,
                        "potential_branches": {},
                        "quality": "UNKNOWN",
                        "reason_codes": ["PROBE"],
                        "evidence": {"probe": True},
                    }
                    role = {
                        "sector_id": "PROBE:SECTOR",
                        "security_id": "PROBE.SECURITY",
                        "role": "EARLY_WATCH",
                        "role_rank": 1,
                        "role_reason_codes": ["PROBE"],
                        "evidence": {"probe": True},
                    }
                    complete = writer.complete(str(first["run_id"]), sector_states=[sector], member_roles=[role])
                    complete_repeat = writer.complete(str(first["run_id"]), sector_states=[sector], member_roles=[role])
                    visible = writer.visible(str(first["run_id"]))
                    checks["complete"] = complete
                    checks["complete_repeat"] = complete_repeat
                    checks["visible"] = visible
                    raise RollbackProbe()
            except RollbackProbe:
                checks["rollback_exception_caught"] = True
            checks["run_after_rollback"] = repository.fetch("select run_id from workbench.research_runs where run_id=%s", (run_id,))
            checks["state_after_rollback"] = repository.fetch("select run_id from workbench.research_sector_states where run_id=%s", (run_id,))
            checks["roles_after_rollback"] = repository.fetch("select run_id from workbench.research_sector_member_roles where run_id=%s", (run_id,))
            if checks["run_after_rollback"] or checks["state_after_rollback"] or checks["roles_after_rollback"]:
                failures.append("rollback_left_research_rows")
            if (checks.get("start_first") or {}).get("reused") is not False:  # type: ignore[union-attr]
                failures.append("start_identity")
            if (checks.get("start_repeat") or {}).get("reused") is not True:  # type: ignore[union-attr]
                failures.append("start_idempotency")
            if (checks.get("complete") or {}).get("status") != "COMPLETE":  # type: ignore[union-attr]
                failures.append("complete_status")
            if (checks.get("complete_repeat") or {}).get("reused") is not True:  # type: ignore[union-attr]
                failures.append("complete_idempotency")
    except Exception as exc:  # pragma: no cover - report the gate failure
        checks["error"] = f"{type(exc).__name__}:{exc}"
        failures.append("research_write_boundary")

    report = {
        "contract_version": "PG_RESEARCH_WRITE_CONTRACT_REHEARSAL_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
        "acceptance": "DEGRADED_PASS_RESEARCH_IDENTITY_IDEMPOTENCY_ROLLBACK" if not failures else "BLOCKED",
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "next_stage": "operations_and_artifact_write_contract" if not failures else "repair_research_write_boundary",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(REPORT.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(temporary, REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
