"""Compare Sep-24 official raw bars with accepted V4-02 raw coordinates."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
import json
import os
from pathlib import Path
import sys
import zipfile

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tdx.day_reader import DAY_RECORD_LENGTH, decode_record  # noqa: E402


def main() -> None:
    capture = json.loads((ROOT / "reports/v4_02/V4_02_GO_FORWARD_TDX_CAPTURE_ATTEMPT_R2.json").read_text(encoding="utf-8"))
    daily_path = ROOT / "data/v4/artifact_store/v4_02/V4_02_ADJUSTED_CANONICAL_DAILY_R7_20260927.parquet"
    rows = duckdb.connect().execute(
        "SELECT source_security_key, raw_open,raw_high,raw_low,raw_close,volume,amount "
        "FROM read_parquet(?) WHERE trade_date=20260924", [str(daily_path)]
    ).fetchall()
    accepted = {r[0]: r[1:] for r in rows}
    found = set()
    counts = Counter()
    examples = []
    with zipfile.ZipFile(ROOT / capture["package_path"]) as archive:
        for info in archive.infolist():
            name = info.filename.replace("\\", "/")
            if not name.lower().endswith(".day"):
                continue
            stem = Path(name).stem.lower()
            if len(stem) != 8 or stem[:2] not in ("sh", "sz"):
                continue
            key = f"{stem[:2].upper()}.{stem[2:]}"
            raw = archive.read(info)
            if len(raw) < DAY_RECORD_LENGTH or len(raw) % DAY_RECORD_LENGTH:
                continue
            for offset in range(len(raw) - DAY_RECORD_LENGTH, -1, -DAY_RECORD_LENGTH):
                date_int = int.from_bytes(raw[offset:offset+4], "little")
                if date_int < 20260924:
                    break
                if date_int != 20260924:
                    continue
                if key not in accepted:
                    counts["PACKAGE_ONLY"] += 1
                    break
                found.add(key)
                bar = decode_record(raw[offset:offset+DAY_RECORD_LENGTH])
                old = accepted[key]
                value = (bar.open, bar.high, bar.low, bar.close, bar.volume, bar.amount)
                price_match = all(abs(Decimal(str(value[i])) - old[i]) <= Decimal("0.005") for i in range(4))
                volume_match = int(value[4]) == int(old[4])
                amount_match = abs(float(value[5]) - float(old[5])) <= max(0.01, abs(float(old[5])) * 1e-6)
                if price_match and volume_match and amount_match:
                    counts["EXACT_OR_NORMALIZED_TOLERANCE_MATCH"] += 1
                else:
                    counts["MISMATCH"] += 1
                    if len(examples) < 10:
                        examples.append({"source_security_key": key, "package": value, "accepted": [str(x) for x in old]})
                break
    counts["ACCEPTED_ONLY"] = len(set(accepted) - found)
    status = "PASS" if counts["MISMATCH"] == 0 and counts["ACCEPTED_ONLY"] == 0 else "V4_02_GO_FORWARD_BLOCKED_RAW_OVERLAP_MISMATCH"
    out = {"contract_id": "V4_02_GO_FORWARD_RAW_OVERLAP_R2", "status": status,
           "target_overlap_date": "2026-09-24", "accepted_row_count": len(accepted),
           "counts": dict(counts), "mismatch_examples": examples,
           "package_sha256": capture["package_sha256"], "accepted_daily_path": daily_path.relative_to(ROOT).as_posix()}
    path = ROOT / "reports/v4_02/V4_02_GO_FORWARD_RAW_OVERLAP_R2.json"
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)
    print(status, dict(counts))


if __name__ == "__main__":
    main()
