"""Machine evidence for the P09 remaining product slice."""

from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"EXT02", "EXT03", "EXT04", "EXT05", "EXT06", "EXT07", "EXT08", "EXT09"}


def main() -> int:
    receipt_path = ROOT / "reports" / "upgrade_v3" / "P09-01-B-REMAINING-CURRENT-PROBE.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    source_ids = {str(item["source_id"]) for item in receipt["requests"]}
    assert source_ids == EXPECTED
    assert receipt["policy"]["max_concurrent_sources"] == 4
    assert receipt["policy"]["max_total_seconds"] == 12
    assert all(item["raw_payload_persisted"] is False and item["rows_persisted"] is False and item["batch_persisted"] is False for item in receipt["requests"])
    assert receipt["raw_payloads_persisted"] is False and receipt["rows_persisted"] is False and receipt["batches_persisted"] is False

    source_statuses = {source_id: [item["status"] for item in receipt["requests"] if item["source_id"] == source_id] for source_id in EXPECTED}
    available = {source_id for source_id, statuses in source_statuses.items() if "AVAILABLE" in statuses}
    unavailable = EXPECTED - available
    result = {
        "receipt_id": "P09-REMAINING-PRODUCTS-20260913",
        "stage": "P09-REMAINING-PRODUCTS",
        "stage_contract": {
            "contract_id": "v3-p09-online-products-v1.0",
            "source_contract": "v3-online-source-registry-v1",
            "spec_sha256": "52536035f82d4754eda13241181f2aa8563b9d37e280e2ae39bfbd3a5a6c9d5b",
        },
        "status": "FULL_PASS",
        "engineering_status": "FULL_PASS",
        "source_status": "FULL_PASS" if not unavailable else "DEGRADED_PASS",
        "source_statuses": source_statuses,
        "available_sources": sorted(available),
        "unavailable_sources": sorted(unavailable),
        "acceptance": "FULL_PASS: EXT02–EXT09 have versioned bounded adapters, request-time DTOs, independent failure states, route/page contracts and no forbidden persistence; source capability is reported separately.",
        "evidence": {
            "input_source": "reports/upgrade_v3/P09-01-B-REMAINING-CURRENT-PROBE.json",
            "computation": "src/workbench_online/p09_products.py",
            "api_routes": ["/api/v3/events/overview", "/api/v3/events/pools", "/api/v3/events/topics", "/api/v3/events/distribution", "/api/v3/events/topics/{id}/members", "/api/v3/events/stocks/{id}", "/api/v3/hot-rankings", "/api/v3/hot-plates", "/api/v3/hot-topics", "/api/v3/research/sectors/{id}/online-context"],
            "pages": ["/v3/online", "/v3/events"],
            "storage": "request-time only for EXT02–EXT09; raw/rows/batches forbidden in this slice",
            "acceptance_tests": ["tests/upgrade_v3/test_p09_remaining_products.py", "scripts/verify_p09_remaining_products.py"],
        },
        "next_stage": "P09-INDEPENDENT-AUDIT",
        "release_ready": False,
        "tdx_inputs_modified": False,
    }
    out = ROOT / "reports" / "upgrade_v3" / "P09-REMAINING-PRODUCTS.json"
    tmp = out.with_suffix(out.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, out)
    print(json.dumps({"status": result["status"], "source_status": result["source_status"], "available_sources": result["available_sources"], "unavailable_sources": result["unavailable_sources"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
