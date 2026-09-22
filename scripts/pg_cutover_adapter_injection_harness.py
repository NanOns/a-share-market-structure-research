"""Exercise explicit backend injection and fail-closed 503 behavior."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_db.backend_provider import AdapterHttpGateway, BackendRepositoryProvider  # noqa: E402
from workbench_service.today_research_bundle import TodayResearchBundleReader  # noqa: E402


REPORT = ROOT / "runtime/postgres_migration/20260922/pg_cutover_adapter_injection_harness_report.json"
SNAPSHOT = ROOT / "runtime/postgres_migration/20260922/market_research.source.duckdb"


def main() -> int:
    failures: list[str] = []
    checks: dict[str, object] = {}
    duck = AdapterHttpGateway(BackendRepositoryProvider(backend="duckdb", duckdb_path=str(SNAPSHOT)))
    pg = AdapterHttpGateway(BackendRepositoryProvider(backend="postgresql"))
    duck_heads = duck.read(lambda repository: repository.publication_heads())
    pg_heads = pg.read(lambda repository: repository.publication_heads())
    checks["publication_heads"] = {
        "duckdb_status": duck_heads["status"],
        "postgres_status": pg_heads["status"],
        "same_body": duck_heads.get("body") == pg_heads.get("body"),
    }
    latest_id = str((pg_heads.get("body") or {}).get("latest_publication_id") or "")
    duck_meta = duck.read(lambda repository: {"names": repository.research_security_names(latest_id), "sectors": repository.sector_metadata(latest_id)})
    pg_meta = pg.read(lambda repository: {"names": repository.research_security_names(latest_id), "sectors": repository.sector_metadata(latest_id)})
    checks["metadata"] = {
        "duckdb_status": duck_meta["status"],
        "postgres_status": pg_meta["status"],
        "same_body": duck_meta.get("body") == pg_meta.get("body"),
        "stock_count": len((pg_meta.get("body") or {}).get("names", {})),
        "sector_count": len((pg_meta.get("body") or {}).get("sectors", [])),
    }
    duck_today = duck.read(lambda repository: TodayResearchBundleReader(ROOT, repository=repository).list(page=1, page_size=20))
    pg_today = pg.read(lambda repository: TodayResearchBundleReader(ROOT, repository=repository).list(page=1, page_size=20))
    checks["today_research"] = {
        "duckdb_status": duck_today["status"],
        "postgres_status": pg_today["status"],
        "same_context": duck_today.get("body", {}).get("context") == pg_today.get("body", {}).get("context"),
        "same_total": duck_today.get("body", {}).get("total") == pg_today.get("body", {}).get("total"),
    }
    bad = AdapterHttpGateway(BackendRepositoryProvider(backend="postgresql", postgres_dsn="host=127.0.0.1 port=1 dbname=market_research user=postgres connect_timeout=1"))
    unavailable = bad.read(lambda repository: repository.publication_heads())
    checks["postgres_failure"] = {"status": unavailable["status"], "code": unavailable.get("body", {}).get("code"), "fallback_used": "duckdb" in str(unavailable).lower()}
    checks_list = [checks["publication_heads"], checks["metadata"], checks["today_research"]]
    if any(item.get("duckdb_status") != 200 or item.get("postgres_status") != 200 or not item.get("same_body", item.get("same_context") and item.get("same_total")) for item in checks_list):
        failures.append("injected_read_projection")
    if unavailable["status"] != 503 or checks["postgres_failure"]["code"] != "POSTGRES_UNAVAILABLE" or checks["postgres_failure"]["fallback_used"]:  # type: ignore[index]
        failures.append("fail_closed_503")
    report = {
        "contract_version": "PG_CUTOVER_ADAPTER_INJECTION_HARNESS_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
        "acceptance": "DEGRADED_PASS_ISOLATED_ADAPTER_INJECTION_503" if not failures else "BLOCKED",
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "next_stage": "maintenance_window_cutover_preflight" if not failures else "repair_adapter_harness",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(REPORT.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(temporary, REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
