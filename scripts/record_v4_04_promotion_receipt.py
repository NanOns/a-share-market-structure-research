"""Record the read-only V4-04 promotion validation result atomically."""

from __future__ import annotations

import json
import os
from pathlib import Path

from verify_v4_04_promotion import validate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/v4_joint/V4_04_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json"


def main() -> None:
    receipt = validate()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_bytes((json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    os.replace(tmp, OUT)
    print(json.dumps({"status": receipt["status"], "accepted_head_sha256": receipt["accepted_head"]["sha256"]}))


if __name__ == "__main__":
    main()
