"""Exercise PostgreSQL read adapters and a sandboxed config rollback.

This is a precutover gate.  It deliberately does not modify the tracked
configuration or inject PostgreSQL into the online service.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_db.postgres_repository import PostgresRepository  # noqa: E402
from workbench_service.today_research_bundle import TodayResearchBundleReader  # noqa: E402


REPORT = ROOT / "runtime/postgres_migration/20260922/pg_adapter_integration_rehearsal_report.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sandbox_config_rollback() -> dict[str, object]:
    """Prove an atomic PG overlay can be rolled back without touching config."""
    source = ROOT / "config/workbench.yaml"
    original = source.read_bytes()
    overlay = original.replace(
        b'engine: "duckdb"', b'engine: "postgresql"\n    dsn_env: "WORKBENCH_PG_DSN"\n    schema: "workbench"'
    ).replace(b"single_owner_required: true", b"single_owner_required: false")
    if b'engine: "postgresql"' not in overlay or b"dsn_env" not in overlay:
        raise RuntimeError("PG_CONFIG_OVERLAY_CONTRACT_FAILED")
    with tempfile.TemporaryDirectory(prefix="pg-config-rollback-") as directory:
        sandbox = Path(directory)
        active = sandbox / "workbench.yaml"
        backup = sandbox / "workbench.yaml.previous"
        active.write_bytes(original)
        backup.write_bytes(original)
        candidate = sandbox / "workbench.yaml.pg.tmp"
        candidate.write_bytes(overlay)
        os.replace(candidate, active)
        overlay_hash = sha256(active.read_bytes())
        rollback = sandbox / "workbench.yaml.rollback.tmp"
        rollback.write_bytes(backup.read_bytes())
        os.replace(rollback, active)
        restored_hash = sha256(active.read_bytes())
    return {
        "tracked_config_path": str(source),
        "tracked_config_sha256": sha256(original),
        "overlay_sha256": overlay_hash,
        "restored_sha256": restored_hash,
        "rollback_match": restored_hash == sha256(original),
        "tracked_config_touched": source.read_bytes() != original,
    }


def main() -> int:
    checks: dict[str, object] = {}
    failures: list[str] = []
    try:
        with PostgresRepository() as repository:
            heads = repository.publication_heads(include_analysis=True)
            checks["publication_heads"] = {
                "count": len(heads["items"]),
                "latest_publication_id": heads.get("latest_publication_id"),
                "analysis_capabilities_present": all("analysis_capabilities" in item for item in heads["items"]),
            }
            if not heads["items"] or not checks["publication_heads"]["analysis_capabilities_present"]:  # type: ignore[index]
                failures.append("publication_heads_adapter")

            reader = TodayResearchBundleReader(ROOT, repository=repository)
            listing = reader.list(page=1, page_size=20)
            first = listing.get("items", [None])[0]
            detail = reader.detail(str(first.get("security_id"))) if isinstance(first, dict) else {"status": "EMPTY"}
            checks["today_research_adapter"] = {
                "status": listing.get("status"),
                "total": listing.get("total"),
                "detail_status": detail.get("status"),
                "repository_injected": True,
            }
            if listing.get("status") not in {"READY", "EMPTY"} or (first and detail.get("status") != "READY"):
                failures.append("today_research_adapter")

            run_row = repository.fetch(
                "select run_id from workbench.research_runs where status='COMPLETE' order by trade_date desc,completed_at desc,run_id desc limit 1"
            )
            if not run_row:
                failures.append("research_run_missing")
            else:
                run_id = str(run_row[0][0])
                states = repository.research_sector_state_rows(run_id)
                roles = repository.research_sector_member_role_rows(run_id)
                checks["research_projection_adapters"] = {"run_id": run_id, "state_rows": len(states), "member_role_rows": len(roles)}
                if not states or not roles:
                    failures.append("research_projection_adapter")
    except Exception as exc:  # pragma: no cover - report the gate failure
        checks["repository_error"] = f"{type(exc).__name__}:{exc}"
        failures.append("repository_adapter_integration")

    try:
        checks["config_rollback"] = sandbox_config_rollback()
        if not checks["config_rollback"]["rollback_match"] or checks["config_rollback"]["tracked_config_touched"]:  # type: ignore[index]
            failures.append("config_rollback")
    except Exception as exc:  # pragma: no cover - report the gate failure
        checks["config_rollback_error"] = f"{type(exc).__name__}:{exc}"
        failures.append("config_rollback")

    report = {
        "contract_version": "PG_ADAPTER_INTEGRATION_REHEARSAL_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "checks": checks,
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
        "acceptance": "DEGRADED_PASS_PRECUTOVER_ADAPTER_AND_ROLLBACK" if not failures else "BLOCKED",
        "next_stage": "repository_adapter_boundary_implementation" if not failures else "repair_rehearsal_failures",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    tmp = REPORT.with_suffix(REPORT.suffix + ".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
