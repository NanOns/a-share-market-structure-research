"""Atomically publish the externally accepted V4-04 R4 head, before V4-05 work."""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASELINE_HEAD = "b7dc52d94d7bd81b8f55e1009d3eb271689f0943"
IMPLEMENTATION = "044dc637f90b35c6097bb800b1d4d755fdfb792c"
ARTIFACT_SHA = "b1ce4e4cb227f7cc25271005debfc9fc7bfaf61d39e20c96592921dd361e3b52"
HISTORY = {
    "R1": "afbea0ab09cbe28cfb5648495264ce346ccce22f5ca40b15b24112b6d8eb2e07",
    "R2": "89ed21dbdcc5abf377d2fda8299c444e7cd687fabb0eb5648ef5f12b8c4c0f12",
    "R3": "0c0fccd06fd2c2bad856b529d3ae2bcf64584f451e97961380997d72830b46b6",
}


def file_hash(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def binding(relative: str) -> dict:
    path = ROOT / relative
    return {"path": relative, "sha256": file_hash(path), "byte_count": path.stat().st_size}


def write_json(relative: str, payload: dict) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes((json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    os.replace(tmp, path)


def main() -> None:
    global_path = "data/v4/V4_STAGE_ACCEPTED_HEAD.json"
    accepted_path = "data/v4/V4_04_ACCEPTED_HEAD.json"
    if (ROOT / accepted_path).exists():
        raise ValueError("V4-04 Accepted Head already exists")
    if (ROOT / "reports/v4_05").exists():
        raise ValueError("V4-05 output existed before promotion")
    baseline = subprocess.check_output(["git", "show", f"{BASELINE_HEAD}:{global_path}"], cwd=ROOT)
    if (ROOT / global_path).read_bytes() != baseline:
        raise ValueError("global Accepted Head differs from reviewed baseline")
    current = json.loads(baseline)
    manifest_path = "reports/v4_04/V4_04_STAGE_CANDIDATE_MANIFEST_R4.json"
    artifact_path = "reports/v4_04/staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_R4.jsonl.gz"
    acceptance_path = "docs/evidence/V4_04_FINAL_EXTERNAL_ACCEPTANCE_R1_20260929.md"
    manifest = json.loads((ROOT / manifest_path).read_text(encoding="utf-8"))
    if (manifest["implementation_commit"] != IMPLEMENTATION or
            manifest["artifact"]["sha256"] != ARTIFACT_SHA or
            file_hash(ROOT / artifact_path) != ARTIFACT_SHA):
        raise ValueError("R4 candidate authority mismatch")
    acceptance = (ROOT / acceptance_path).read_text(encoding="utf-8")
    for required in ("V4_04_EXTERNAL_ACCEPTANCE_PASS_R4", "FULL_PASS_REQUIRED_SCOPE", "EXTERNALLY_ACCEPTED", ARTIFACT_SHA):
        if required not in acceptance:
            raise ValueError("external acceptance evidence incomplete")
    for revision, expected in HISTORY.items():
        name = f"reports/v4_04/staging/V4_04_FULL_MARKET_CORE_PROFILE_CANDIDATE_{revision}.jsonl.gz"
        if file_hash(ROOT / name) != expected:
            raise ValueError(f"historical {revision} artifact changed")
    contract_files = ("config/v4_04_field_registry_v2.json", "config/v4_04_output_schema_v2.json",
                      "config/v4_04_algorithm_contracts_v3.json", "config/v4_04_parameter_set_v1.json",
                      "config/v4_04_field_window_mapping_v1.json")
    capabilities = {name: "PASS" for name in (
        "STOCK_CORE_FULL_MARKET_PROFILE", "PURE_CORE_TREND", "PURE_CORE_POSITION",
        "PURE_CORE_MA_STRUCTURE", "PURE_CORE_RELATIVE", "PURE_CORE_COMPRESSION",
        "PURE_CORE_PARTICIPATION", "PURE_CORE_EXTENSION", "MARKET_REGIME_UI",
        "TECHNICAL_WINDOW_TRACEABILITY")}
    capabilities.update({name: "NOT_IN_V4_04_SCOPE" for name in (
        "TURNOVER_CONTEXT", "STOCK_BASE_SEED", "SECTOR_ROTATION_PRODUCTION",
        "STOCK_PREWATCH", "ADVANCED_STRUCTURE")})
    capabilities["DATA_FACTOR_REPLAY_PASS"] = "PENDING_V4_05"
    accepted = {
        "contract_id": "V4_04_ACCEPTED_HEAD_V1", "stage": "V4-04",
        "status": "FULL_PASS_REQUIRED_SCOPE", "external_acceptance": "EXTERNALLY_ACCEPTED",
        "accepted_at_date": "2026-09-29", "source_cutoff": "2026-09-24",
        "accepted_artifact": binding(artifact_path), "accepted_manifest": binding(manifest_path),
        "implementation_commit": IMPLEMENTATION, "evidence_seal_commit": BASELINE_HEAD,
        "external_acceptance_evidence": binding(acceptance_path),
        "contract_bindings": {name: binding(name) for name in contract_files},
        "r4_evidence_bindings": {name: binding(item["path"]) for name, item in manifest["evidence"].items()},
        "upstream_identities": {name: current["bindings"][name] for name in (
            "v4_01_accepted_head", "v4_02_accepted_head")} | {"v4_03_accepted_head": current["v4_03_binding"]},
        "capabilities": capabilities, "historical_candidate_hashes": HISTORY,
        "stage_record": {
            "stage_contract": "V4_04_FULL_MARKET_CORE_PROFILE_R4",
            "evidence": "R4 manifest, independent postcheck, machine semantic coverage, deterministic build and focused runtime gate",
            "acceptance_result": "FULL_PASS_REQUIRED_SCOPE / EXTERNALLY_ACCEPTED",
            "next_stage": "V4-05 Replay Gate A authorized after promotion validation"},
        "next_stage": "V4-05_REPLAY_GATE_A_AUTHORIZED_AFTER_PROMOTION_VALIDATION",
    }
    write_json(accepted_path, accepted)
    updated = dict(current)
    updated["v4_04_binding"] = binding(accepted_path)
    updated["v4_04_status"] = "FULL_PASS_REQUIRED_SCOPE"
    updated["v4_04_external_acceptance"] = "EXTERNALLY_ACCEPTED"
    updated["v4_05_entry"] = "AUTHORIZED_REPLAY_GATE_A"
    updated["v4_04_entry"] = "COMPLETED_EXTERNALLY_ACCEPTED"
    updated["accepted_stage_range"] = "V4_00_TO_V4_04_ACCEPTED; V4_05_NOT_ACCEPTED"
    updated["version"] = "2.1.0"
    write_json(global_path, updated)
    print(json.dumps({"accepted_head": binding(accepted_path), "global_head": binding(global_path)}))


if __name__ == "__main__":
    main()
