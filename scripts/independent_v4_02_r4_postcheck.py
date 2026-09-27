from __future__ import annotations

"""Independent hash, identity, phase, and gate verification for V4-02 R4."""

import gzip
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "reports/v4_02/V4_02_FINAL_STAGING_MANIFEST_R4.json"
OUT = ROOT / "reports/v4_02/V4_02_FINAL_INDEPENDENT_POSTCHECK_R4.json"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    checks, findings = {}, []
    failures = []
    for name, component in manifest["components"].items():
        path = ROOT / component["path"]
        if not path.exists() or sha(path) != component["sha256"]:
            failures.append(name)
    checks["all_component_hashes_match"] = not failures
    if failures:
        findings.append("COMPONENT_HASH_MISMATCH:" + ",".join(failures))

    alias = load("reports/v4_02/V4_01_CODE_CHANGE_ALIAS_AUDIT_R7.json")
    identity = load("data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json")
    target = [r for r in identity["records"] if r.get("security_id") == "SEC-EDEDE35FE66896ACCA0AC85EEB2F133B"]
    by_alias = {r.get("source_security_key"): r for r in target}
    checks["r7_alias_and_board"] = (alias.get("scan", {}).get("unresolved_required_scope_code_change_identities") == 0
        and by_alias.get("SZ.300114", {}).get("symbol_effective_to") == "2025-02-16"
        and by_alias.get("SZ.302132", {}).get("symbol_effective_from") == "2025-02-17"
        and by_alias.get("SZ.302132", {}).get("board") == "CHINEXT")
    if not checks["r7_alias_and_board"]:
        findings.append("R7_ALIAS_OR_BOARD_FAILED")

    r3_post = load("reports/v4_02/V4_02_FINAL_INDEPENDENT_POSTCHECK_R3.json")
    checks["frozen_r3_previous_close_chain_pass"] = (r3_post.get("status") == "PASS"
        and r3_post.get("checks", {}).get("ordinary_suspension_adjacent_bar_reason_removed") is True)
    if not checks["frozen_r3_previous_close_chain_pass"]:
        findings.append("FROZEN_R3_PREVIOUS_CLOSE_CHECK_FAILED")

    events = [json.loads(line) for line in (ROOT / "reports/v4_02/V4_02_SPECIAL_PRICE_PHASE_EVENTS_R4.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    phase_starts = {(e["security_id"], e["trade_date"]): e for e in events}
    expected_days = Counter()
    phases, reasons, bse_rows, rows, blank_unknown = Counter(), Counter(), 0, 0, 0
    selected = {}
    keys_needed = {(r["security_id"], r["trade_date"]) for r in load("reports/v4_02/V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R4.json")["r3_findings"]}
    with gzip.open(ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R4_20260927.jsonl.gz", "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            rows += 1
            sid, day = str(row.get("security_id")), str(row.get("trade_date"))
            phase = str(row.get("special_price_phase", ""))
            phases[phase] += 1
            if row.get("board_scope") == "BSE":
                bse_rows += 1
            if row.get("limit_status") == "UNKNOWN":
                reason = str(row.get("reason") or "")
                reasons[reason] += 1
                if not reason:
                    blank_unknown += 1
            if (sid, day) in keys_needed:
                selected[(sid, day)] = row
            if (sid, day) in phase_starts:
                expected_days[(sid, day)] += 1
                if row.get("limit_status") != "NO_LIMIT" or phase != "DELISTING_FIRST_DAY":
                    findings.append("DELISTING_FIRST_DAY_NOT_NO_LIMIT:" + sid + ":" + day)
    price_receipt = load("reports/v4_02/V4_02_PRICE_LIMIT_ACCEPTANCE_R4_20260927.json")
    checks["r4_price_rows_and_digest"] = (rows == 4035729
        and sha(ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R4_20260927.jsonl.gz") == price_receipt.get("artifact", {}).get("sha256"))
    checks["official_delisting_events_bound_to_no_limit_rows"] = len(phase_starts) == len(events) and len(expected_days) == len(events)
    checks["delisting_period_rule_selection"] = (
        phases["DELISTING_PERIOD"] == 14 * len(events)
        and all(board in {"SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"} for board in [e.get("board_scope") for e in events]))
    checks["all_unknown_price_rows_have_stable_reason"] = blank_unknown == 0 and reasons.get("") == 0
    checks["bse_isolated"] = bse_rows == 0
    if not checks["r4_price_rows_and_digest"]:
        findings.append("R4_PRICE_ROW_COUNT_OR_DIGEST_FAILED")
    if not checks["official_delisting_events_bound_to_no_limit_rows"]:
        findings.append("OFFICIAL_PHASE_ROWS_NOT_RECONCILED")
    if not checks["delisting_period_rule_selection"]:
        findings.append("DELISTING_PERIOD_RULE_SCOPE_FAILED")
    if blank_unknown:
        findings.append(f"UNKNOWN_PRICE_ROWS_WITHOUT_REASON:{blank_unknown}")
    if bse_rows:
        findings.append(f"BSE_ROWS_IN_REQUIRED_PRICE_OUTPUT:{bse_rows}")

    audit = load("reports/v4_02/V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R4.json")
    checks["all_range_exceptions_dispositioned"] = (audit.get("status") == "CLOSED"
        and audit.get("scope", {}).get("r3_current_exception_rows") == 53
        and audit.get("scope", {}).get("undispositioned_engineering_exceptions") == 0
        and all(row.get("disposition") for row in audit.get("dispositions", [])))
    if not checks["all_range_exceptions_dispositioned"]:
        findings.append("R4_RANGE_EXCEPTION_GATE_OPEN")
    checks["dispositions_reconcile_to_price_rows"] = all(
        ((row["security_id"], row["trade_date"]) in selected)
        and (selected[(row["security_id"], row["trade_date"])].get("limit_status") == "NO_LIMIT"
             if row.get("disposition") == "RESOLVED_DELISTING_FIRST_DAY_NO_LIMIT"
             else selected[(row["security_id"], row["trade_date"])].get("limit_status") == "UNKNOWN")
        for row in audit.get("r3_findings", []))
    if not checks["dispositions_reconcile_to_price_rows"]:
        findings.append("R4_EXCEPTION_PRICE_STATUS_MISMATCH")

    r3 = load("reports/v4_02/V4_02_PRICE_LIMIT_ACCEPTANCE_R3_20260927.json")
    r3_reasons = r3.get("unknown_reason_counts", {})
    checks["unsupported_action_unknowns_preserved"] = (reasons.get("CORPORATE_ACTION_REFERENCE_UNSUPPORTED") == r3_reasons.get("CORPORATE_ACTION_REFERENCE_UNSUPPORTED")
        and reasons.get("REFERENCE_CHAIN_BLOCKED_BY_UNSUPPORTED_ACTION") == r3_reasons.get("REFERENCE_CHAIN_BLOCKED_BY_UNSUPPORTED_ACTION")
        and reasons.get("REFERENCE_STATE_UNAVAILABLE") == r3_reasons.get("REFERENCE_STATE_UNAVAILABLE"))
    if not checks["unsupported_action_unknowns_preserved"]:
        findings.append("R3_UNKNOWN_REASON_SCOPE_CHANGED")

    test = load("reports/v4_02/V4_02_FINAL_R4_TEST_RECEIPT.json")
    checks["r3_freeze_and_r4_tests_pass"] = test.get("result") == "PASS" and test.get("failed") == 0 and test.get("skipped") == 0
    if not checks["r3_freeze_and_r4_tests_pass"]:
        findings.append("R4_TEST_RECEIPT_NOT_PASS")

    status = "PASS" if not findings else "BLOCKED"
    result = {"contract_id": "V4_02_FINAL_INDEPENDENT_POSTCHECK_R4", "version": "4.0.0", "status": status,
        "manifest": {"path": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(MANIFEST)},
        "checks": checks, "findings": findings,
        "counts": {"price_rows": rows, "unknown_reasons": dict(reasons), "special_price_phases": dict(phases),
                   "range_exception_dispositions": len(audit.get("dispositions", [])), "current_range_exceptions": len(audit.get("r3_findings", [])),
                   "delisting_event_starts": len(events), "blank_unknown_reason_rows": blank_unknown, "bse_rows": bse_rows},
        "tdx_root_write_count": 0,
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "next_stage": "SEAL_FINAL_R4_RECEIPT_AND_PROMOTE_ACCEPTED_HEAD" if status == "PASS" else "REPAIR_R4_POSTCHECK_FINDINGS"}
    temp = OUT.with_suffix(OUT.suffix + ".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temp.replace(OUT)
    print(json.dumps({"status": status, "checks": checks, "findings": findings}, ensure_ascii=False))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
