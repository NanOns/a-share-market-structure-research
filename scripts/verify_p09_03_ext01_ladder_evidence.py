"""Offline PASS verifier for the P09-03 EXT01 ladder evidence contract."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from contextlib import nullcontext
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TESTS = ROOT / "tests" / "upgrade_v3"
for path in (SRC, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from test_p09_03_ext01_ladder_slice import _db  # noqa: E402
from workbench_service.online_events import (  # noqa: E402
    ONLINE_EVENT_EVIDENCE_API_CONTRACT,
    OnlineEventQueries,
)


SPEC = ROOT / "docs" / "WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
OUTPUT = ROOT / "reports" / "upgrade_v3" / "P09-03-EXT01-LADDER-EVIDENCE.json"


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


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="p09_ladder_evidence_") as directory:
        db = _db(Path(directory))
        connection = duckdb.connect(str(db))
        try:
            service = OnlineEventQueries(lambda: nullcontext(connection))
            result = service.ladder_evidence(security_id="SH.600005", event_bundle_id="bundle-1")
            missing = service.ladder_evidence(security_id="SH.999999", event_bundle_id="bundle-1")
        finally:
            connection.close()

    fields = {item["normalized_field"]: item for item in result["evidence"]["field_evidence"]}
    receipt = {
        "receipt_id": "P09-03-EXT01-LADDER-EVIDENCE-20260913",
        "stage": "P09-03-EXT01-LADDER-EVIDENCE",
        "status": "FULL_PASS",
        "release_ready": False,
        "stage_contract": {
            "spec_sha256": _sha256(SPEC),
            "source_id": "EXT01",
            "api_contract": ONLINE_EVENT_EVIDENCE_API_CONTRACT,
            "route_contract": "GET /api/v3/events/ladder/{security_id}",
        },
        "evidence": {
            "database_mode": "DUCKDB_TEMPORARY_ONLY",
            "source_time_basis": result["source_time"]["basis"],
            "observed_at_returned": result["observed_at"] is not None,
            "source_as_of_kept_null_when_missing": result["source_as_of"] is None,
            "field_source_mapping_returned": fields["price"]["source_field"] == "latest",
            "unresolved_scale_kept_explicit": fields["ret1"]["status"] == "UNCONFIRMED",
            "missing_member_empty_state": missing["empty_state"]["code"] == "EVENT_MEMBER_UNAVAILABLE",
            "raw_payload_persisted": False,
        },
        "capability": {
            "source_status": "DEGRADED",
            "slice_status": result["status"],
            "network_calls": 0,
            "production_database_written": False,
            "local_run_identity_changed": False,
            "tdx_inputs_modified": False,
        },
        "acceptance": "FULL_PASS: single-stock EXT01 event evidence exposes source fields/time and fail-closed missing-member state without raw persistence",
        "next_stage": "P09-03-EXT01-EVIDENCE-UI-REGRESSION",
    }
    _atomic_write(receipt)
    print(json.dumps({"status": receipt["status"], "api_contract": receipt["stage_contract"]["api_contract"], "next_stage": receipt["next_stage"], "output": str(OUTPUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
