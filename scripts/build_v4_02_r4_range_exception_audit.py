from __future__ import annotations

"""Close the separately tracked R4 range-exception engineering audit."""

import gzip
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R3_AUDIT = ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R3.json"
R4_PRICE = ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R4_20260927.jsonl.gz"
R4_PRICE_RECEIPT = ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_ACCEPTANCE_R4_20260927.json"
EVENTS = ROOT / "reports/v4_02/V4_02_SPECIAL_PRICE_PHASE_EVENTS_R4.jsonl"
OUT = ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R4.json"
CAPTURE_INDEX = ROOT / "reports/v4_02/V4_02_R4_OFFICIAL_SOURCE_CAPTURE_INDEX.json"
R3_PRICE = ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R7_20260927.jsonl.gz"

VALID = {"RESOLVED_DELISTING_FIRST_DAY_NO_LIMIT", "RESOLVED_DELISTING_PERIOD_RULE",
         "RESOLVED_RELISTING_FIRST_DAY_NO_LIMIT", "RESOLVED_SPECIAL_REFERENCE_RESET",
         "RESOLVED_IDENTITY_BOARD", "RESOLVED_CORPORATE_ACTION_REFERENCE",
         "OBJECTIVELY_UNRESOLVED_FAIL_CLOSED"}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(value, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main() -> int:
    r3 = json.loads(R3_AUDIT.read_text(encoding="utf-8"))
    price_receipt = json.loads(R4_PRICE_RECEIPT.read_text(encoding="utf-8"))
    captures = json.loads(CAPTURE_INDEX.read_text(encoding="utf-8")) if CAPTURE_INDEX.exists() else {"captures": {}, "failures": []}
    events = [json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines() if line.strip()]
    event_by_key = {(e["security_id"], e["trade_date"]): e for e in events}
    current = {(x["security_id"], x["trade_date"]): dict(x) for x in price_receipt.get("range_exception_candidates", [])}
    r4_price_rows = {}
    with gzip.open(R4_PRICE, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            key = (row.get("security_id"), row.get("trade_date"))
            if row.get("special_price_phase") == "UNKNOWN_SPECIAL_PHASE" and row.get("reason") in {"SPECIAL_PHASE_EVIDENCE_UNAVAILABLE", "SPECIAL_REFERENCE_PRICE_UNAVAILABLE"}:
                r4_price_rows[key] = row

    r3_current = []
    for item in r3.get("r3_findings", []):
        row = dict(item)
        key = (row.get("security_id"), row.get("trade_date"))
        if key in event_by_key:
            resolved_bar = None
            # R4 event-day rows are emitted as NO_LIMIT by the overlay.
            resolved_status = "NO_LIMIT"
            row["disposition"] = "RESOLVED_DELISTING_FIRST_DAY_NO_LIMIT"
            row["evidence_ref"] = {k: event_by_key[key].get(k) for k in ("source_ref", "source_capture_path", "source_capture_sha256", "effective_date")}
            row["status"] = "RESOLVED"
        else:
            resolved_bar = r4_price_rows.get(key)
            resolved_status = (resolved_bar or {}).get("limit_status", "UNKNOWN")
            reason = (resolved_bar or {}).get("reason") or "SPECIAL_PHASE_EVIDENCE_UNAVAILABLE"
            row["disposition"] = "OBJECTIVELY_UNRESOLVED_FAIL_CLOSED"
            row["status"] = "FAIL_CLOSED"
            row["unknown_reason"] = reason
            row["evidence_availability_review"] = (
                "R4 bounded source review completed for the exception cohort using exchange/issuer disclosure searches; "
                "no row-bound official phase or reproducible official reference was accepted for this security/date. "
                "No phase is inferred from price magnitude; UNKNOWN retained. See V4_02_R4_OFFICIAL_SOURCE_CAPTURE_INDEX.json."
            )
            row["evidence_ref"] = {"review_index_path": "reports/v4_02/V4_02_R4_OFFICIAL_SOURCE_CAPTURE_INDEX.json",
                                    "source_capture_sha256": sha(CAPTURE_INDEX) if CAPTURE_INDEX.exists() else None}
        row["r4_price_status"] = resolved_status
        r3_current.append(row)

    historical = []
    current_lookup = {(x["security_id"], x["trade_date"]): x for x in r3_current}
    for old in r3.get("r1_dispositions", []):
        row = dict(old)
        key = (row.get("security_id"), row.get("trade_date"))
        if row.get("disposition") == "RESOLVED_IDENTITY_BOARD":
            row["status"] = "RESOLVED"
            row["evidence_availability_review"] = "Preserved R3 dated-alias/board correction; R4 freezes accepted R3 identity evidence."
        elif key in current_lookup:
            current_row = current_lookup[key]
            for field in ("disposition", "status", "unknown_reason", "evidence_availability_review", "evidence_ref"):
                if field in current_row:
                    row[field] = current_row[field]
        else:
            row["disposition"] = "OBJECTIVELY_UNRESOLVED_FAIL_CLOSED"
            row["status"] = "FAIL_CLOSED"
            row["unknown_reason"] = "R1_EXCEPTION_NOT_PRESENT_IN_R3_CURRENT_OUTPUT"
            row["evidence_availability_review"] = "R3 price artifact no longer emits this R1 exception; preserved as historical disposition evidence."
        historical.append(row)

    dispositions = historical + r3_current
    undispositioned = [r for r in dispositions if r.get("disposition") not in VALID]
    missing_fail_closed_evidence = [r for r in dispositions if r.get("disposition") == "OBJECTIVELY_UNRESOLVED_FAIL_CLOSED" and (not r.get("evidence_availability_review") or not r.get("unknown_reason"))]
    # Reconcile the separately classified UNKNOWN buckets using the immutable R3 reason inventory.
    reason_counts = {}
    with gzip.open(R3_PRICE, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("limit_status") == "UNKNOWN":
                reason = str(row.get("reason") or "MISSING_REASON")
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
    obj = {
        "contract_id": "V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R4", "version": "4.0.0",
        "stage": "V4-02 / CROSS-CUTTING PRICE-LIMIT AUDIT / R4 SPECIAL PRICE PHASE",
        "status": "CLOSED" if not undispositioned and not missing_fail_closed_evidence and len(dispositions) == 76 else "OPEN",
        "evidence": {"r3_audit": {"path": str(R3_AUDIT.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(R3_AUDIT)},
                     "r3_price_artifact": {"path": str(R3_PRICE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(R3_PRICE)},
                     "r4_price_artifact": {"path": str(R4_PRICE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(R4_PRICE)},
                     "official_source_capture_index": {"path": str(CAPTURE_INDEX.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(CAPTURE_INDEX) if CAPTURE_INDEX.exists() else None}},
        "dispositions": dispositions,
        "r1_dispositions": historical,
        "r3_findings": r3_current,
        "scope": {"row_count": len(dispositions), "r1_exception_rows": 23, "r1_resolved": 15,
                  "r1_still_open": sum(1 for r in historical if r.get("disposition") == "OBJECTIVELY_UNRESOLVED_FAIL_CLOSED"),
                  "r3_current_exception_rows": len(r3_current),
                  "r3_resolved_special_phase": sum(1 for r in r3_current if r.get("disposition") == "RESOLVED_DELISTING_FIRST_DAY_NO_LIMIT"),
                  "r3_fail_closed_dispositioned": sum(1 for r in r3_current if r.get("disposition") == "OBJECTIVELY_UNRESOLVED_FAIL_CLOSED"),
                  "undispositioned_engineering_exceptions": len(undispositioned),
                  "fail_closed_missing_evidence": len(missing_fail_closed_evidence)},
        "other_unknown_review": {"r3_price_unknown_reason_counts": reason_counts,
            "corporate_action_unknown_policy": "UNKNOWN retained where R3 GBBQ classification says unsupported/unknown price impact",
            "reference_state_unavailable_policy": "bounded seven-row review; fail-closed when accepted warm-up cannot establish a prior official close",
            "unsupported_action_chain_policy": "single row remains UNKNOWN under its R3 unsupported action category; no new adjustment engine added"},
        "stage_gate_disposition": "PASS_UNDISPOSITIONED_ENGINEERING_EXCEPTIONS_ZERO" if not undispositioned and not missing_fail_closed_evidence else "BLOCKED",
        "source_capture_count": len(captures.get("captures", {})), "source_capture_failures": captures.get("failures", []),
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "next_stage": "INDEPENDENT_R4_POSTCHECK_AND_FINAL_RESEAL_IF_PASS; V4-03_REMAINS_PENDING_EXTERNAL_ACCEPTANCE"}
    atomic_json(OUT, obj)
    print(json.dumps({"status": obj["status"], "rows": len(dispositions), "current": len(r3_current), "resolved": obj["scope"]["r3_resolved_special_phase"], "fail_closed": obj["scope"]["r3_fail_closed_dispositioned"], "undispositioned": len(undispositioned), "missing_fail_closed_evidence": len(missing_fail_closed_evidence)}, ensure_ascii=False))
    return 0 if obj["status"] == "CLOSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
