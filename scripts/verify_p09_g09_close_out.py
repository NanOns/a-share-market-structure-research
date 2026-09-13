"""Aggregate the current P09 G09 gate without rewriting historical receipts."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports/upgrade_v3"


def _read(name: str) -> dict:
    return json.loads((REPORTS / name).read_text(encoding="utf-8"))


def main() -> int:
    spec = ROOT / "docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
    audit = _read("P09-REAUDIT-CURRENT-20260913.json")
    mapping = _read("P09-TOPIC-SECTOR-MAPPING-20260913.json")
    metadata = _read("P09-01-B-REMAINING-REPROBE-20260913.json")
    prior = _read("P09-CLOSE-OUT-20260913.json")
    checks = {
        "spec_unchanged": hashlib.sha256(spec.read_bytes()).hexdigest() == prior["stage_contract"]["spec_sha256"],
        "reaudit_full_zero_findings": audit.get("status") == "FULL_PASS" and audit.get("engineering_status") == "FULL_PASS" and not audit.get("findings"),
        "mapping_evidence_pass": mapping.get("status") == "FULL_PASS" and all(item.get("pass") for item in mapping.get("checks", [])),
        "metadata_no_forbidden_persistence": all(metadata.get(key) is False for key in ("raw_payloads_persisted", "rows_persisted", "batches_persisted")),
        "longzijue_sources_full_reprobe": bool(metadata.get("requests")) and all(item.get("status") == "AVAILABLE" for item in metadata.get("requests", [])),
    }
    status = "FULL_PASS" if all(checks.values()) else "BLOCKED"
    payload = {
        "receipt_id": "P09-G09-CURRENT-CLOSE-OUT-20260913",
        "stage": "P09-G09-CURRENT-CLOSE-OUT",
        "status": status,
        "engineering_status": "FULL_PASS" if status == "FULL_PASS" else "BLOCKED",
        "source_status": "FULL_PASS" if status == "FULL_PASS" else "BLOCKED",
        "preview_ready": status == "FULL_PASS",
        "release_ready": status == "FULL_PASS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stage_contract": {"contract_id": "v3-p09-g09-current-close-out-v1.0", "spec_sha256": hashlib.sha256(spec.read_bytes()).hexdigest(), "scope": "P09 actionable engineering audit findings, source capability, online context and UI preview"},
        "checks": checks,
        "known_limits": audit.get("known_limits", []),
        "deferred_enhancements": audit.get("deferred_enhancements", []),
        "evidence": {"reaudit": "reports/upgrade_v3/P09-REAUDIT-CURRENT-20260913.json", "mapping": "reports/upgrade_v3/P09-TOPIC-SECTOR-MAPPING-20260913.json", "metadata": "reports/upgrade_v3/P09-01-B-REMAINING-REPROBE-20260913.json", "tests": "P09 and cross-cutting regression commands recorded in final report"},
        "acceptance": "V3 G09 FULL_PASS: Longzijue core online products, adapters, APIs, page and bounded live reprobe passed." if status == "FULL_PASS" else "G09 blocked by failed current checks.",
        "next_stage": "P10-01" if status == "FULL_PASS" else "P09-REPAIR-AND-RETEST",
        "tdx_inputs_modified": False,
        "production_database_written": False,
    }
    out = REPORTS / "P09-G09-CURRENT-CLOSE-OUT-20260913.json"
    temp = out.with_suffix(out.suffix + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, out)
    print(json.dumps({"status": status, "checks": checks}, ensure_ascii=False))
    return 0 if status == "FULL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
