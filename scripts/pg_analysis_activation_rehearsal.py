"""Rehearse AnalysisActivationService on the PostgreSQL repository boundary."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from workbench_db.analysis_activation_repository import PostgresAnalysisActivationRepository  # noqa: E402
from workbench_db.postgres_history_job_repository import PostgresHistoryJobRepository  # noqa: E402
from workbench_db.postgres_repository import PostgresRepository  # noqa: E402
from workbench_service.analysis_activation import AnalysisActivationService  # noqa: E402
from workbench_service.source_freezer import atomic_write_manifest, build_source_manifest  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "runtime/postgres_migration/20260922/pg_analysis_activation_rehearsal_report.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=None)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("WORKBENCH_PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    token = uuid4().hex[:12]
    checks: dict[str, object] = {}
    failures: list[str] = []
    job_id = f"job-activation-pg-probe-{token}"
    publication_id: str | None = None
    new_publication_id: str | None = None
    snapshot_id: str | None = None
    manifest_path: Path | None = None
    input_path = ROOT / "runtime/postgres_migration/20260922" / f"activation_probe_input_{token}.txt"
    try:
        with PostgresRepository(dsn) as base:
            with base.connection.cursor() as cur:  # type: ignore[union-attr]
                cur.execute("select publication_id,cast(trade_date as text) from workbench.publications where status='SUCCESS' order by trade_date desc,revision desc limit 1")
                publication_id, cutoff = cur.fetchone()
                publication_id = str(publication_id)
                cutoff = str(cutoff)
                cur.execute("select publication_id from workbench.publication_heads where trade_date=%s", (cutoff,))
                expected_head_id = str(cur.fetchone()[0])
                cur.execute("select slice_id,domain,cast(trade_date as text) from workbench.analysis_slices where cast(trade_date as text)<=%s order by trade_date desc,slice_id limit 1", (cutoff,))
                slice_id, domain, slice_date = cur.fetchone()
                slice_id, domain, slice_date = str(slice_id), str(domain), str(slice_date)

            input_path.parent.mkdir(parents=True, exist_ok=True)
            input_path.write_text(f"activation-probe-{token}\n", encoding="utf-8")
            import hashlib
            manifest = build_source_manifest(
                publication_id=publication_id,
                cutoff_date=cutoff,
                source_revision_id=1,
                source_identity_sha256="current-economic-model",
                source_snapshot_manifest_sha256="s" * 64,
                source_bundle_id=f"activation-probe-bundle-{token}",
                observed_at=datetime.now(timezone.utc).isoformat(),
                window_plan={"output_start": cutoff, "output_end": cutoff, "read_start": cutoff, "read_end": cutoff, "output_days": 1, "required_history": 1},
                inputs=[{"path": input_path.relative_to(ROOT).as_posix(), "kind": "file", "role": "probe", "sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(), "observed_at": datetime.now(timezone.utc).isoformat(), "effective_date": cutoff, "date_scope": {"as_of": cutoff}}],
            )
            manifest_path = ROOT / "reports/upgrade_m7" / f"source_manifest_{cutoff.replace('-', '')}_activation_probe_{token}.json"
            atomic_write_manifest(manifest_path, manifest)

            request = {"base_publication_id": publication_id, "basis": "RECONSTRUCTED", "output_days": 1, "domains": [domain], "membership_snapshot_id": None, "contract_bundle_id": f"activation-probe-{token}", "source_manifest_path": manifest_path.relative_to(ROOT).as_posix(), "source_manifest_sha256": manifest["manifest_sha256"], "slice_ids": [slice_id]}
            payload = {"contract": "history-job-state-v1.0", "job_kind": "HISTORY_ANALYSIS", "request_identity": token, "request": request, "planned_domains": [domain], "completed_slice_ids": [slice_id]}
            jobs = PostgresHistoryJobRepository(base)
            with jobs.transaction():
                jobs.upsert_job(job_id=job_id, job_key=f"activation-probe-{token}", status="SUCCESS", payload=payload)
                jobs.upsert_attempt(job_id=job_id, attempt=1, status="SUCCESS", payload={"attempt": 1})
                jobs.append_event(job_id=job_id, attempt=1, status="SUCCESS")

            service = AnalysisActivationService(ROOT, repository=PostgresAnalysisActivationRepository(dsn))
            prepared = service.prepare(job_id)
            snapshot_id = prepared["snapshot_id"]
            checks["prepare"] = prepared["status"] == "PREPARED" and prepared["binding_domain"] == "LOCAL_RECONSTRUCTED"
            activated = service.activate(job_id, expected_head_id=expected_head_id, idempotency_key=f"activate-{token}")
            new_publication_id = activated["publication_id"]
            checks["activate"] = activated["status"] == "SUCCESS" and activated["analysis_snapshot_id"] == snapshot_id
            replay = service.activate(job_id, expected_head_id=expected_head_id, idempotency_key=f"activate-{token}")
            checks["idempotent_activate"] = replay.get("reused") is True and replay.get("publication_id") == new_publication_id
            with base.connection.cursor() as cur:  # type: ignore[union-attr]
                cur.execute("select status from workbench.analysis_snapshots where snapshot_id=%s", (snapshot_id,))
                checks["snapshot_success"] = cur.fetchone()[0] == "SUCCESS"
                cur.execute("select snapshot_id from workbench.publication_analysis_snapshots where publication_id=%s and domain=%s", (new_publication_id, "LOCAL_RECONSTRUCTED"))
                checks["snapshot_binding"] = cur.fetchone()[0] == snapshot_id
                cur.execute("select publication_id from workbench.publication_heads where trade_date=%s", (cutoff,))
                checks["head_advanced"] = cur.fetchone()[0] == new_publication_id

            # Restore the original head and remove all probe rows, including
            # cloned daily rows and immutable snapshot metadata.
            with base.transaction():
                with base.connection.cursor() as cur:  # type: ignore[union-attr]
                    cur.execute("update workbench.publication_heads set publication_id=%s where trade_date=%s", (expected_head_id, cutoff))
                    cur.execute("delete from workbench.publication_analysis_snapshots where publication_id=%s", (new_publication_id,))
                    cur.execute("delete from workbench.relation_publication_bindings where publication_id=%s", (new_publication_id,))
                    cur.execute("delete from workbench.publication_memberships where publication_id=%s", (new_publication_id,))
                    cur.execute("delete from workbench.publication_artifacts where publication_id=%s", (new_publication_id,))
                    for table in ("stock_daily", "sector_daily", "candidate_daily", "market_daily", "structure_details", "queue_memberships", "unified_board", "queue_rankings"):
                        cur.execute(f"delete from workbench.{table} where publication_id=%s", (new_publication_id,))
                    cur.execute("delete from workbench.publications where publication_id=%s", (new_publication_id,))
                    cur.execute("delete from workbench.analysis_snapshot_entries where snapshot_id=%s", (snapshot_id,))
                    cur.execute("delete from workbench.analysis_snapshots where snapshot_id=%s", (snapshot_id,))
                    cur.execute("delete from workbench.job_events where job_id=%s", (job_id,))
                    cur.execute("delete from workbench.job_attempts where job_id=%s", (job_id,))
                    cur.execute("delete from workbench.jobs where job_id=%s", (job_id,))
            checks["cleanup"] = True
    except Exception as exc:  # pragma: no cover - external database state
        checks["error"] = f"{type(exc).__name__}:{exc}"
        failures.append("pg_analysis_activation")
    finally:
        if manifest_path:
            manifest_path.unlink(missing_ok=True)
        input_path.unlink(missing_ok=True)
        if input_path.parent.exists() and not any(input_path.parent.iterdir()):
            shutil.rmtree(input_path.parent, ignore_errors=True)
    for key in ("prepare", "activate", "idempotent_activate", "snapshot_success", "snapshot_binding", "head_advanced", "cleanup"):
        if checks.get(key) is not True:
            failures.append(key)
    report = {"contract_version": "PG_ANALYSIS_ACTIVATION_V1", "generated_at_utc": datetime.now(timezone.utc).isoformat(), "checks": checks, "failures": sorted(set(failures)), "online_switch_performed": False, "data_generation_triggered": False, "acceptance": "DEGRADED_PASS_PG_ANALYSIS_ACTIVATION" if not failures else "BLOCKED", "next_stage": "wire_analysis_activation_factory_after_maintenance_cutover" if not failures else "repair_pg_analysis_activation"}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.report.with_suffix(args.report.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(temporary, args.report)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
