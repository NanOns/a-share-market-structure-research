from __future__ import annotations

"""Record the DM-01 accepted-builder registry gate and its current evidence."""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.daily_data_head import write_json_atomic  # noqa: E402
from workbench_analysis.dm01_accepted_builder_registry import validate_registry  # noqa: E402


DEFAULT_AUDIT = Path(r"D:\Users\lps\Desktop\V4_DM01_POSTCLOSE_EXTERNAL_AUDIT_R2_20260928.md")
AUDIT_COPY = Path("docs/evidence/V4_DM01_POSTCLOSE_EXTERNAL_AUDIT_R2_20260928.md")
TDX_ROOT = Path("D:/new_tdx")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def latest_tdx_capture(target_date: str) -> tuple[dict | None, Path | None]:
    directory = ROOT / "data/v4/source_snapshots/tdx" / target_date.replace("-", "")
    receipts = sorted(directory.glob("capture-*/capture_receipt.json"),
                      key=lambda path: path.stat().st_mtime, reverse=True) if directory.is_dir() else []
    for path in receipts:
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if receipt.get("target_date") == target_date:
            return receipt, path
    return None, None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-date", default="2026-09-28")
    parser.add_argument("--audit-document", type=Path, default=DEFAULT_AUDIT)
    args = parser.parse_args()

    registry_path = ROOT / "config/v4_dm01_accepted_builder_registry_v1.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    validation = validate_registry(project_root=ROOT)
    audit_copy = ROOT / AUDIT_COPY
    audit_evidence = {"path": AUDIT_COPY.as_posix(), "available": audit_copy.is_file()}
    if audit_evidence["available"]:
        audit_evidence["sha256"] = sha256(audit_copy)
    audit_evidence["input_attachment_path"] = str(args.audit_document)
    audit_evidence["input_attachment_available"] = args.audit_document.is_file()
    if args.audit_document.is_file():
        audit_evidence["input_attachment_sha256"] = sha256(args.audit_document)
        audit_evidence["copy_matches_input_attachment"] = audit_evidence.get("sha256") == audit_evidence["input_attachment_sha256"]

    capture, capture_path = latest_tdx_capture(args.target_date)
    tdx_evidence = None
    if capture is not None and capture_path is not None:
        tdx_evidence = {
            "path": capture_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(capture_path),
            "status": capture.get("status"),
            "target_date": capture.get("target_date"),
            "update_date": capture.get("update_date"),
            "snapshot_id": capture.get("snapshot_id"),
            "observed_at": capture.get("observed_at"),
        }

    head_paths = {
        "data_accepted": ROOT / "data/v4/V4_DATA_ACCEPTED_HEAD.json",
        "stage_accepted": ROOT / "data/v4/V4_STAGE_ACCEPTED_HEAD.json",
        "dev_baseline": ROOT / "data/v4/V4_DEV_BASELINE_HEAD.json",
    }
    head_hashes = {name: sha256(path) for name, path in head_paths.items()}
    data_head = json.loads(head_paths["data_accepted"].read_text(encoding="utf-8"))
    stage_head = json.loads(head_paths["stage_accepted"].read_text(encoding="utf-8"))

    blockers = validation.get("runtime_api_blockers", [])
    result = {
        "contract_id": "V4_DM01_BUILDER_REGISTRY_STAGE_RECEIPT_V1",
        "version": "1.0.0",
        "status": validation.get("status"),
        "observed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "stage_contract": {
            "stage": "V4-DM-01",
            "registry_contract_id": registry.get("contract_id"),
            "registry_version": registry.get("version"),
            "registry_path": registry_path.relative_to(ROOT).as_posix(),
            "registry_sha256": sha256(registry_path),
            "latest_applicable_external_audit": audit_evidence,
            "algorithm_boundary": "DM-01 may select scope, resolve parent revisions, stage artifacts, write receipts, and publish atomically; component calculations remain pinned to accepted V4-01/V4-02 runtimes.",
            "v4_03_started": False,
        },
        "evidence": {
            "registry_validation": validation,
            "accepted_runtime_bindings": {
                capability: {
                    "owner_stage": item.get("owner_stage"),
                    "accepted_algorithm_contract": item.get("accepted_algorithm_contract"),
                    "accepted_runtime": item.get("accepted_runtime", []),
                    "runtime_api_assessment": item.get("runtime_api_assessment"),
                }
                for capability, item in registry.get("capabilities", {}).items()
            },
            "latest_official_tdx_capture": tdx_evidence,
            "accepted_parent_cutoff": data_head.get("accepted_trade_date"),
            "head_sha256": head_hashes,
            "stage_head_v4_01_binding": stage_head.get("bindings", {}).get("v4_01_r8_1", {}).get("sha256"),
            "known_stage_head_governance_debt": "KNOWN_STAGE_HEAD_GOVERNANCE_DEBT_V4_01_R8_3_NOT_REOPENED",
        },
        "acceptance_result": {
            "static_nine_capability_registry": validation.get("registry_integrity_status"),
            "bound_production_builder_count": validation.get("bound_builder_count", 0),
            "required_production_builder_count": validation.get("capability_count", 0),
            "real_incremental_builders": "BLOCKED_ACCEPTED_TARGET_DATE_ADAPTER_CALLABLES_UNAVAILABLE",
            "runtime_api_blockers": blockers,
            "independent_real_postcheck": "IMPLEMENTED_NOT_RUN_NO_REAL_COMPONENT_ARTIFACTS",
            "data_head_promoted": False,
            "stage_head_mutated": False,
            "dev_baseline_mutated": False,
            "tdx_root_write_count": 0,
        },
        "next_stage": "EXPOSE_OR_APPROVE_TARGET_DATE_CALLABLES_FOR_THE_PINNED_ACCEPTED_RUNTIMES_WITHOUT_ALGORITHM_CHANGE; BIND_ALL_NINE; THEN_RECHECK_OFFICIAL_TDX_PUBLICATION_AND_RUN_REAL_E2E",
    }
    output = ROOT / "reports/v4_dm01" / args.target_date / "builder_registry_stage_receipt_r1.json"
    output_sha = write_json_atomic(output, result, tdx_root=TDX_ROOT)
    print(json.dumps({"status": result["status"], "receipt_path": output.relative_to(ROOT).as_posix(),
                      "receipt_sha256": output_sha, "bound_builder_count": validation.get("bound_builder_count"),
                      "missing_builders": validation.get("missing_builders"),
                      "current_tdx_update_date": (tdx_evidence or {}).get("update_date")}, ensure_ascii=False))
    return 0 if validation.get("production_builders_ready") else 2


if __name__ == "__main__":
    raise SystemExit(main())
