"""Promote the externally accepted R3 amendment without changing foundation heads."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = "a54154e5e25b149fd35a09935435dcaa40ad8b8b"
ACCEPTED = "data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json"
GLOBAL = "data/v4/V4_STAGE_ACCEPTED_HEAD.json"
SOURCE_SHA = "70b79898325ef6c67ea697f922d38fa3fd523e2ad62879b1b9fcb59fce52bf0c"
CANDIDATE_SHA = "7d87f5164c11f791ad24ad7c05139dca949f1c891523616ece907cd0f28fd8c8"
GBBQ_ID = "775d82c58b5b46ec1d21478f86ba8ef90302691982e68d5c4cfcd51fddda666e"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def bind(relative: str) -> dict:
    path = ROOT / relative
    return {"path": relative, "sha256": digest(path), "byte_count": path.stat().st_size}


def write(relative: str, value: dict) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def main() -> None:
    if (ROOT / ACCEPTED).exists():
        raise ValueError("amendment already promoted")
    for name in ("data/v4/V4_02_ACCEPTED_HEAD.json", "data/v4/V4_04_ACCEPTED_HEAD.json", GLOBAL):
        baseline = subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT)
        if (ROOT / name).read_bytes() != baseline:
            raise ValueError(f"baseline changed: {name}")
    manifest_path = "reports/v4_02/V4_02_GO_FORWARD_PIT_AMENDMENT_CANDIDATE_MANIFEST_R3.json"
    manifest = json.loads((ROOT / manifest_path).read_text(encoding="utf-8"))
    candidate = "reports/v4_02/staging/V4_02_GO_FORWARD_ADJUSTED_T0_CANDIDATE_R3.jsonl.gz"
    if manifest["r3_candidate_sha256"] != CANDIDATE_SHA or digest(ROOT / candidate) != CANDIDATE_SHA:
        raise ValueError("candidate mismatch")
    if manifest["official_tdx_sha256"] != SOURCE_SHA:
        raise ValueError("source mismatch")
    source = f"data/v4/source_snapshots/tdx/20260928/sha256-{SOURCE_SHA}/hsjday.zip"
    if digest(ROOT / source) != SOURCE_SHA:
        raise ValueError("official source bytes mismatch")
    gbbq = f"data/v4/source_snapshot_store/gbbq/sha256-{GBBQ_ID}/manifest.json"
    gbbq_manifest = json.loads((ROOT / gbbq).read_text(encoding="utf-8"))
    if gbbq_manifest["snapshot_id"] != f"sha256-{GBBQ_ID}":
        raise ValueError("GBBQ snapshot mismatch")
    acceptance = "docs/evidence/V4_02_GO_FORWARD_PIT_AMENDMENT_R3_FINAL_EXTERNAL_ACCEPTANCE_20260929.md"
    if "V4_02_GO_FORWARD_PIT_AMENDMENT_EXTERNAL_ACCEPTANCE_PASS_R3" not in (ROOT / acceptance).read_text(encoding="utf-8"):
        raise ValueError("external acceptance missing")
    evidence = {
        "external_acceptance": acceptance, "candidate_manifest": manifest_path,
        "independent_postcheck": "reports/v4_02/V4_02_GO_FORWARD_PIT_AMENDMENT_SEAL_POSTCHECK_R3.json",
        "publication_time": "reports/v4_02/V4_02_GO_FORWARD_PUBLICATION_TIME_R3.json",
        "remote_lfs_restore": "reports/v4_02/V4_02_GO_FORWARD_REMOTE_LFS_RESTORE_R3.json",
        "runtime_tests": "reports/v4_02/V4_02_GO_FORWARD_R3_TEST_RECEIPT.json",
        "r2_r3_diff": "reports/v4_02/V4_02_GO_FORWARD_R2_R3_DIFF_R3.json",
        "gbbq_snapshot": gbbq, "official_tdx_package": source,
    }
    head = {
        "contract_id": "V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD_V1",
        "stage": "V4-02-GO-FORWARD-PIT-AMENDMENT", "status": "FULL_PASS_GO_FORWARD_SCOPE",
        "external_acceptance": "EXTERNALLY_ACCEPTED", "external_acceptance_decision": "V4_02_GO_FORWARD_PIT_AMENDMENT_EXTERNAL_ACCEPTANCE_PASS_R3",
        "first_accepted_target_trade_date": "2026-09-28", "publication_mode": "DELAYED_FORMAL_PUBLICATION",
        "knowledge_lineage": "PIT_OBSERVED_AFTER_FORMAL_PUBLICATION",
        "historical_as_recorded_adjusted_price": "BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE",
        "official_tdx_package_sha256": SOURCE_SHA, "candidate_path": candidate,
        "candidate_sha256": CANDIDATE_SHA, "logical_digest": manifest["r3_logical_digest"],
        "accepted_candidate": bind(candidate), "evidence_bindings": {key: bind(path) for key, path in evidence.items()},
        "foundation_bindings": {name: bind(name) for name in ("data/v4/V4_02_ACCEPTED_HEAD.json", "data/v4/V4_04_ACCEPTED_HEAD.json")},
        "stage_record": {"stage_contract": "V4_02_GO_FORWARD_PIT_AMENDMENT_R3", "evidence": "R3 manifest, source, external acceptance and independent checks", "acceptance_result": "FULL_PASS_GO_FORWARD_SCOPE / EXTERNALLY_ACCEPTED", "next_stage": "V4-05 Replay Gate A R2 after promotion validation"},
    }
    write(ACCEPTED, head)
    global_head = json.loads((ROOT / GLOBAL).read_text(encoding="utf-8"))
    global_head.update({"v4_02_go_forward_pit_binding": bind(ACCEPTED), "v4_02_go_forward_pit_status": "FULL_PASS_GO_FORWARD_SCOPE", "v4_02_go_forward_pit_external_acceptance": "EXTERNALLY_ACCEPTED", "v4_02_go_forward_first_target": "2026-09-28", "historical_as_recorded_adjusted_price": "BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE", "v4_05_entry": "AUTHORIZED_REPLAY_GATE_A_R2", "version": "2.2.0"})
    write(GLOBAL, global_head)


if __name__ == "__main__":
    main()
