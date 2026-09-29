"""Independent evidence check for the go-forward PIT acceptance seal."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = "a54154e5e25b149fd35a09935435dcaa40ad8b8b"
OUT = ROOT / "reports/v4_joint/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    head_path = ROOT / "data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json"
    head = json.loads(head_path.read_text(encoding="utf-8"))
    global_head = json.loads((ROOT / "data/v4/V4_STAGE_ACCEPTED_HEAD.json").read_text(encoding="utf-8"))
    checks = {}
    for name in ("data/v4/V4_02_ACCEPTED_HEAD.json", "data/v4/V4_04_ACCEPTED_HEAD.json"):
        checks[f"baseline:{name}"] = (ROOT / name).read_bytes() == subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT)
    for key, binding in head["evidence_bindings"].items():
        path = ROOT / binding["path"]
        checks[f"binding:{key}"] = path.is_file() and path.stat().st_size == binding["byte_count"] and sha(path) == binding["sha256"]
    checks["candidate"] = sha(ROOT / head["candidate_path"]) == head["candidate_sha256"] == "7d87f5164c11f791ad24ad7c05139dca949f1c891523616ece907cd0f28fd8c8"
    checks["source_identity"] = head["evidence_bindings"]["official_tdx_package"]["sha256"] == head["official_tdx_package_sha256"]
    checks["external_decision"] = head["external_acceptance_decision"] in (ROOT / head["evidence_bindings"]["external_acceptance"]["path"]).read_text(encoding="utf-8")
    checks["global_binding"] = global_head["v4_02_go_forward_pit_binding"]["sha256"] == sha(head_path)
    checks["original_foundation_binding"] = global_head["bindings"]["v4_02_accepted_head"]["sha256"] == sha(ROOT / "data/v4/V4_02_ACCEPTED_HEAD.json")
    checks["v4_08_block"] = global_head["v4_08_sector_entry"] == "BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION"
    checks["entry"] = global_head["v4_05_entry"] == "AUTHORIZED_REPLAY_GATE_A_R2"
    checks["r2_not_started"] = not (ROOT / "reports/v4_05/V4_05_REPLAY_GATE_A_R2_RECEIPT.json").exists()
    checks["historical_block"] = head["historical_as_recorded_adjusted_price"] == "BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE"
    receipt = {"contract_id": "V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD_PROMOTION_VALIDATOR_R1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "accepted_head_sha256": sha(head_path), "global_head_sha256": sha(ROOT / "data/v4/V4_STAGE_ACCEPTED_HEAD.json"), "stage_record": {"stage_contract": "V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD_V1", "evidence": "Independently checked byte hashes, baseline heads, external decision, and downstream ordering", "acceptance_result": "PASS" if all(checks.values()) else "FAIL", "next_stage": "V4-05 Replay Gate A R2 only on PASS"}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, OUT)
    if not all(checks.values()):
        raise SystemExit(json.dumps({k: v for k, v in checks.items() if not v}))
    print(receipt["status"])


if __name__ == "__main__":
    main()
