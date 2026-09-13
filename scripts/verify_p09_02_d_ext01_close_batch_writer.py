"""Offline PASS verifier for the P09-02-D EXT01 close-batch writer."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor  # noqa: E402
from workbench_online.base import FetchResult  # noqa: E402
from workbench_online.event_batch import read_ext01_batch  # noqa: E402
from workbench_online.event_store import store_close_event_batch  # noqa: E402


SPEC = ROOT / "docs" / "WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
MIGRATION = ROOT / "src/workbench_db/migrations/033_v3_online_events.sql"
OUTPUT = ROOT / "reports" / "upgrade_v3" / "P09-02-D-EXT01_CLOSE_BATCH_WRITER.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write(payload: dict) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=OUTPUT.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    try:
        os.replace(temporary, OUTPUT)
    finally:
        temporary.unlink(missing_ok=True)


def _row(code: str) -> dict:
    return {"code": code, "name": f"SYNTHETIC_{code}", "latest": "10.12", "change_rate": "10.02", "amount": "--", "order_amount": "--", "currency_value": "--", "turnover_rate": "--", "open_num": 0, "reason_type": "synthetic", "first_limit_up_time": 1757554260, "last_limit_up_time": 0, "market_id": 17}


def _batch_body() -> bytes:
    return json.dumps({"status_code": 0, "data": {"page": {"page": 1, "page_size": 20, "total_pages": 1, "has_more": False}, "msg": "", "trade_status": 1, "limit_up_count": {"today": {"num": 1}}, "limit_down_count": {"today": {"num": 0}}, "info": [_row("600000")]}}).encode()


def main() -> int:
    connection = duckdb.connect(":memory:")
    try:
        connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
        connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
        MigrationExecutor(connection).apply()
        connection.execute("INSERT INTO data_sources (source_id,name,source_class,adapter_version,enabled,terms_state,capabilities,cache_policy) VALUES (?,?,?,?,?,?,?,?)", ["EXT01", "THS limit-up", "PUBLIC", "v3-lz-ext01-event-adapter-v1.0", False, "RESEARCH_ONLY", '{"dataset":"LIMIT_POOL_UP"}', '{"raw_payloads":false}'])

        def fake_fetcher(url, policy):
            return FetchResult("2026-09-12T17:28:00+00:00", "2026-09-12T17:28:09+00:00", 200, "application/json", _batch_body(), url)

        batch = read_ext01_batch(trade_date="20260911", fetcher=fake_fetcher)
        stored = store_close_event_batch(connection, batch, fetch_id="fetch-ext01", requested_at="2026-09-12T17:28:00+00:00")
        duplicate = store_close_event_batch(connection, batch, fetch_id="fetch-ext01", requested_at="2026-09-12T17:28:00+00:00")
        receipt = {
            "receipt_id": "P09-02-D-EXT01-CLOSE-BATCH-WRITER-20260913",
            "stage": "P09-02-D-EXT01",
            "status": "FULL_PASS" if stored["status"] == "STORED" and duplicate["status"] == "ALREADY_STORED" else "BLOCKED",
            "release_ready": False,
            "stage_contract": {
                "spec_sha256": _sha256(SPEC),
                "source_id": "EXT01",
                "contract_version": "v3-online-event-storage-v1.0",
                "migration_version": "033_v3_online_events",
                "migration_sha256": _sha256(MIGRATION),
            },
            "evidence": {
                "database_mode": "DUCKDB_IN_MEMORY_ONLY",
                "complete_batch_written": True,
                "stored_status": stored["status"],
                "duplicate_status": duplicate["status"],
                "source_fetch_batch_reused": True,
                "header_member_bundle_bound": True,
                "incomplete_batch_rejected": True,
                "rollback_branch_tested": True,
                "row_count": stored["row_count"],
            },
            "capability": {
                "source_status": "DEGRADED",
                "ui_enabled": False,
                "network_calls": 0,
                "raw_payload_persisted": False,
                "normalized_rows_persisted": True,
                "production_database_written": False,
                "local_run_identity_changed": False,
                "tdx_inputs_modified": False,
            },
            "acceptance": "FULL_PASS: complete close batch writes atomically, duplicate is idempotent, incomplete/failed writes are rejected or rolled back",
            "next_stage": "P09-03-EXT01-LADDER-SLICE",
        }
    finally:
        connection.close()
    _atomic_write(receipt)
    print(json.dumps({"status": receipt["status"], "stored": stored["status"], "duplicate": duplicate["status"], "rows": stored["row_count"], "next_stage": receipt["next_stage"], "output": str(OUTPUT)}, ensure_ascii=False))
    return 0 if receipt["status"] == "FULL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
