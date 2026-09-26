from __future__ import annotations

"""Write the final V4-02 receipt and atomically promote its accepted head."""

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(value, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--pack-a", default="reports/v4_02/V4_02_DATA_PERIOD_MAINLINE_FINAL_ACCEPTANCE_R2.json")
    p.add_argument("--manifest", default="reports/v4_02/V4_02_FINAL_STAGING_MANIFEST_R1.json")
    p.add_argument("--postcheck", default="reports/v4_02/V4_02_FINAL_INDEPENDENT_POSTCHECK_R1.json")
    p.add_argument("--contract", default="config/v4_02_final_closure_contract_v1.json")
    p.add_argument("--out", default="reports/v4_02/V4_02_FINAL_RECEIPT_R1.json")
    p.add_argument("--head", default="data/v4/V4_02_ACCEPTED_HEAD.json")
    p.add_argument("--range-audit", default="reports/v4_02/V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R1.json")
    args = p.parse_args()
    pack_a_path, manifest_path, postcheck_path = ROOT / args.pack_a, ROOT / args.manifest, ROOT / args.postcheck
    contract_path, receipt_path, head_path = ROOT / args.contract, ROOT / args.out, ROOT / args.head
    range_audit_path = ROOT / args.range_audit
    pack_a = json.loads(pack_a_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    postcheck = json.loads(postcheck_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    range_audit = json.loads(range_audit_path.read_text(encoding="utf-8")) if range_audit_path.exists() else None
    previous_head_sha = sha(head_path) if head_path.exists() else None
    checks = {
        "pack_a_final_seal_pass": pack_a.get("status") == "PASS_WITH_HISTORICAL_NON_PIT_BOUNDARY",
        "whole_stage_manifest_prepared": manifest.get("status") == "STAGING_CANDIDATE_READY",
        "independent_final_postcheck_pass": postcheck.get("status") == "PASS",
        "four_required_boards_only": manifest.get("required_boards") == ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"] and manifest.get("bse_in_required_outputs") is False,
        "all_unknown_price_statuses_fail_closed": postcheck.get("checks", {}).get("all_unknown_values_have_explicit_reason") is True,
        "required_price_limit_samples_pass": postcheck.get("checks", {}).get("required_rule_samples_present") is True,
        "historical_pit_adjusted_not_claimed": pack_a.get("acceptance", {}).get("historical_pit_adjusted") == "NOT_AVAILABLE_PRE_PROJECT; NOT_CLAIMED",
        "go_forward_snapshot_enabled": pack_a.get("acceptance", {}).get("go_forward_pit_capture", "").startswith("ENABLED_FROM_FIRST_PUBLICATION"),
    }
    blockers = [name for name, value in checks.items() if not value]
    final_status = "PASS_WITH_BSE_SCOPE_DEGRADED" if not blockers else "BLOCKED"
    receipt = {
        "contract_id": "V4_02_FINAL_ACCEPTANCE_RECEIPT_R1",
        "version": "1.0.0",
        "stage": "V4-02 FINAL CLOSURE PACK",
        "status": final_status,
        "checks": checks,
        "blockers": blockers,
        "scope": {"start_date": "2023-07-04", "source_cutoff": "2026-09-24",
                  "required_boards": ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"],
                  "optional_degraded": ["BSE"]},
        "historical_adjusted_lineage": "DIAGNOSTIC_NON_PIT; HISTORICAL_PIT_NOT_CLAIMED",
        "go_forward_adjusted_permission": pack_a.get("acceptance", {}).get("go_forward_pit_capture"),
        "component_hashes": postcheck.get("component_hashes", {}),
        "separate_audits": ([{"path": args.range_audit, "sha256": sha(range_audit_path),
                              "status": range_audit.get("status"), "scope": range_audit.get("scope"),
                              "stage_gate_disposition": range_audit.get("stage_gate_disposition")}]
                            if range_audit else []),
        "staging_manifest": {"path": args.manifest, "sha256": sha(manifest_path)},
        "independent_postcheck": {"path": args.postcheck, "sha256": sha(postcheck_path), "status": postcheck.get("status")},
        "pack_a_final_receipt": {"path": args.pack_a, "sha256": sha(pack_a_path), "status": pack_a.get("status")},
        "atomic_publication": {"head_path": args.head, "previous_head_sha256": previous_head_sha,
                               "promoted": False if blockers else True},
        "v4_03_entry": "PENDING_EXTERNAL_ACCEPTANCE" if not blockers else "BLOCKED",
        "scanner_factor_trading_runs": 0,
        "contract": {"path": args.contract, "sha256": sha(contract_path), "id": contract.get("contract_id")},
        "execution_identity": {"seal_script_sha256": sha(Path(__file__).resolve())},
        "next_stage": "WAIT_FOR_EXTERNAL_ACCEPTANCE; DO_NOT_START_V4_03" if not blockers else "RESOLVE_FINAL_CLOSURE_BLOCKERS; DO_NOT_START_V4_03",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    atomic_json(receipt_path, receipt)
    if not blockers:
        head = {"contract_id": "V4_02_ACCEPTED_HEAD_V1", "stage": "V4-02",
                "status": final_status, "source_cutoff": "2026-09-24",
                "manifest_path": args.manifest, "manifest_sha256": sha(manifest_path),
                "final_receipt_path": args.out, "final_receipt_sha256": sha(receipt_path),
                "accepted_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "v4_03_entry": "PENDING_EXTERNAL_ACCEPTANCE"}
        atomic_json(head_path, head)
        written = json.loads(head_path.read_text(encoding="utf-8"))
        if written.get("final_receipt_sha256") != sha(receipt_path):
            raise RuntimeError("ATOMIC_ACCEPTED_HEAD_READBACK_FAILED")
    else:
        # The existing accepted head remains untouched on any failed candidate.
        if (sha(head_path) if head_path.exists() else None) != previous_head_sha:
            raise RuntimeError("FAILED_CANDIDATE_CHANGED_ACCEPTED_HEAD")
    print(json.dumps({"status": final_status, "blockers": blockers,
                      "head_promoted": not blockers, "receipt": args.out}, ensure_ascii=False))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
