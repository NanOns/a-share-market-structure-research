"""Rehearse explicit-offset persistence for M14 evidence and quotes."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_db.postgres_online_repository import PostgresOnlineRepository  # noqa: E402
from workbench_db.postgres_repository import PostgresRepository  # noqa: E402


DEFAULT_REPORT = ROOT / "runtime/postgres_migration/20260922/pg_online_time_contract_rehearsal_report.json"


class RollbackProbe(Exception):
    pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    marker = uuid.uuid4().hex
    evidence_id = "evidence-rehearsal-" + marker
    batch_id = "quote-batch-rehearsal-" + marker
    valid_evidence = {
        "evidence_id": evidence_id, "source_id": "REHEARSAL", "evidence_type": "NEWS", "security_id": "SH.600000",
        "event_time": "2026-09-22T01:00:00+00:00", "published_at": "2026-09-22T02:00:00+00:00", "first_seen_at": "2026-09-22T03:00:00+00:00",
        "text_hash": "hash-" + marker, "raw_ref": "raw/" + marker,
    }
    valid_quote = {
        "batch_id": batch_id, "security_id": "SH.600000", "quote_time": "2026-09-22T03:01:00+00:00",
        "quote_state": "OBSERVED", "source_code": "REHEARSAL:600000", "price_unit": "CNY", "amount_unit": "CNY", "volume_unit": "SHARES",
        "price": 10, "ret1": 0.01, "amount": 100, "volume": 10,
    }
    checks: dict[str, object] = {}
    failures: list[str] = []
    try:
        with PostgresRepository() as repository:
            writer = PostgresOnlineRepository(repository)
            try:
                writer.insert_evidence({**valid_evidence, "first_seen_at": "2026-09-22T03:00:00"})
            except ValueError as exc:
                checks["evidence_offset_required"] = str(exc) == "FIRST_SEEN_AT_OFFSET_REQUIRED"
            try:
                writer.insert_quote({**valid_quote, "quote_time": None})
            except ValueError as exc:
                checks["quote_time_required"] = str(exc) == "QUOTE_TIME_MISSING"
            try:
                with repository.transaction():
                    writer.insert_evidence(valid_evidence)
                    writer.insert_quote(valid_quote)
                    with repository.connection.cursor() as cur:  # type: ignore[union-attr]
                        cur.execute("select count(*) from workbench.online_evidence where evidence_id=%s", (evidence_id,))
                        checks["evidence_inserted_in_tx"] = int(cur.fetchone()[0]) == 1
                        cur.execute("select count(*) from workbench.online_quote_entries where batch_id=%s", (batch_id,))
                        checks["quote_inserted_in_tx"] = int(cur.fetchone()[0]) == 1
                    raise RollbackProbe()
            except RollbackProbe:
                checks["rollback_exception_caught"] = True
            with repository.connection.cursor() as cur:  # type: ignore[union-attr]
                cur.execute("select count(*) from workbench.online_evidence where evidence_id=%s", (evidence_id,))
                checks["evidence_rollback"] = int(cur.fetchone()[0]) == 0
                cur.execute("select count(*) from workbench.online_quote_entries where batch_id=%s", (batch_id,))
                checks["quote_rollback"] = int(cur.fetchone()[0]) == 0
    except Exception as exc:  # pragma: no cover - report external service state
        checks["error"] = f"{type(exc).__name__}:{exc}"
        failures.append("online_time_contract_connection")
    for key in ("evidence_offset_required", "quote_time_required", "evidence_inserted_in_tx", "quote_inserted_in_tx", "rollback_exception_caught", "evidence_rollback", "quote_rollback"):
        if checks.get(key) is not True:
            failures.append(key)
    report = {
        "contract_version": "PG_ONLINE_TIME_CONTRACT_REHEARSAL_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "failures": sorted(set(failures)),
        "status": "PASS" if not failures else "FAIL",
        "acceptance": "DEGRADED_PASS_ONLINE_TIME_CONTRACT" if not failures else "BLOCKED",
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "next_stage": "complete_remaining_application_adapter_migration" if not failures else "repair_online_time_contract",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.report.with_suffix(args.report.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(args.report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
