"""Summarize R3-to-R4 row, field, state, period-lineage and identity changes."""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import gzip
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/v4_05/V4_05_R4_R3_DIFF.json"


def sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> dict:
    before_path = ROOT / "reports/v4_05/staging/V4_05_R3_FULL_MARKET_CORE_PROFILE.jsonl.gz"
    after_path = ROOT / "reports/v4_05/staging/V4_05_R4_FULL_MARKET_CORE_PROFILE.jsonl.gz"
    counts = Counter()
    business_examples, state_examples, period_examples, reason_examples = [], [], [], []
    rows_before = rows_after = 0
    with gzip.open(before_path, "rt", encoding="utf-8") as before, gzip.open(after_path, "rt", encoding="utf-8") as after:
        while True:
            a_line, b_line = before.readline(), after.readline()
            if not a_line and not b_line:
                break
            if not a_line or not b_line:
                counts["row_count_mismatch"] += 1
                break
            a, b = json.loads(a_line), json.loads(b_line)
            rows_before += 1; rows_after += 1
            if a["security_id"] != b["security_id"]:
                counts["row_identity_mismatch"] += 1
                continue
            sid = a["security_id"]
            for name in sorted(set(a.get("derived_fields", {})) | set(b.get("derived_fields", {}))):
                old, new = a.get("derived_fields", {}).get(name, {}), b.get("derived_fields", {}).get(name, {})
                old_value = (old.get("value"), old.get("quality"), old.get("unknown_reason"))
                new_value = (new.get("value"), new.get("quality"), new.get("unknown_reason"))
                if old_value != new_value:
                    counts[f"business_field_changed:{name}"] += 1
                    if len(business_examples) < 40:
                        business_examples.append({"security_id": sid, "field": name, "r3": old_value, "r4": new_value})
            for name in sorted(set(a.get("states", {})) | set(b.get("states", {}))):
                old, new = a.get("states", {}).get(name, {}), b.get("states", {}).get(name, {})
                old_value = (old.get("value"), old.get("unknown_reason"))
                new_value = (new.get("value"), new.get("unknown_reason"))
                if old_value != new_value:
                    counts[f"state_changed:{name}"] += 1
                    if len(state_examples) < 40:
                        state_examples.append({"security_id": sid, "state": name, "r3": old_value, "r4": new_value})
            for name in ("weekly_trend_state", "monthly_trend_state"):
                old, new = a.get("period_lineage", {}).get(name, {}), b.get("period_lineage", {}).get(name, {})
                old_id = (old.get("period_view"), old.get("period_last_session"), old.get("window_identity"))
                new_id = (new.get("period_view"), new.get("period_last_session"), new.get("window_identity"))
                if old_id != new_id:
                    counts[f"period_lineage_changed:{name}"] += 1
                    if len(period_examples) < 40:
                        period_examples.append({"security_id": sid, "field": name, "r3": old_id, "r4": new_id})
            old_unknown = {name: item.get("unknown_reason") for name, item in a.get("states", {}).items() if item.get("unknown_reason")}
            new_unknown = {name: item.get("unknown_reason") for name, item in b.get("states", {}).items() if item.get("unknown_reason")}
            if old_unknown != new_unknown:
                counts["unknown_reason_map_changed"] += 1
                if len(reason_examples) < 40:
                    reason_examples.append({"security_id": sid, "r3": old_unknown, "r4": new_unknown})
            if a.get("source_digest") != b.get("source_digest"):
                counts["source_digest_changed"] += 1
            if a.get("output_digest") != b.get("output_digest"):
                counts["output_digest_changed"] += 1
    old_regime = json.loads((ROOT / "reports/v4_05/V4_05_R3_MARKET_REGIME.json").read_text(encoding="utf-8"))
    new_regime = json.loads((ROOT / "reports/v4_05/V4_05_R4_MARKET_REGIME.json").read_text(encoding="utf-8"))
    result = {"contract_id": "V4_05_R4_R3_DIFF_V1", "status": "PASS" if rows_before == rows_after == 5222 and not counts["row_identity_mismatch"] and not counts["row_count_mismatch"] else "FAIL",
              "row_set": {"r3_rows": rows_before, "r4_rows": rows_after, "same_ordered_id_set": rows_before == rows_after == 5222 and not counts["row_identity_mismatch"]},
              "profile_sha256": {"r3": sha(before_path), "r4": sha(after_path)},
              "change_counts": dict(counts), "business_field_changes": business_examples,
              "state_changes": state_examples, "period_lineage_changes": period_examples,
              "unknown_reason_changes": reason_examples,
              "market_identity_change": {"r3_market_snapshot_id": old_regime["axes"]["identity"]["market_snapshot_id"],
                                         "r4_market_snapshot_id": new_regime["identity"]["market_snapshot_id"],
                                         "r3_adjustment_basis_id": old_regime["axes"]["identity"]["adjustment_basis_id"],
                                         "r4_adjustment_basis_id": new_regime["identity"]["adjustment_basis_id"],
                                         "r3_trend_axis": old_regime["target_row"]["trend_axis"],
                                         "r4_trend_axis": new_regime["target_row"]["trend_axis"]},
              "expected_drift_explanation": ["source digests and output digests are rebound to R4 artifacts",
                                             "period lineage views use the accepted temporal enum even when QFQ inputs are blocked",
                                             "market trend is UNKNOWN because accepted V4-03 path continuation is not authorized"],
              "unexpected_business_value_drift": sum(value for key, value in counts.items() if key.startswith("business_field_changed:"))}
    temp = OUT.with_suffix(OUT.suffix + ".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, OUT)
    return result


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, sort_keys=True))
