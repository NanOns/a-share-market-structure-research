"""Bounded current P09 metadata probe; persists no source payload or row."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_online.p09_products import P09OnlineProducts  # noqa: E402
from workbench_online.p09_products import _url  # noqa: E402
from workbench_online.base import OnlineFetchPolicy, bounded_get  # noqa: E402


def main() -> int:
    requests = [
        ("EXT02", {"date": "2026-09-11"}),
        ("EXT03", {"date": "2026-09-11"}),
        ("EXT04", {"date": "2026-09-11"}),
        ("EXT05", {"pool_name": "limit_up", "date": "2026-09-11"}),
        ("EXT07", {"type": "hour", "list_type": "normal"}),
        ("EXT08", {"type": "concept"}),
        ("EXT09", {"page": 1, "page_size": 30}),
    ]
    started = time.monotonic()
    responses = P09OnlineProducts().batch(requests)
    entries = []
    for (source, params), response in zip(requests, responses):
        entries.append({**response.receipt(), "request": params, "normalized_row_count": len(response.normalized) if isinstance(response.normalized, list) else None, "coverage_status": "UNKNOWN", "complete_pagination": False})
    pagination_checks = []
    for source, params, row_key in [
        ("EXT02", {"date": "2026-09-11", "page": 2, "limit": 50}, "info"),
        ("EXT09", {"page": 2, "page_size": 30}, "topic_list"),
    ]:
        try:
            remaining = 12.0 - (time.monotonic() - started)
            if remaining <= 0:
                raise TimeoutError("TOTAL_TIME_BUDGET_EXCEEDED")
            result = bounded_get(_url(source, params), OnlineFetchPolicy(timeout_seconds=min(3, remaining), max_response_bytes=2_000_000, retries=0))
            data = json.loads(result.body).get("data", {})
            rows = data.get(row_key) if isinstance(data, dict) else None
            pagination_checks.append({"source_id": source, "request": params, "http_status": result.status_code, "raw_sha256": result.raw_sha256, "row_count": len(rows) if isinstance(rows, list) else None, "requested_at": result.requested_at_utc, "received_at": result.received_at_utc, "raw_payload_persisted": False, "rows_persisted": False})
        except Exception as exc:
            pagination_checks.append({"source_id": source, "request": params, "error_code": type(exc).__name__, "row_count": None})
    payload = {
        "receipt_id": "P09-SOURCE-METADATA-PROBE-20260913",
        "contract_id": "v3-p09-source-metadata-probe-v1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requests": entries,
        "pagination_checks": pagination_checks,
        "raw_payloads_persisted": False,
        "rows_persisted": False,
        "batches_persisted": False,
        "next_stage": "P09-REAUDIT-CURRENT",
    }
    out = ROOT / "reports/upgrade_v3/P09-SOURCE-METADATA-PROBE-20260913.json"
    temp = out.with_suffix(out.suffix + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, out)
    print(json.dumps({"statuses": {entry["source_id"]: entry["status"] for entry in entries}, "receipt": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
