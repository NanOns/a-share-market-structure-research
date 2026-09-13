"""Repair missing historical target-domain references in the activated snapshot."""

from __future__ import annotations

from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "database" / "market_research.duckdb"
ACTIVATION_REPORT = ROOT / "reports" / "upgrade_v3" / "P11-V3-DAILY-ACTIVATION-20260913.json"
REPORT = ROOT / "reports" / "upgrade_v3" / "P11-V3-SNAPSHOT-COMPATIBILITY-REPAIR-20260913.json"
PUBLICATION_ID = "m4-8a99c99719061f4f1f166d0b9184506c"
TARGET_DOMAINS = ("technical", "strength", "high", "structure", "summary", "member_state")
CURRENT_DAY = "2026-09-10"
CONTRACT_VERSION = "V3_P11_SNAPSHOT_COMPATIBILITY_REPAIR_V1_0"


def atomic_write(payload: dict[str, object]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(REPORT.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, REPORT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair V3 activated snapshot historical references")
    parser.add_argument("--apply", action="store_true", help="insert only missing immutable snapshot-entry references")
    args = parser.parse_args()
    activation = json.loads(ACTIVATION_REPORT.read_text(encoding="utf-8"))
    previous_receipt = {}
    if REPORT.exists():
        try:
            previous_receipt = json.loads(REPORT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous_receipt = {}
    current_snapshot = str(activation["build_result"]["snapshot_binding"]["snapshot_id"])
    source_snapshot = str(activation["build_result"]["source_snapshot_id"])
    before_stat = DB.stat()
    with duckdb.connect(str(DB), read_only=not args.apply) as connection:
        source_rows = connection.execute(
            "SELECT domain,cast(trade_date as varchar),slice_id FROM analysis_snapshot_entries WHERE snapshot_id=? AND domain IN (?,?,?,?,?,?) ORDER BY domain,trade_date",
            [source_snapshot, *TARGET_DOMAINS],
        ).fetchall()
        current_rows = connection.execute(
            "SELECT domain,cast(trade_date as varchar),slice_id FROM analysis_snapshot_entries WHERE snapshot_id=? AND domain IN (?,?,?,?,?,?) ORDER BY domain,trade_date",
            [current_snapshot, *TARGET_DOMAINS],
        ).fetchall()
        source_map = {(str(domain), str(day)): str(slice_id) for domain, day, slice_id in source_rows}
        current_map = {(str(domain), str(day)): str(slice_id) for domain, day, slice_id in current_rows}
        missing = [(domain, day, slice_id) for (domain, day), slice_id in sorted(source_map.items()) if (domain, day) not in current_map]
        conflicts = [(domain, day, current_map[(domain, day)], slice_id) for (domain, day), slice_id in sorted(source_map.items()) if (domain, day) in current_map and current_map[(domain, day)] != slice_id and day != "2026-09-10"]
        inserted = []
        if args.apply and missing:
            connection.execute("BEGIN TRANSACTION")
            try:
                for domain, day, slice_id in missing:
                    connection.execute(
                        "INSERT INTO analysis_snapshot_entries VALUES (?,?,?,?)",
                        [current_snapshot, domain, day, slice_id],
                    )
                    inserted.append({"domain": domain, "trade_date": day, "slice_id": slice_id})
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
        final_rows = connection.execute(
            "SELECT domain,cast(trade_date as varchar),slice_id FROM analysis_snapshot_entries WHERE snapshot_id=? AND domain IN (?,?,?,?,?,?) ORDER BY domain,trade_date",
            [current_snapshot, *TARGET_DOMAINS],
        ).fetchall()
    after_stat = DB.stat()
    final_map = {(str(domain), str(day)): str(slice_id) for domain, day, slice_id in final_rows}
    source_historical_map = {(domain, day): slice_id for (domain, day), slice_id in source_map.items() if day != CURRENT_DAY}
    final_historical_map = {(domain, day): slice_id for (domain, day), slice_id in final_map.items() if day != CURRENT_DAY}
    current_day_before_map = {(domain, day): slice_id for (domain, day), slice_id in current_map.items() if day == CURRENT_DAY}
    current_day_final_map = {(domain, day): slice_id for (domain, day), slice_id in final_map.items() if day == CURRENT_DAY}
    historical_missing_after = [
        (domain, day, slice_id)
        for (domain, day), slice_id in sorted(source_historical_map.items())
        if final_historical_map.get((domain, day)) != slice_id
    ]
    previously_inserted = previous_receipt.get("after", {}).get("inserted_entries", [])
    effective_inserted = inserted or [
        entry for entry in previously_inserted
        if final_map.get((str(entry.get("domain")), str(entry.get("trade_date")))) == str(entry.get("slice_id"))
    ]
    previous_before = previous_receipt.get("before", {})
    baseline_missing_entries = previous_before.get("missing_entries") if previous_before.get("missing_entries") else [
        {"domain": d, "trade_date": day, "slice_id": sid} for d, day, sid in missing
    ]
    baseline_target_entry_count = previous_before.get("target_entry_count", len(current_rows))
    checks = {
        "source_snapshot_has_target_entries": bool(source_rows),
        "no_historical_slice_conflicts": not conflicts,
        "apply_requested": bool(args.apply),
        "all_missing_entries_inserted": not historical_missing_after and all(
            final_map.get((domain, day)) == slice_id for domain, day, slice_id in missing
        ),
        "final_historical_target_entries_equal_source": final_historical_map == source_historical_map,
        "current_day_entries_preserved": current_day_final_map == current_day_before_map,
        "final_target_entry_count_matches_source": len(final_rows) == len(source_rows),
        "database_stat_available": after_stat.st_size > 0 and after_stat.st_mtime_ns > 0,
    }
    status = "FULL_PASS" if all(checks.values()) else "BLOCKED"
    payload = {
        "receipt_id": "P11-V3-SNAPSHOT-COMPATIBILITY-REPAIR-20260913",
        "stage": "P11 V3 snapshot historical target-entry compatibility repair",
        "status": status,
        "contract_version": CONTRACT_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage_contract": {
            "spec_section": "§18.7 P04-02；§18.14 P11-04；§20.3–§20.8",
            "scope": "补齐新激活 snapshot 中缺失的既有 target-domain immutable slice 引用；不删除旧 snapshot、不创建业务事实、不改旧表。",
        },
        "checks": checks,
        "publication_id": PUBLICATION_ID,
        "source_snapshot_id": source_snapshot,
        "current_snapshot_id": current_snapshot,
        "target_domains": list(TARGET_DOMAINS),
        "before": {"target_entry_count": baseline_target_entry_count, "source_target_entry_count": len(source_rows), "missing_count": len(baseline_missing_entries), "missing_entries": baseline_missing_entries, "conflicts": conflicts},
        "after": {"target_entry_count": len(final_rows), "inserted_count": len(effective_inserted), "inserted_entries": effective_inserted, "historical_missing_after": [{"domain": d, "trade_date": day, "slice_id": sid} for d, day, sid in historical_missing_after]},
        "execution_observation": {"target_entry_count_before_this_attempt": len(current_rows), "missing_count_before_this_attempt": len(missing), "inserted_this_attempt": len(inserted)},
        "database_boundary": {"path": str(DB), "before": {"size": before_stat.st_size, "mtime_ns": before_stat.st_mtime_ns}, "after": {"size": after_stat.st_size, "mtime_ns": after_stat.st_mtime_ns}},
        "acceptance": "FULL_PASS：当前 publication 的新 snapshot 已恢复与 source snapshot 相同的旧日期 target 域历史引用；当前日新 slice 保持，旧日期 immutable slice 只补引用；无删除、无重算、无 TDX 访问。" if status == "FULL_PASS" else "BLOCKED：snapshot 历史引用仍不完整或存在冲突。",
        "known_limits": [
            "本修复只补 snapshot-entry 引用，不重新计算 2026-09-08/09 的业务结果。",
            "P10-03 效果观察仍为 EFFECT_OBSERVATION_PENDING；旧表保留决定不变。",
        ],
        "next_stage": "V3_DAILY_OPERATION_AND_P10_03_EFFECT_OBSERVATION",
        "safety": {"old_snapshot_deleted": False, "old_tables_deleted": False, "tdx_inputs_modified": False, "business_rows_recalculated": False},
    }
    atomic_write(payload)
    print(json.dumps({"status": status, "apply": args.apply, "missing_before": len(missing), "inserted": len(inserted), "current_snapshot_id": current_snapshot}, ensure_ascii=False))
    return 0 if status == "FULL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
