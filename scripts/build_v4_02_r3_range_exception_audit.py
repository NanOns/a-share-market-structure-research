from __future__ import annotations

"""Reconcile the R1 23 exceptions with R3 results and enumerate new findings."""

import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R1_PRICE = ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R6_2_20260926.jsonl.gz"
R3_PRICE = ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R7_20260927.jsonl.gz"
R1_AUDIT = ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R1.json"
OUT = ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R3.json"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rows(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def key(row: dict) -> tuple[str, str]:
    return str(row["security_id"]), str(row["trade_date"]).replace("-", "")


def main() -> int:
    current = {}
    current_exceptions = []
    for row in rows(R3_PRICE):
        current[key(row)] = row
        if row.get("reason") == "CLOSE_OUTSIDE_LIMIT_RANGE":
            current_exceptions.append(row)
    original_exceptions = [row for row in rows(R1_PRICE) if row.get("reason") == "CLOSE_OUTSIDE_LIMIT_RANGE"]
    prior_findings = []
    for row in original_exceptions:
        newer = current.get(key(row))
        if newer and newer.get("reason") != "CLOSE_OUTSIDE_LIMIT_RANGE":
            disposition = "RESOLVED_IDENTITY_BOARD" if row.get("board_scope") != newer.get("board_scope") else "RESOLVED_ALIAS_INTERVAL"
            state = "RESOLVED"
        else:
            disposition, state = None, "OPEN"
        prior_findings.append({"security_id": row["security_id"], "source_security_key_r1": row["source_security_key"],
                              "trade_date": row["trade_date"], "board_scope_r1": row["board_scope"],
                              "r1_reason": row["reason"], "r3_reason": newer.get("reason") if newer else "MISSING_R3_ROW",
                              "r3_source_security_key": newer.get("source_security_key") if newer else None,
                              "r3_board_scope": newer.get("board_scope") if newer else None,
                              "disposition": disposition, "status": state})
    prior_open_keys = {key(row) for row in original_exceptions
                       if current.get(key(row), {}).get("reason") == "CLOSE_OUTSIDE_LIMIT_RANGE"}
    new_findings = [{"security_id": row["security_id"], "source_security_key": row["source_security_key"],
                     "trade_date": row["trade_date"], "board_scope": row["board_scope"],
                     "risk_status": row.get("risk_status"), "reference_price": row.get("reference_price"),
                     "rule_id": row.get("rule_id"), "reason": row.get("reason"),
                     "present_in_r1_open_set": key(row) in prior_open_keys,
                     "disposition": None, "status": "OPEN_EVIDENCE_REQUIRED",
                     "evidence_availability_review": "NO_ROW_SPECIFIC_OFFICIAL_CAPTURE_BOUND_IN_R3_PACK"}
                    for row in current_exceptions]
    resolved = sum(item["status"] == "RESOLVED" for item in prior_findings)
    prior_open = sum(item["status"] == "OPEN" for item in prior_findings)
    doc = {
        "contract_id": "V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R3",
        "version": "3.0.0",
        "status": "OPEN" if prior_open or new_findings else "CLOSED",
        "stage": "V4-02 / CROSS-CUTTING AUDIT / SEPARATE FROM FINAL STAGE GATE",
        "scope": {"r1_exception_rows": len(original_exceptions), "r1_resolved": resolved,
                  "r1_still_open": prior_open, "r3_current_exception_rows": len(new_findings),
                  "r3_additional_exception_rows": len(new_findings) - len(prior_open_keys),
                  "row_count": len(prior_findings) + len(new_findings),
                  "r3_disposition_complete": False, "exception": "CLOSE_OUTSIDE_LIMIT_RANGE"},
        "evidence": {"r1_price_artifact": {"path": str(R1_PRICE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(R1_PRICE)},
                     "r3_price_artifact": {"path": str(R3_PRICE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(R3_PRICE)},
                     "r1_audit": {"path": str(R1_AUDIT.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(R1_AUDIT)}},
        "r1_dispositions": prior_findings,
        "r3_findings": new_findings,
        "stage_gate_disposition": "BLOCKED_PENDING_ROW_SPECIFIC_DISPOSITIONS; UNKNOWN_IS_NOT_ACCEPTED_AS_CLOSURE",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "next_stage": "COMPLETE_OFFICIAL_EVIDENCE_REVIEW_AND_DISPOSITION_FOR_EACH_R3_FINDING",
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": doc["status"], "r1_total": len(original_exceptions), "r1_resolved": resolved,
                      "r1_open": prior_open, "r3_current": len(new_findings),
                      "r3_additional": len(new_findings) - len(prior_open_keys), "path": str(OUT.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if doc["status"] == "CLOSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
