"""Read-only P09 RELATED mapping evidence; no source rows are persisted."""

from __future__ import annotations

import json
import os
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_online.p09_products import P09OnlineProducts  # noqa: E402
from workbench_service.p09_context import _security_key, load_mapping, select_mappings  # noqa: E402


def main() -> int:
    mapping = load_mapping(ROOT)
    db_path = ROOT / "data/database/market_research.duckdb"
    topics = P09OnlineProducts().topics(trade_date="2026-09-11")
    checks: list[dict[str, object]] = []
    with duckdb.connect(str(db_path), read_only=True) as db:
        run = db.execute("SELECT run_id,publication_id,cast(trade_date AS VARCHAR),membership_snapshot_id FROM research_runs WHERE run_id=? AND status='COMPLETE'", [mapping.get("local_run_id")]).fetchone()
        checks.append({"id": "BOUND_COMPLETE_RUN", "pass": bool(run and run[2] == mapping.get("local_trade_date") and run[3] == mapping.get("local_membership_snapshot_id"))})
        checks.append({"id": "SOURCE_HASHES", "pass": topics.get("source_hashes") == {"EXT03": mapping.get("source_ext03_sha256"), "EXT04": mapping.get("source_ext04_sha256")}})
        for entry in mapping.get("entries", []):
            source_date = entry.get("source_trade_date")
            selected = select_mappings(mapping, publication_id=entry["publication_id"], sector_id=entry["sector_id"], topics=topics.get("items", []), source_date=source_date, local_run_id=run[0] if run else None, local_date=run[2] if run else None)
            names = db.execute("SELECT DISTINCT sector_name FROM sector_daily WHERE publication_id=? AND sector_id=?", [entry["publication_id"], entry["sector_id"]]).fetchall()
            members = db.execute("SELECT security_id FROM membership_entries WHERE membership_snapshot_id=? AND sector_id=?", [mapping.get("local_membership_snapshot_id"), entry["sector_id"]]).fetchall()
            local_codes = {key for (raw,) in members if (key := _security_key(raw)) is not None}
            source_codes = {key for item in selected[0]["topic"].get("members", []) if (key := _security_key(item.get("source_code"))) is not None} if len(selected) == 1 else set()
            passed = len(selected) == 1 and len(names) == 1 and names[0][0] == entry["source_topic_name"] and len(source_codes) == entry["source_member_count"] and len(local_codes) == entry["local_member_count"] and len(source_codes & local_codes) == entry["overlap_count"] and entry["relation"] == "RELATED"
            checks.append({"id": entry["evidence_id"], "pass": passed, "source_member_count": len(source_codes), "local_member_count": len(local_codes), "overlap_count": len(source_codes & local_codes)})
    status = "FULL_PASS" if checks and all(item["pass"] for item in checks) else "BLOCKED"
    receipt = {"receipt_id": "P09-TOPIC-SECTOR-MAPPING-20260913", "stage": "P09-MAPPING-EVIDENCE", "status": status, "contract_id": mapping.get("contract_id"), "mapping_sha256": hashlib.sha256((ROOT / "config/p09_topic_sector_mapping_v1.json").read_bytes()).hexdigest(), "generated_at": datetime.now(timezone.utc).isoformat(), "checks": checks, "source_date": "2026-09-11", "local_date": mapping.get("local_trade_date"), "source_hashes": topics.get("source_hashes"), "raw_payloads_persisted": False, "rows_persisted": False, "tdx_inputs_modified": False, "next_stage": "P09-REAUDIT-CURRENT" if status == "FULL_PASS" else "P09-MAPPING-REPAIR"}
    target = ROOT / "reports/upgrade_v3/P09-TOPIC-SECTOR-MAPPING-20260913.json"
    temp = target.with_suffix(target.suffix + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, target)
    print(json.dumps({"status": status, "checks": checks}, ensure_ascii=False))
    return 0 if status == "FULL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
