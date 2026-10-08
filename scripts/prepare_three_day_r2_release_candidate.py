"""Bind the independently checked sector-current candidate into an immutable R2 successor."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from scripts.fp01_evidence import write
from workbench_service.current_v4_context import digest
from workbench_service.joint_release import AUTHORITY, validate

OUT = ROOT / os.environ.get("R2_REPAIR_EVIDENCE_DIR", "docs/evidence/three_day_repair_r2_20261008")
DAILY = ROOT / os.environ.get("R2_DAILY_AUTHORITY_DIR", "data/v4/r2_daily_candidates/three_day_repair_r2_20261008")
SNAPSHOT_FILE = os.environ.get("R2_OWNER_SNAPSHOT_FILE", "R2_P0_2_OWNER_CONSUMER_SNAPSHOT.json")


def main():
    candidate_name = "R2_P0_4_RELEASE_CANDIDATE.json" if "R2_REPAIR_EVIDENCE_DIR" in os.environ else "R2_RELEASE_CANDIDATE.json"
    candidate_path = OUT / candidate_name
    if candidate_path.exists():
        raise RuntimeError("R2_RELEASE_CANDIDATE_FROZEN")
    live_bytes = (ROOT / AUTHORITY).read_bytes()
    candidate = json.loads(live_bytes)
    owner_snapshot = json.loads((OUT / SNAPSHOT_FILE).read_bytes())
    sector = json.loads((DAILY / "v4_sector_operational_authority_v1.json").read_bytes())
    if owner_snapshot["target"] != candidate["trade_date"] or sector["trade_date"] != candidate["trade_date"]:
        raise ValueError("SECTOR_TARGET_DATE_CONFLICT")
    snapshot = owner_snapshot["snapshot"]["pointer"]
    candidate["snapshot"] = snapshot
    candidate["daily_owner_authorities"]["sector"] = sector
    candidate["full_product_release"] = False
    candidate["trading"] = False
    candidate["app_version"] = __import__("subprocess").check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    candidate["r2_repair_scope"] = {
        "contract_id": "R2_SCOPED_SECTOR_CURRENT_FACTS_SUCCESSOR_V1",
        "eligible_domain": "sectors_current_facts",
        "target": candidate["trade_date"],
        "sector_authority_sha256": __import__("hashlib").sha256(
            (DAILY / "v4_sector_operational_authority_v1.json").read_bytes()
        ).hexdigest(),
        "independent_oracle": (OUT / ("R2_P0_4_SECTOR_INDEPENDENT_ORACLE.json" if "R2_REPAIR_EVIDENCE_DIR" in os.environ
                                       else "R2_P0_2_SECTOR_INDEPENDENT_ORACLE.json")).relative_to(ROOT).as_posix(),
        "unknown_capabilities": ["historical_membership", "Base", "Seed", "rotation_output_state", "stock_structure"],
        "activation_performed": False,
    }
    manifest = validate(ROOT, candidate)
    if manifest["context"]["accepted_trade_date"] != candidate["trade_date"]:
        raise ValueError("RELEASE_DATE_READBACK_MISMATCH")
    if (ROOT / AUTHORITY).read_bytes() != live_bytes:
        raise ValueError("LIVE_AUTHORITY_CHANGED_DURING_PREPARATION")
    write(candidate_path, candidate)
    write(OUT / "R2_RELEASE_CANDIDATE_PREPARATION.json", {
        "result": "VALIDATED_CANDIDATE_NOT_ACTIVATED",
        "target": candidate["trade_date"],
        "scope": candidate["r2_repair_scope"],
        "candidate": {"path": candidate_path.relative_to(ROOT).as_posix(), "sha256": digest(candidate_path.read_bytes())},
        "predecessor_authority_sha256": digest(live_bytes),
        "live_authority_unchanged": True,
        "manifest": {"path": candidate["snapshot"]["manifest"]["path"], "sha256": candidate["snapshot"]["manifest"]["sha256"]},
        "strict_pit": False,
        "activation": False,
        "next_stage": "P0_4_SCOPED_ACTIVATION_QA_AND_IAB_SMOKE",
    })
    print(json.dumps({"result": "VALIDATED_CANDIDATE_NOT_ACTIVATED", "date": candidate["trade_date"],
                      "scope": candidate["operational_release_scope"], "full_product_release": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
