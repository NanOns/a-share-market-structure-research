"""Prepare or explicitly append the exact current V4 Data Head to PG."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from workbench_db.v4_dm01_stage_state_pg_r1 import (  # noqa: E402
    append_stage,
    build_data_head_import_payload,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha256", required=True, help="independently verified raw Head SHA-256")
    parser.add_argument("--bytes", required=True, type=int, help="independently verified raw Head byte count")
    parser.add_argument("--write", action="store_true", help="append the validated import into explicitly configured V4 PG")
    args = parser.parse_args(argv)
    source_binding = {
        "path": "data/v4/V4_DATA_ACCEPTED_HEAD.json",
        "sha256": args.sha256,
        "bytes": args.bytes,
    }
    payload = build_data_head_import_payload(ROOT, source_binding)
    summary = {
        "contract_id": payload["contract_id"],
        "stage": "data_head",
        "trade_date": payload["trade_date"],
        "source_binding": payload["source_binding"],
        "status": "VALIDATED_READY_TO_APPEND" if args.write else "VALIDATED_DRY_RUN",
        "write_requested": args.write,
    }
    if args.write:
        summary["pg_append"] = append_stage(ROOT, payload["trade_date"], "data_head", payload)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
