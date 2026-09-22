"""Rehearse PostgreSQL relation revisions, attributes and rollback."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from workbench_db.postgres_repository import PostgresRepository  # noqa: E402
from workbench_service.relation_repository import PostgresRelationRepository  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "runtime/postgres_migration/20260922/pg_relation_repository_rehearsal_report.json"


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--dsn", default=None); parser.add_argument("--report", type=Path, default=REPORT); args = parser.parse_args()
    dsn = args.dsn or os.environ.get("WORKBENCH_PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    token = uuid4().hex[:12]; scope = f"PROBE:RELATION-V3-{token}"; rollback_scope = f"PROBE:ROLLBACK-V3-{token}"
    edges = [{"sector_id": "SECTOR:PROBE", "security_id": "000001.SZ", "source_kind": "DIRECT"}, {"sector_id": "SECTOR:PROBE", "security_id": "000002.SZ", "source_kind": "DIRECT"}]
    attrs = [{"sector_id": "SECTOR:PROBE", "name": "Probe sector", "type": "LOCAL", "role": "CORE", "semantic_bucket": "TEST"}]
    checks: dict[str, object] = {}; failures: list[str] = []
    try:
        with PostgresRepository(dsn) as base:
            relation = PostgresRelationRepository(base)
            first = relation.record_observation(source_scope=scope, edges=edges, attributes=attrs, source_effective_date="2026-09-22", source_file_hashes={"probe": token}, observation_id=f"obs-probe-{token}")
            second = relation.record_observation(source_scope=scope, edges=edges, attributes=attrs, source_effective_date="2026-09-22", source_file_hashes={"probe": token}, observation_id=f"obs-probe-repeat-{token}")
            changed = relation.record_observation(source_scope=scope, edges=[*edges, {"sector_id": "SECTOR:PROBE", "security_id": "000003.SZ", "source_kind": "DIRECT"}], attributes=attrs, source_effective_date="2026-09-22", source_file_hashes={"probe": token, "changed": True}, observation_id=f"obs-probe-changed-{token}")
            checks["first_revision"] = first["status"] == "UPDATED" and first["revision_no"] == 1
            checks["unchanged_repeat"] = second["status"] == "UNCHANGED" and second["revision_no"] == 1
            checks["changed_revision"] = changed["status"] == "UPDATED" and changed["revision_no"] == 2 and len(changed["diff"]["added"]) == 1
            try:
                with base.transaction():
                    relation.record_observation(source_scope=rollback_scope, edges=edges, attributes=(), source_effective_date="2026-09-22", source_file_hashes={"probe": token}, observation_id=f"obs-rollback-{token}", manage_transaction=False)
                    raise RuntimeError("ROLLBACK_PROBE")
            except RuntimeError as exc:
                checks["rollback_error"] = str(exc)
            checks["rollback_clean"] = relation.current_revision(rollback_scope) is None
            with base.transaction() as connection:
                with connection.cursor() as cur:
                    for table in ("relation_edge_intervals", "relation_observations", "sector_attribute_revision_bindings", "sector_attribute_versions", "sector_attribute_revisions", "relation_revisions"):
                        cur.execute(f"delete from workbench.{table} where source_scope=%s", (scope,))
            checks["cleanup"] = relation.current_revision(scope) is None
    except Exception as exc:  # pragma: no cover
        checks["error"] = f"{type(exc).__name__}:{exc}"; failures.append("postgres_relation_repository")
    for key in ("first_revision", "unchanged_repeat", "changed_revision", "rollback_clean", "cleanup"):
        if checks.get(key) is not True: failures.append(key)
    report = {"contract_version": "PG_RELATION_REPOSITORY_V1", "generated_at_utc": datetime.now(timezone.utc).isoformat(), "checks": checks, "failures": sorted(set(failures)), "online_switch_performed": False, "data_generation_triggered": False, "acceptance": "DEGRADED_PASS_RELATION_REPOSITORY" if not failures else "BLOCKED", "next_stage": "inject_postgres_relation_repository_into_publisher_binding" if not failures else "repair_postgres_relation_repository"}
    args.report.parent.mkdir(parents=True, exist_ok=True); temporary = args.report.with_suffix(args.report.suffix + ".tmp"); temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8"); os.replace(temporary, args.report); print(json.dumps(report, ensure_ascii=False, indent=2, default=str)); return 0 if not failures else 2


if __name__ == "__main__": raise SystemExit(main())
