from __future__ import annotations

"""Bind immutable R3 components and the R4 price-phase closure evidence."""

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
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact(path: str, rows: int | None = None) -> dict:
    target = ROOT / path
    return {"path": path, "bytes": target.stat().st_size, "sha256": sha(target), "row_count": rows}


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(value, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main() -> int:
    r3 = json.loads((ROOT / "reports/v4_02/V4_02_FINAL_STAGING_MANIFEST_R3.json").read_text(encoding="utf-8"))
    r4price = json.loads((ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_ACCEPTANCE_R4_20260927.json").read_text(encoding="utf-8"))
    audit_path = ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R4.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    test_path = ROOT / "reports/v4_02/V4_02_FINAL_R4_TEST_RECEIPT.json"
    test = json.loads(test_path.read_text(encoding="utf-8"))
    alias_path = ROOT / "reports/v4_02/V4_01_CODE_CHANGE_ALIAS_AUDIT_R7.json"
    alias = json.loads(alias_path.read_text(encoding="utf-8"))
    components = dict(r3["components"])
    r3_price_component = r3["components"].get("PRICE_LIMIT_R3") or r3["components"].get("PRICE_LIMIT")
    if not r3_price_component:
        raise SystemExit("R3_PRICE_COMPONENT_MISSING_FROM_FROZEN_MANIFEST")
    components["PRICE_LIMIT_R3"] = artifact("data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R7_20260927.jsonl.gz", r4price["row_count"])
    components.update({
        "PRICE_LIMIT_R4": artifact("data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R4_20260927.jsonl.gz", r4price["row_count"]),
        "PRICE_LIMIT_ACCEPTANCE_R4": artifact("reports/v4_02/V4_02_PRICE_LIMIT_ACCEPTANCE_R4_20260927.json"),
        "SPECIAL_PRICE_PHASE_CONTRACT_V1": artifact("config/v4_02_special_price_phase_v1.json"),
        "SPECIAL_PRICE_PHASE_EVENTS_R4": artifact("reports/v4_02/V4_02_SPECIAL_PRICE_PHASE_EVENTS_R4.jsonl", r4price["special_phase_counts"].get("DELISTING_FIRST_DAY", 0)),
        "R4_OFFICIAL_SOURCE_CAPTURE_INDEX": artifact("reports/v4_02/V4_02_R4_OFFICIAL_SOURCE_CAPTURE_INDEX.json"),
        "R4_RANGE_EXCEPTION_AUDIT": artifact(str(audit_path.relative_to(ROOT)).replace("\\", "/")),
        "R4_TEST_RECEIPT": artifact(str(test_path.relative_to(ROOT)).replace("\\", "/")),
        "R3_INDEPENDENT_POSTCHECK_FREEZE": artifact("reports/v4_02/V4_02_FINAL_INDEPENDENT_POSTCHECK_R3.json"),
        "R4_CAPTURE_SCRIPT": artifact("scripts/capture_v4_02_r4_official_sources.py"),
        "R4_PRICE_OVERLAY_SCRIPT": artifact("scripts/build_v4_02_price_limits_r4_overlay.py"),
    })
    blockers = []
    if audit.get("status") != "CLOSED" or audit.get("scope", {}).get("undispositioned_engineering_exceptions") != 0:
        blockers.append("R4_RANGE_EXCEPTION_DISPOSITION_GATE_OPEN")
    if test.get("result") != "PASS" or test.get("failed") != 0 or test.get("skipped") != 0:
        blockers.append("R4_SPECIAL_PHASE_TESTS_NOT_PASS")
    if alias.get("scan", {}).get("unresolved_required_scope_code_change_identities") != 0:
        blockers.append("R7_ALIAS_AUDIT_OPEN")
    manifest = {
        "contract_id": "V4_02_WHOLE_STAGE_STAGING_MANIFEST_R4", "version": "4.0.0",
        "status": "STAGING_CANDIDATE_READY" if not blockers else "BLOCKED",
        "stage": "V4-02", "stage_contract": "PRICE_LIMIT_RULE_R4 + SPECIAL_PRICE_PHASE_V1; R3 freezes retained",
        "governing_upgrade_contract": {"contract_id": "DA-MSR-V4.2.2-CODEX-REV2", "path": "D:/Users/lps/Desktop/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925_codex修改版.md", "sha256": "744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd"},
        "source_cutoff": "2026-09-24", "required_boards": ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"],
        "optional_degraded_boards": ["BSE"], "bse_in_required_outputs": False,
        "components": components,
        "acceptance": {"r3_previous_close_chain_frozen": True,
            "r7_alias_board_audit_unresolved": alias["scan"]["unresolved_required_scope_code_change_identities"],
            "r4_price_unknown": r4price["limit_status_counts"].get("UNKNOWN", 0),
            "r4_range_exception_rows": audit["scope"]["r3_current_exception_rows"],
            "r4_undispositioned_engineering_exceptions": audit["scope"]["undispositioned_engineering_exceptions"],
            "r4_fail_closed_dispositioned": audit["scope"]["r3_fail_closed_dispositioned"],
            "r4_special_phase_counts": r4price["special_phase_counts"], "test_result": test["result"]},
        "blockers": blockers,
        "frozen_r3_evidence": {"manifest_sha256": r3.get("sha256"), "r3_price_artifact_sha256": r3_price_component["sha256"],
                               "r3_independent_postcheck_sha256": components["R3_INDEPENDENT_POSTCHECK_FREEZE"]["sha256"]},
        "scanner_factor_trading_runs": 0,
        "next_stage": "INDEPENDENT_R4_POSTCHECK; IF PASS SEAL R4 AND SET V4-03 PENDING_EXTERNAL_ACCEPTANCE",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    out = ROOT / "reports/v4_02/V4_02_FINAL_STAGING_MANIFEST_R4.json"
    atomic_json(out, manifest)
    manifest["sha256"] = sha(out)
    print(json.dumps({"status": manifest["status"], "blockers": blockers, "components": len(components), "manifest_sha256": manifest["sha256"]}, ensure_ascii=False))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
