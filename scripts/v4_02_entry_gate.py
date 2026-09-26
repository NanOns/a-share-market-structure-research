from __future__ import annotations

"""Verify the V4-02 entry authorization and emit an auditable gate receipt."""

import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config/v4_02_canonical_daily_pit_contract_v1.json"
MAPPING_PATH = ROOT / "config/v4_02_stage_acceptance_mapping_v1.json"
PHASE0_PATH = ROOT / "reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT.json"
V4_01_PATH = ROOT / "reports/v4_01/v4_01_final_stage_receipt_R6_2_20260926.json"
UNIVERSE_PATH = ROOT / "reports/v4_01/historical_evaluable_universe_receipt_R6_2_20260926.json"
SELECTION_RECEIPT_PATH = ROOT / "reports/v4_01/v4_01_source_selection_receipt_R4_20260925.json"
EXTERNAL_ACCEPTANCE_PATH = ROOT / "docs/evidence/V4_01_R6_2_FINAL_EXTERNAL_ACCEPTANCE_20260926.md"
EXTERNAL_ACCEPTANCE_SHA256 = "6c8d1c69fc7e473964995b4d00abd5150d9474e5065fca22d7ec112a0b4d3a5c"
CONTRACT_SHA256 = "744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def main() -> int:
    contract = read_json(CONTRACT_PATH)
    mapping = read_json(MAPPING_PATH)
    phase0 = read_json(PHASE0_PATH)
    v4_01 = read_json(V4_01_PATH)
    universe = read_json(UNIVERSE_PATH)
    selection_receipt = read_json(SELECTION_RECEIPT_PATH)
    external_text = EXTERNAL_ACCEPTANCE_PATH.read_text(encoding="utf-8")

    selection_manifest_path = ROOT / selection_receipt["source_selection_manifest"]
    checks = {
        "governing_contract_sha256": sha256(Path(r"D:\Users\lps\Desktop\A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925_codex修改版.md")) == CONTRACT_SHA256,
        "phase0_degraded_pass_and_same_contract": phase0.get("phase0_status") == "DEGRADED_PASS" and phase0.get("technical_contract_sha256") == CONTRACT_SHA256 and not phase0.get("remaining_phase0_blockers"),
        "external_acceptance_hash": sha256(EXTERNAL_ACCEPTANCE_PATH) == EXTERNAL_ACCEPTANCE_SHA256,
        "external_acceptance_authorizes_v4_02": all(token in external_text for token in ("V4-01 = PASS_WITH_BSE_SCOPE_DEGRADED", "V4-01 = EXTERNALLY_ACCEPTED", "V4-02 = AUTHORIZED_TO_START", "V4-03 = BLOCKED")),
        "v4_01_required_scope_pass": v4_01.get("required_scope_status") == "PASS" and v4_01.get("blockers") == [] and v4_01.get("status") == "PASS_WITH_BSE_SCOPE_DEGRADED",
        "v4_01_bse_degradation_explicit": v4_01.get("explicit_bse_scope_degradation_allowed") is True and v4_01.get("scope", {}).get("optional_bse") == "DEGRADED_BSE",
        "v4_01_required_boards_pass": all(v4_01.get("scope", {}).get("board_statistics", {}).get(board, {}).get("status") == "PASS" for board in mapping["acceptance"]["board_scope"]["required"]),
        "historical_universe_required_scope_pass": universe.get("status") == "PASS" and universe.get("required_scope", {}).get("identity_unresolved") == 0,
        "source_selection_manifest_hash_bound": sha256(selection_manifest_path) == selection_receipt.get("source_selection_manifest_sha256") and v4_01.get("evidence", {}).get("R4_source_selection", {}).get("sha256") == sha256(SELECTION_RECEIPT_PATH),
        "machine_contract_points_to_current_mapping": contract.get("version") == "2.0.0" and contract.get("stage_acceptance_mapping", {}).get("contract_id") == mapping.get("contract_id"),
        "no_generic_degraded_pass": contract.get("acceptance", {}).get("generic_degraded_pass_allowed") is False and mapping.get("entry", {}).get("generic_degraded_pass_allowed") is False,
    }
    status = "ENTRY_AUTHORIZED" if all(checks.values()) else "BLOCKED"
    report = {
        "contract_id": "V4_02_ENTRY_GATE_RECEIPT_V1",
        "version": "1.0.0",
        "stage": "V4-02",
        "stage_contract": "DA-MSR-V4.2.2-CODEX-REV2 §§3B.6/3C.1-3C.4/5.2-5.3/6A/10N/78; V4_CANONICAL_DAILY_PIT_PERIODS_V2; V4_02_STAGE_ACCEPTANCE_MAPPING_V1",
        "consulted_upgrade": contract["consulted_upgrade"],
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "evidence": {
            "contract_sha256": sha256(CONTRACT_PATH),
            "mapping_sha256": sha256(MAPPING_PATH),
            "phase0_receipt_sha256": sha256(PHASE0_PATH),
            "external_acceptance_sha256": sha256(EXTERNAL_ACCEPTANCE_PATH),
            "v4_01_final_receipt_sha256": sha256(V4_01_PATH),
            "v4_01_historical_universe_receipt_sha256": sha256(UNIVERSE_PATH),
            "v4_01_source_selection_receipt_sha256": sha256(SELECTION_RECEIPT_PATH),
            "canonical_source_selection_manifest_sha256": sha256(selection_manifest_path),
        },
        "execution_identity": {
            "input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "script_sha256": sha256(Path(__file__).resolve()),
        },
        "checks": checks,
        "entry_status": status,
        "v4_02_implementation_status": "OPEN",
        "v4_02_acceptance_status": "NOT_ACCEPTED",
        "stage_completion_authorized": False,
        "outputs_emitted": False,
        "degraded_scopes": ["BSE_OPTIONAL_ONLY"] if status == "ENTRY_AUTHORIZED" else [],
        "blocked_scopes": [] if status == "ENTRY_AUTHORIZED" else [key for key, passed in checks.items() if not passed],
        "open_acceptance_capabilities": mapping["current_disposition"]["known_open_capabilities"],
        "next_stage": mapping["current_disposition"]["next_stage"] if status == "ENTRY_AUTHORIZED" else "RESOLVE_V4_02_ENTRY_GATE_EVIDENCE",
        "tdx_root_read_count": 0,
        "tdx_root_write_count": 0,
        "scanner_or_factor_run_count": 0,
    }
    output = ROOT / "reports/v4_02/V4_02_ENTRY_GATE_20260926.json"
    atomic_json(output, report)
    print(json.dumps({"receipt": output.relative_to(ROOT).as_posix(), "entry_status": status, "checks_passed": sum(checks.values()), "checks_total": len(checks)}, ensure_ascii=False))
    return 0 if status == "ENTRY_AUTHORIZED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
