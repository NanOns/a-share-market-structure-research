"""Compare the backend-neutral WorkbenchReadRepository contract."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_db.read_repository import DuckDBReadRepository  # noqa: E402
from workbench_db.postgres_repository import PostgresRepository  # noqa: E402


REPORT = ROOT / "runtime/postgres_migration/20260922/workbench_read_contract_shadow_report.json"
SNAPSHOT = ROOT / "runtime/postgres_migration/20260922/market_research.source.duckdb"


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def main() -> int:
    checks: dict[str, object] = {}
    failures: list[str] = []
    with DuckDBReadRepository(SNAPSHOT) as duck:
        duck_heads = duck.publication_heads()
        publication_id = str(duck_heads.get("latest_publication_id") or "")
        duck_names = duck.research_security_names(publication_id)
        duck_sectors = duck.sector_metadata(publication_id)
        duck_edges = duck.relation_edges_for_publication(publication_id)
    with PostgresRepository() as pg:
        pg_heads = pg.publication_heads()
        pg_names = pg.research_security_names(publication_id)
        pg_sectors = pg.sector_metadata(publication_id)
        pg_edges = pg.relation_edges_for_publication(publication_id)
    checks["publication_heads"] = {
        "duckdb_count": len(duck_heads["items"]),
        "postgres_count": len(pg_heads["items"]),
        "match": canonical(duck_heads) == canonical(pg_heads),
    }
    checks["security_names"] = {"duckdb_count": len(duck_names), "postgres_count": len(pg_names), "digest_match": digest(duck_names) == digest(pg_names)}
    checks["sector_metadata"] = {"duckdb_count": len(duck_sectors), "postgres_count": len(pg_sectors), "digest_match": digest(duck_sectors) == digest(pg_sectors)}
    checks["relation_edges"] = {"duckdb_count": len(duck_edges), "postgres_count": len(pg_edges), "digest_match": digest(duck_edges) == digest(pg_edges)}
    for name, value in checks.items():
        if not all(bool(item) for key, item in value.items() if key.endswith("match") or key == "digest_match"):
            failures.append(name)
    report = {
        "contract_version": "WORKBENCH_READ_REPOSITORY_CONTRACT_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_snapshot": str(SNAPSHOT),
        "publication_id": publication_id,
        "checks": checks,
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "acceptance": "DEGRADED_PASS_READ_BOUNDARY_SHADOW" if not failures else "BLOCKED",
        "next_stage": "repository_write_boundary_design" if not failures else "repair_read_boundary",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(REPORT.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
