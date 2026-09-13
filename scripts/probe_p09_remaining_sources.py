"""Probe the remaining V3 P09 public sources without persisting source rows."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from workbench_online.base import OnlineFetchPolicy
from workbench_online.p09_products import EVENT_POOLS, HOT_RANK_MODES, P09OnlineProducts


def _last_weekday(value: date) -> date:
    while value.weekday() >= 5:
        value -= timedelta(days=1)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", dest="trade_date", default=None, help="YYYY-MM-DD or YYYYMMDD")
    args = parser.parse_args()
    raw_date = args.trade_date or _last_weekday(date.today()).isoformat()
    if len(raw_date) == 8 and raw_date.isdigit():
        raw_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
    day = date.fromisoformat(raw_date)
    date_text = day.isoformat()
    requests = [
        ("EXT02", {"date": date_text}),
        ("EXT03", {"date": date_text}),
        ("EXT04", {"date": date_text}),
        *(('EXT05', {"pool_name": name, "date": date_text}) for name in EVENT_POOLS),
        ("EXT06", {"date": date_text}),
        *(('EXT07', {"type": period, "list_type": kind}) for period, kind in HOT_RANK_MODES),
        ("EXT08", {"type": "concept"}),
        ("EXT08", {"type": "industry"}),
        ("EXT09", {"page": 1, "page_size": 30}),
    ]
    # A probe must test endpoints directly; it cannot depend on the receipt it creates.
    service = P09OnlineProducts(policy=OnlineFetchPolicy(timeout_seconds=3, max_response_bytes=2_000_000, retries=0), capabilities={source: "CURRENT_PROBE" for source, _ in requests})
    responses = service.batch(requests)
    items = []
    for (source_id, params), response in zip(requests, responses):
        receipt = response.receipt()
        receipt["request"] = params
        receipt["probe_date"] = date_text
        receipt["normalized_row_count"] = len(response.normalized) if isinstance(response.normalized, list) else None
        items.append(receipt)
    statuses = {source_id: [] for source_id in {item["source_id"] for item in items}}
    for item in items:
        statuses[item["source_id"]].append(item["status"])
    output = {
        "receipt_contract": "v3-p09-current-probe-receipt-v1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe_date": date_text,
        "policy": {"policy_id": "P09_ONLINE_BOUNDED_V1", "max_total_seconds": 12, "max_source_seconds": 8, "max_response_bytes": 2_000_000, "max_concurrent_sources": 4, "credentials_allowed": False},
        "source_summary": statuses,
        "requests": items,
        "raw_payloads_persisted": False,
        "rows_persisted": False,
        "batches_persisted": False,
        "tdx_inputs_modified": False,
    }
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "reports" / "upgrade_v3"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "P09-01-B-REMAINING-REPROBE-20260913.json"
    temp = target.with_suffix(target.suffix + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, target)
    print(json.dumps({"status": "FULL_PASS" if all(item["status"] == "AVAILABLE" for item in items) else "DEGRADED_PASS", "receipt": str(target), "source_summary": statuses}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
