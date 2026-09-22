"""Rehearse managed-root ArtifactCatalog registration and rollback."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_db.postgres_artifact_catalog import ArtifactCatalogError, PostgresArtifactCatalog  # noqa: E402
from workbench_db.postgres_repository import PostgresRepository  # noqa: E402


REPORT = ROOT / "runtime/postgres_migration/20260922/pg_operations_artifact_contract_rehearsal_report.json"


class RollbackProbe(Exception):
    pass


def main() -> int:
    checks: dict[str, object] = {}
    failures: list[str] = []
    runtime_dir = ROOT / "runtime/postgres_migration/20260922"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="artifact-catalog-probe-", dir=str(runtime_dir)) as directory:
            probe_dir = Path(directory)
            probe_file = probe_dir / "probe.json"
            probe_file.write_text('{"contract":"probe","version":1}\n', encoding="utf-8")
            relative = probe_file.relative_to(ROOT).as_posix()
            with PostgresRepository() as repository:
                catalog = PostgresArtifactCatalog(repository, root=ROOT, forbidden_roots=(Path("D:/new_tdx"),))
                try:
                    with repository.transaction():
                        registered = catalog.register_file(managed_root_id="PROJECT_ROOT", relative_path=relative, category="MANIFEST", artifact_contract="ARTIFACT_CATALOG_PROBE_V1", migration_class="RETAIN_EXTERNAL")
                        checks["registered"] = registered
                        checks["round_trip"] = catalog.get(str(registered["artifact_id"]))
                        raise RollbackProbe()
                except RollbackProbe:
                    checks["rollback_exception_caught"] = True
                checks["after_rollback"] = catalog.get(str(registered["artifact_id"]))
                if checks["after_rollback"] is not None:
                    failures.append("artifact_catalog_rollback")
                if (checks.get("round_trip") or {}).get("sha256") != (checks.get("registered") or {}).get("sha256"):  # type: ignore[union-attr]
                    failures.append("artifact_digest_round_trip")
                invalid = {}
                for value in ("../config/workbench.yaml", str(ROOT / "config/workbench.yaml"), "E:/outside.txt"):
                    try:
                        catalog.resolve_path("PROJECT_ROOT", value)
                    except ArtifactCatalogError as exc:
                        invalid[value] = str(exc)
                checks["invalid_path_rejections"] = invalid
                if len(invalid) != 3:
                    failures.append("artifact_path_guard")
    except Exception as exc:  # pragma: no cover - report the gate failure
        checks["error"] = f"{type(exc).__name__}:{exc}"
        failures.append("operations_artifact_boundary")

    report = {
        "contract_version": "PG_OPERATIONS_ARTIFACT_CONTRACT_REHEARSAL_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
        "acceptance": "DEGRADED_PASS_MANAGED_ROOT_ARTIFACT_ROLLBACK" if not failures else "BLOCKED",
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "next_stage": "cutover_adapter_injection" if not failures else "repair_operations_artifact_boundary",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(REPORT.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(temporary, REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
