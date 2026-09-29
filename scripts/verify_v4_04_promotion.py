"""Read-only independent validation of the V4-04 Accepted Head promotion."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "b7dc52d94d7bd81b8f55e1009d3eb271689f0943"
EXPECTED_ARTIFACT = "b1ce4e4cb227f7cc25271005debfc9fc7bfaf61d39e20c96592921dd361e3b52"
EXPECTED_MANIFEST_BLOB = "091515764ef4976cb8639297f12dc2cfafb7d3b6"


def file_hash(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_binding(item: dict) -> None:
    path = ROOT / item["path"]
    if (not path.is_file() or file_hash(path) != item["sha256"] or
            ("byte_count" in item and path.stat().st_size != item["byte_count"])):
        raise ValueError(f"binding identity mismatch: {item['path']}")


def baseline_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=ROOT)


def validate() -> dict:
    accepted_path = "data/v4/V4_04_ACCEPTED_HEAD.json"
    global_path = "data/v4/V4_STAGE_ACCEPTED_HEAD.json"
    accepted = json.loads((ROOT / accepted_path).read_text(encoding="utf-8"))
    global_head = json.loads((ROOT / global_path).read_text(encoding="utf-8"))
    prior = json.loads(baseline_bytes(global_path))
    manifest_item = accepted["accepted_manifest"]
    artifact_item = accepted["accepted_artifact"]
    verify_binding(manifest_item)
    verify_binding(artifact_item)
    if artifact_item["sha256"] != EXPECTED_ARTIFACT:
        raise ValueError("accepted artifact is not externally accepted R4")
    manifest_blob = subprocess.check_output(["git", "hash-object", str(ROOT / manifest_item["path"])], cwd=ROOT, text=True).strip()
    if manifest_blob != EXPECTED_MANIFEST_BLOB:
        raise ValueError("R4 manifest Git blob mismatch")
    manifest = json.loads((ROOT / manifest_item["path"]).read_text(encoding="utf-8"))
    if manifest["artifact"] != artifact_item or manifest["implementation_commit"] != accepted["implementation_commit"]:
        raise ValueError("manifest/accepted head identity mismatch")
    for item in manifest["evidence"].values():
        verify_binding(item)
    for item in accepted["r4_evidence_bindings"].values():
        verify_binding(item)
    for item in accepted["contract_bindings"].values():
        verify_binding(item)
    verify_binding(accepted["external_acceptance_evidence"])
    external = (ROOT / accepted["external_acceptance_evidence"]["path"]).read_text(encoding="utf-8")
    if not all(text in external for text in ("V4_04_EXTERNAL_ACCEPTANCE_PASS_R4", "FULL_PASS_REQUIRED_SCOPE",
                                             "EXTERNALLY_ACCEPTED", EXPECTED_ARTIFACT)):
        raise ValueError("external acceptance content mismatch")
    if (accepted["stage"] != "V4-04" or accepted["status"] != "FULL_PASS_REQUIRED_SCOPE" or
            accepted["external_acceptance"] != "EXTERNALLY_ACCEPTED" or
            accepted["source_cutoff"] != "2026-09-24"):
        raise ValueError("accepted stage status mismatch")
    for name in ("v4_01_accepted_head", "v4_02_accepted_head"):
        if global_head["bindings"][name] != prior["bindings"][name]:
            raise ValueError(f"upstream {name} binding changed")
    if global_head["bindings"] != prior["bindings"] or global_head["v4_03_binding"] != prior["v4_03_binding"]:
        raise ValueError("foundation accepted bindings changed")
    for item in accepted["upstream_identities"].values():
        verify_binding(item)
        if (ROOT / item["path"]).read_bytes() != baseline_bytes(item["path"]):
            raise ValueError(f"accepted upstream head changed: {item['path']}")
    verify_binding(global_head["v4_04_binding"])
    if global_head["v4_04_binding"]["path"] != accepted_path or list(global_head).count("v4_04_binding") != 1:
        raise ValueError("global V4-04 pointer is not unique")
    required = {name for name in accepted["capabilities"] if name.startswith("PURE_CORE_")} | {
        "STOCK_CORE_FULL_MARKET_PROFILE", "MARKET_REGIME_UI", "TECHNICAL_WINDOW_TRACEABILITY"}
    if any(accepted["capabilities"][name] != "PASS" for name in required):
        raise ValueError("required V4-04 capability not passed")
    if accepted["capabilities"]["DATA_FACTOR_REPLAY_PASS"] != "PENDING_V4_05":
        raise ValueError("V4-05 capability prematurely passed")
    if (global_head["v4_08_sector_entry"] != prior["v4_08_sector_entry"] or
            global_head["v4_05_entry"] != "AUTHORIZED_REPLAY_GATE_A"):
        raise ValueError("successor authorization or V4-08 block mismatch")
    if (ROOT / "reports/v4_05").exists():
        raise ValueError("V4-05 business output existed before promotion validation")
    for revision, expected in accepted["historical_candidate_hashes"].items():
        path = ROOT / f"reports/v4_04/staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_{revision}.jsonl.gz"
        if file_hash(path) != expected:
            raise ValueError(f"historical {revision} candidate changed")
    if file_hash(ROOT / prior["bindings"]["tdx_archive"]["path"]) != prior["bindings"]["tdx_archive"]["sha256"]:
        raise ValueError("accepted local TDX archive identity changed")
    allowed = {accepted_path, global_path,
               "docs/evidence/V4_04_FINAL_EXTERNAL_ACCEPTANCE_R1_20260929.md",
               "docs/evidence/V4_04_ACCEPTED_HEAD_PROMOTION_AND_V4_05_REPLAY_GATE_A_ENTRY_TASK_R1_20260929.md",
               "docs/audits/V4_04_PROMOTION_STAGE_RECORD_R1_20260929.md",
               "scripts/promote_v4_04_accepted_head.py", "scripts/verify_v4_04_promotion.py",
               "scripts/record_v4_04_promotion_receipt.py",
               "reports/v4_joint/V4_04_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json"}
    changed = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT, text=True).splitlines()
    paths = {line[3:].replace("\\", "/") for line in changed}
    if paths - allowed:
        raise ValueError(f"non-promotion file changed before validation: {sorted(paths - allowed)}")
    return {"contract_id": "V4_04_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1", "status": "PASS",
            "external_acceptance": "V4_04_EXTERNAL_ACCEPTANCE_PASS_R4",
            "accepted_head": {"path": accepted_path, "sha256": file_hash(ROOT / accepted_path)},
            "global_head": {"path": global_path, "sha256": file_hash(ROOT / global_path)},
            "r4_manifest_git_blob": manifest_blob,
            "r4_artifact_sha256": EXPECTED_ARTIFACT,
            "evidence_receipts_checked": len(manifest["evidence"]),
            "foundation_bindings_unchanged": True,
            "v4_08_sector_block_preserved": True,
            "v4_05_business_outputs_before_validation": 0,
            "tdx_archive_identity_unchanged": True,
            "historical_candidate_hashes": accepted["historical_candidate_hashes"]}


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
