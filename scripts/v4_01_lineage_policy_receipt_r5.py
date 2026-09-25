from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    contract_path = ROOT / "config/v4_01_history_lineage_policy_v1.json"
    contract = json.loads(contract_path.read_text("utf-8"))
    valid = (contract.get("status") == "FROZEN"
             and contract.get("history_before_v4", {}).get("lineage") == "RECONSTRUCTED_CORRECTED"
             and contract.get("history_before_v4", {}).get("as_recorded_claim_allowed") is False
             and contract.get("history_from_v4_go_forward", {}).get("lineage") == "PIT_OBSERVED_AS_RECORDED_APPEND_ONLY"
             and "overwrite_prior_source_revision" in contract.get("prohibited", []))
    receipt = {"stage": "V4-01-LINEAGE-POLICY-R5", "contract_id": contract["contract_id"],
               "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
               "status": "PASS" if valid else "BLOCKED", "stage_completion_authorized": False,
               "meaning": contract.get("acceptance_meaning"),
               "verified_rules": {"pre_v4_history": contract.get("history_before_v4"),
                                  "v4_go_forward": contract.get("history_from_v4_go_forward"),
                                  "prohibited": contract.get("prohibited")},
               "input": {"path": "config/v4_01_history_lineage_policy_v1.json", "sha256": sha256(contract_path)},
               "execution_identity": {"input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                                      "script_sha256": sha256(Path(__file__))},
               "next_stage": "V4_01_FINAL_RECEIPT_R5"}
    _atomic_json(ROOT / "reports/v4_01/lineage_policy_receipt_R5_20260925.json", receipt)
    print(json.dumps({"status": receipt["status"], "receipt": "reports/v4_01/lineage_policy_receipt_R5_20260925.json"}))
    return 0 if valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
