"""Verify the isolated daily DuckDB workspace without running generation."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path

from workbench_service.compute_workspace import compute_database_path, prepare_compute_workspace


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "runtime/postgres_migration/20260922/compute_workspace_rehearsal_report.json"


def main() -> int:
    source = (ROOT / "data/database/market_research.duckdb").resolve()
    checks: dict[str, object] = {}
    failures: list[str] = []
    try:
        target, refresh = prepare_compute_workspace(ROOT, source, os.environ.get("WORKBENCH_PG_DSN"))
        checks["workspace_isolated_from_shared_db"] = target != source
        checks["workspace_path_contract"] = target == compute_database_path(ROOT)
        checks["latest_pg_publication_materialized"] = bool(refresh.get("publication_id") and refresh.get("trade_date"))
        checks["shared_database_not_target"] = "market_research.duckdb" not in str(target)
        checks["data_generation_triggered"] = False
    except Exception as exc:  # pragma: no cover - external database evidence
        checks["error"] = f"{type(exc).__name__}:{exc}"
        failures.append("compute_workspace_prepare")
    for name in ("workspace_isolated_from_shared_db", "workspace_path_contract", "latest_pg_publication_materialized", "shared_database_not_target"):
        if checks.get(name) is not True:
            failures.append(name)
    payload = {
        "contract_version": "DAILY_COMPUTE_WORKSPACE_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_database": str(source),
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "checks": checks,
        "failures": sorted(set(failures)),
        "status": "PASS" if not failures else "BLOCKED",
        "acceptance": "DEGRADED_PASS_DAILY_COMPUTE_WORKSPACE" if not failures else "BLOCKED",
        "next_stage": "manual_daily_generation_observation" if not failures else "repair_compute_workspace",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(REPORT.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(temporary, REPORT)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
