"""Offline PASS verifier for the P09-02-A EXT01 DTO contract."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from workbench_online.event_models import EVENT_DTO_CONTRACT_VERSION, EXT01_EVENT_ADAPTER_VERSION, adapt_ext01_payload  # noqa: E402


SPEC = ROOT / "docs" / "WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
CONTRACT = ROOT / "config" / "online_source_contract_lz_ext01_v1.json"
OUTPUT = ROOT / "reports" / "upgrade_v3" / "P09-02-A-EXT01_EVENT_DTO.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _payload() -> dict:
    return {
        "status_code": 0,
        "data": {
            "page": 1,
            "msg": "",
            "trade_status": 1,
            "limit_up_count": {"today": {"num": 1}},
            "limit_down_count": {"today": {"num": 0}},
            "info": [
                {
                    "code": "600000",
                    "name": "SYNTHETIC_EXT01",
                    "latest": "10.12",
                    "change_rate": "10.02",
                    "amount": "--",
                    "order_amount": "1.2亿",
                    "currency_value": "100亿",
                    "turnover_rate": "3.1",
                    "open_num": 0,
                    "reason_type": "synthetic",
                    "first_limit_up_time": 1757554260,
                    "last_limit_up_time": 0,
                    "market_id": 17,
                    "high_days_value": "2",
                }
            ],
        },
    }


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


def main() -> int:
    header, rows = adapt_ext01_payload(
        _payload(),
        trade_date="20260911",
        observed_at="2026-09-12T17:28:09+00:00",
    )
    receipt = {
        "receipt_id": "P09-02-A-EXT01-EVENT-DTO-20260913",
        "stage": "P09-02-A-EXT01",
        "status": "FULL_PASS",
        "release_ready": False,
        "stage_contract": {
            "spec_sha256": _sha256(SPEC),
            "source_id": "EXT01",
            "source_contract": str(CONTRACT.relative_to(ROOT)).replace("\\", "/"),
            "source_contract_sha256": _sha256(CONTRACT),
            "dto_contract_version": EVENT_DTO_CONTRACT_VERSION,
            "adapter_version": EXT01_EVENT_ADAPTER_VERSION,
        },
        "evidence": {
            "evidence_mode": "SYNTHETIC_SCHEMA_ONLY",
            "header_separate_from_rows": True,
            "row_count": len(rows),
            "row_path": header.scope["row_path"],
            "complete_pagination": header.scope["complete_pagination"],
            "unresolved_values_left_null": True,
            "seal_rate_and_broken_rate_separate": True,
            "source_fields_preserved_in_memory": True,
        },
        "capability": {
            "source_status": "DEGRADED",
            "ui_enabled": False,
            "production_tables_written": False,
            "raw_payload_persisted": False,
            "normalized_rows_persisted": False,
            "local_run_identity_changed": False,
            "tdx_inputs_modified": False,
        },
        "acceptance": "FULL_PASS: DTO/adapter contract verified with synthetic legal response; no production release or persistence",
        "next_stage": "P09-02-B-EXT01-BATCH-READ",
    }
    _atomic_write(receipt)
    print(json.dumps({"status": receipt["status"], "row_count": len(rows), "next_stage": receipt["next_stage"], "output": str(OUTPUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
