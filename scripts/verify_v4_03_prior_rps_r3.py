"""Publish a dedicated receipt for the prior-RPS part of the full independent replay."""

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/v4_03/V4_03_PRIOR_RPS_INDEPENDENT_POSTCHECK_R3.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    staging = ROOT / "reports/v4_03/staging/V4_03_PRIOR_RPS_STAGING_R3.json"
    receipt_path = ROOT / "reports/v4_03/V4_03_PRIOR_RPS_STAGING_RECEIPT_R3.json"
    full_path = ROOT / "reports/v4_03/V4_03_INDEPENDENT_POSTCHECK_R3.json"
    candidate_path = ROOT / "reports/v4_03/V4_03_FULL_SCOPE_CANDIDATE_RECEIPT_R3.json"
    prior = json.loads(staging.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    full = json.loads(full_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    good = (sha(staging) == receipt["artifact_sha256"] == full["prior_artifact_sha256"] == candidate["prior_rps_artifact_sha256"]
            and full["status"] == "PASS" and full["prior_artifact_mismatch_count"] == 0
            and candidate["prior_rps_origin"] == "V4_03_STAGE_OWNED_HISTORICAL_STAGING_R3"
            and len(prior["rows"]) == 3)
    output = {"contract_id": "V4_03_PRIOR_RPS_INDEPENDENT_POSTCHECK_R3", "status": "PASS" if good else "FAIL",
              "prior_artifact_sha256": sha(staging), "prior_rows": len(prior["rows"]),
              "prior_coordinates": [[row["trade_date"], row["field_id"]] for row in prior["rows"]],
              "independent_replay_receipt_sha256": sha(full_path),
              "prior_artifact_mismatch_count": full["prior_artifact_mismatch_count"],
              "delta_identity_mismatch_count": sum(value for key, value in full["identity_mismatch_count_by_field"].items() if key.startswith("rps") and "delta" in key),
              "value_quality_mismatch_count": sum(value for key, value in full["mismatch_count_by_field"].items() if key.startswith("rps") and "delta" in key),
              "governing_task": "docs/audits/V4_03_R3_EXTERNAL_BLOCKER_CLOSURE_TASK_20260928.md",
              "stage_acceptance": "NOT_GRANTED"}
    tmp = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    tmp.write_text(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, OUTPUT)
    if not good or output["delta_identity_mismatch_count"] or output["value_quality_mismatch_count"]:
        raise RuntimeError("prior RPS independent closure failed")
    print(json.dumps({"status": output["status"], "prior_rows": output["prior_rows"]}))


if __name__ == "__main__":
    main()
