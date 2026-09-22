"""Rehearse the operations config history repository boundary."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_db.config_store import PostgresConfigVersionStore  # noqa: E402
from workbench_db.postgres_repository import PostgresRepository  # noqa: E402


DEFAULT_REPORT = ROOT / "runtime/postgres_migration/20260922/pg_config_store_rehearsal_report.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    revision = "rehearsal-" + uuid.uuid4().hex
    payload = json.dumps({"revision": revision, "config": {"query_page_size": 50}}, ensure_ascii=False, separators=(",", ":"))
    checks: dict[str, object] = {}
    failures: list[str] = []
    try:
        with PostgresRepository() as repository:
            store = PostgresConfigVersionStore(repository)
            store.put(revision, payload)
            rows = store.list()
            checks["roundtrip"] = any(item.get("revision") == revision for item in rows)
            checks["row_count_after_put"] = len(rows)
            with repository.connection.cursor() as cursor:  # type: ignore[union-attr]
                cursor.execute("delete from workbench.config_versions where config_revision=%s", (revision,))
            repository.connection.commit()  # type: ignore[union-attr]
            checks["cleanup"] = True
    except Exception as exc:  # pragma: no cover - report external service state
        checks["error"] = f"{type(exc).__name__}:{exc}"
        failures.append("postgres_config_store")
    if checks.get("roundtrip") is not True:
        failures.append("roundtrip")
    report = {
        "contract_version": "PG_CONFIG_STORE_REHEARSAL_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "failures": sorted(set(failures)),
        "status": "PASS" if not failures else "FAIL",
        "acceptance": "DEGRADED_PASS_CONFIG_STORE" if not failures else "BLOCKED",
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "next_stage": "migrate_remaining_operations_metadata_readers_and_writers" if not failures else "repair_config_store_boundary",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.report.with_suffix(args.report.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(args.report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
