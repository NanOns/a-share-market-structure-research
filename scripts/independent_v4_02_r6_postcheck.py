from __future__ import annotations

"""Independent row-level business comparison of the R6 runtime build to R4."""

import gzip
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R4 = ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R4_20260927.jsonl.gz"
R6 = ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R6_20260927.jsonl.gz"
R4_ACCEPTANCE = ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_ACCEPTANCE_R4_20260927.json"
R4_POSTCHECK = ROOT / "reports/v4_02/V4_02_FINAL_INDEPENDENT_POSTCHECK_R4.json"
BUILD = ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_BUILD_R6.json"
OUT = ROOT / "reports/v4_02/V4_02_FINAL_INDEPENDENT_POSTCHECK_R6.json"

BUSINESS_FIELDS = (
    "security_id", "trade_date", "special_price_phase", "limit_status", "reason", "reference_price",
    "limit_up_price", "limit_down_price", "rule_id", "reference_basis", "risk_status", "is_st",
)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def business(row: dict) -> dict:
    return {key: row.get(key) for key in BUSINESS_FIELDS}


def atomic_json(path: Path, value: dict) -> None:
    import os
    import tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main() -> int:
    r4_receipt = json.loads(R4_ACCEPTANCE.read_text(encoding="utf-8"))
    r4_post = json.loads(R4_POSTCHECK.read_text(encoding="utf-8"))
    build = json.loads(BUILD.read_text(encoding="utf-8"))
    if sha(R4) != r4_receipt["artifact"]["sha256"]:
        raise SystemExit("R6_POSTCHECK_R4_INPUT_HASH_MISMATCH")
    r4_phases, r6_phases = Counter(), Counter()
    r4_unknown, r6_unknown = Counter(), Counter()
    r4_status, r6_status = Counter(), Counter()
    left_digest, right_digest = hashlib.sha256(), hashlib.sha256()
    differences = []
    count = 0
    with gzip.open(R4, "rt", encoding="utf-8") as old, gzip.open(R6, "rt", encoding="utf-8") as new:
        for left, right in zip(old, new, strict=True):
            before, after = json.loads(left), json.loads(right)
            b4, b6 = business(before), business(after)
            if b4 != b6 and len(differences) < 100:
                differences.append({"row": count, "security_id": before.get("security_id"), "trade_date": before.get("trade_date"),
                                    "r4": {k: v for k, v in b4.items() if b4.get(k) != b6.get(k)},
                                    "r6": {k: v for k, v in b6.items() if b4.get(k) != b6.get(k)}})
            for row, digest, phases, unknown, statuses in ((before, left_digest, r4_phases, r4_unknown, r4_status),
                                                             (after, right_digest, r6_phases, r6_unknown, r6_status)):
                payload = json.dumps(business(row), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                digest.update(payload.encode("utf-8"))
                phases[str(row.get("special_price_phase") or "REGULAR")] += 1
                statuses[str(row.get("limit_status") or "UNKNOWN")] += 1
                if row.get("limit_status") == "UNKNOWN":
                    unknown[str(row.get("reason") or "<blank>")] += 1
            count += 1
    expected_phases = r4_post.get("counts", {}).get("special_price_phases", {})
    expected_unknown = r4_post.get("counts", {}).get("unknown_reasons", {})
    expected_status = r4_receipt.get("limit_status_counts", {})
    calls = build.get("apply_phase_event_call_counts", {})
    checks = {
        "row_count_unchanged": count == int(r4_receipt.get("row_count", -1)) == int(build.get("row_count", -2)),
        "business_payload_identical": not differences,
        "business_digest_identical": left_digest.hexdigest() == right_digest.hexdigest() == build.get("business_payload_sha256"),
        "phase_inventory_identical": dict(r4_phases) == dict(r6_phases) == expected_phases,
        "unknown_reason_inventory_identical": dict(r4_unknown) == dict(r6_unknown) == expected_unknown,
        "limit_status_inventory_identical": dict(r4_status) == dict(r6_status) == expected_status,
        "runtime_recomputed_event_windows": calls.get("DELISTING_FIRST_DAY") == 22 and calls.get("DELISTING_PERIOD") == 308,
        "runtime_applied_unknown_fail_closed": calls.get("UNKNOWN_SPECIAL_PHASE") == 31,
    }
    result = {
        "contract_id": "V4_02_FINAL_INDEPENDENT_POSTCHECK_R6", "version": "6.0.0",
        "status": "PASS" if all(checks.values()) else "BLOCKED", "checks": checks,
        "counts": {"price_rows": count, "special_price_phases": dict(r6_phases), "unknown_reasons": dict(r6_unknown),
                   "limit_status": dict(r6_status), "apply_phase_event_calls": calls, "business_difference_rows": len(differences)},
        "digests": {"r4_business_payload_sha256": left_digest.hexdigest(), "r6_business_payload_sha256": right_digest.hexdigest()},
        "differences_sample": differences[:20],
        "inputs": {"r4_price_sha256": sha(R4), "r6_price_sha256": sha(R6), "r6_build_receipt_sha256": sha(BUILD),
                   "r4_acceptance_sha256": sha(R4_ACCEPTANCE), "r4_postcheck_sha256": sha(R4_POSTCHECK)},
        "tdx_root_write_count": 0,
        "next_stage": "SEAL_R6_INTERNAL_FINAL_RECEIPT; KEEP_V4-03_BLOCKED_PENDING_EXTERNAL_ACCEPTANCE",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    atomic_json(OUT, result)
    print(json.dumps({"status": result["status"], "checks": checks, "business_difference_rows": len(differences)}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
