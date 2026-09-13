"""Offline close-out verifier for the EXT01 P09-03 product slice."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
OUTPUT = ROOT / "reports" / "upgrade_v3" / "P09-03-EXT01-CLOSE-OUT.json"

RECEIPTS = {
    "P09-01-B-LZ-EXT01": ROOT / "reports/upgrade_v3/P09-01-B-LZ-EXT01_CURRENT_PROBE.json",
    "P09-02-A-EXT01": ROOT / "reports/upgrade_v3/P09-02-A-EXT01_EVENT_DTO.json",
    "P09-02-B-EXT01": ROOT / "reports/upgrade_v3/P09-02-B-EXT01_BATCH_READ.json",
    "P09-02-C-EXT01": ROOT / "reports/upgrade_v3/P09-02-C-EXT01_CLOSE_BATCH_STORE.json",
    "P09-02-D-EXT01": ROOT / "reports/upgrade_v3/P09-02-D-EXT01_CLOSE_BATCH_WRITER.json",
    "P09-03-EXT01": ROOT / "reports/upgrade_v3/P09-03-EXT01-LADDER-SLICE.json",
    "P09-03-EXT01-LADDER-EVIDENCE": ROOT / "reports/upgrade_v3/P09-03-EXT01-LADDER-EVIDENCE.json",
    "P09-03-EXT01-EVIDENCE-UI-REGRESSION": ROOT / "reports/upgrade_v3/P09-03-EXT01-EVIDENCE-UI-REGRESSION.json",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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
    loaded = {task_id: _load(path) for task_id, path in RECEIPTS.items()}
    engineering_pass = all(loaded[task_id].get("status") == "FULL_PASS" for task_id in RECEIPTS if task_id != "P09-01-B-LZ-EXT01")
    source_probe_degraded = loaded["P09-01-B-LZ-EXT01"].get("status") == "DEGRADED_PASS"
    receipt = {
        "receipt_id": "P09-03-EXT01-CLOSE-OUT-20260913",
        "stage": "P09-03-EXT01-CLOSE-OUT",
        "status": "DEGRADED_PASS" if engineering_pass and source_probe_degraded else "BLOCKED",
        "release_ready": False,
        "stage_contract": {
            "spec_sha256": _sha256(SPEC),
            "source_id": "EXT01",
            "scope_contract": "v3-events-ladder-v1.0 + v3-events-ladder-evidence-v1.0 + v3-events-evidence-ui-regression-v1.0",
            "close_out_contract": "v3-p09-ext01-slice-close-out-v1.0",
        },
        "evidence": {
            "child_receipts": {task_id: {"status": value["status"], "release_ready": value.get("release_ready", False)} for task_id, value in loaded.items()},
            "engineering_chain_full_pass": engineering_pass,
            "source_probe_degraded_pass": source_probe_degraded,
            "source_scope": "EXT01 LIMIT_POOL_UP only",
            "known_source_limits": [
                "single-page current probe; complete pagination not verified",
                "amount/seal_amount/float_market_cap/turnover and ret1 scale semantics remain unresolved",
                "source_as_of may be absent; observed_at is not a per-stock transaction time",
            ],
            "not_closed_in_this_slice": [
                "EXT02–EXT09 independent current probes and product pages",
                "market overview, topics, pools and hot-rank pages",
                "P09-04 live sector member quote ranking",
                "production activation/release readiness",
            ],
            "manual_browser_ui_regression": "recorded in V3_P09_03_EXT01_EVIDENCE_UI_REGRESSION.md",
        },
        "capability": {
            "slice_status": "DEGRADED_PASS",
            "source_status": "DEGRADED",
            "product_status": "PREVIEW_ONLY",
            "network_calls": 0,
            "production_database_written": False,
            "raw_payload_persisted": False,
            "local_run_identity_changed": False,
            "tdx_inputs_modified": False,
        },
        "acceptance": "DEGRADED_PASS: EXT01 ladder and evidence slice is independently usable as a bounded preview with explicit source limits; P09-wide missing datasets remain open",
        "next_stage": "P09-01-B-LZ-EXT02-CURRENT-PROBE",
    }
    _atomic_write(receipt)
    print(json.dumps({"status": receipt["status"], "source_status": receipt["capability"]["source_status"], "next_stage": receipt["next_stage"], "output": str(OUTPUT)}, ensure_ascii=False))
    return 0 if receipt["status"] in {"FULL_PASS", "DEGRADED_PASS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
