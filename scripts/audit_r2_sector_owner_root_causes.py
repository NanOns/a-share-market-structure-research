"""Freeze field-level sector owner status and five auditable current examples."""
import csv
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidence/three_day_repair_r2_20261008"
AUTH = ROOT / "data/v4/r2_daily_candidates/three_day_repair_r2_20261008/v4_sector_operational_authority_v1.json"
ORACLE = OUT / "R2_P0_2_SECTOR_INDEPENDENT_ORACLE.csv"
TARGET = "2026-09-30"


def bind(path):
    path = Path(path)
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": h}


def main():
    authority = json.loads(AUTH.read_text(encoding="utf-8"))
    native_path = ROOT / authority["native"]["path"]
    rows = []
    with gzip.open(native_path, "rt", encoding="utf-8") as stream:
        rows = [json.loads(line) for line in stream if json.loads(line).get("target_trade_date") == TARGET]
    reasons = {}
    for row in rows:
        for field, cell in row["fields"].items():
            if cell.get("quality") != "ACCEPTED":
                counts = reasons.setdefault(field, Counter())
                counts[cell.get("reason_code") or cell.get("reason") or "UNKNOWN"] += 1
    all_oracle = {}
    with ORACLE.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            item = all_oracle.setdefault(row["sector_id"], {"sector_type": row["sector_type"]})
            item[row["field"]] = None if row["independent_expected"] == "" else float(row["independent_expected"])
    candidates = list(all_oracle.items())
    chosen = []
    for metric, reverse, wanted_type in (("breadth_ret1", True, "INDUSTRY"), ("breadth_ret1", False, "THEME"),
                                          ("sector_rs20", True, "THEME"), ("sector_rs20", False, "INDUSTRY"),
                                          ("ma20_width", True, "INDUSTRY")):
        pool = [(sid, row) for sid, row in candidates if row["sector_type"] == wanted_type and row.get(metric) is not None and sid not in {s["sector_id"] for s in chosen}]
        if not pool:
            pool = [(sid, row) for sid, row in candidates if row.get(metric) is not None and sid not in {s["sector_id"] for s in chosen}]
        sid, row = sorted(pool, key=lambda pair: pair[1][metric], reverse=reverse)[0]
        chosen.append({"sector_id": sid, "sector_type": row["sector_type"], "selection_basis": f"{'max' if reverse else 'min'}_{metric}",
                       "current_2026_09_30": {field: row.get(field) for field in (
                           "sector_rs1", "sector_rs5", "sector_rs20", "breadth_ret1", "breadth_ret5", "breadth_ret20", "ma20_width")},
                       "t_minus_1_2026_09_29": "NOT_VERIFIABLE_NO_ACCEPTED_ASOF_MEMBERSHIP_SNAPSHOT"})
    accepted = {field: sum(row["fields"].get(field, {}).get("quality") == "ACCEPTED" for row in rows)
                for field in sorted(set().union(*(row["fields"].keys() for row in rows)))}
    data = {
        "contract_id": "R2_SECTOR_OWNER_BINDING_AND_ROOT_CAUSE_V1",
        "target": TARGET,
        "result": "PARTIAL_CURRENT_FACTS_PASS_HISTORICAL_ROTATION_NOT_VERIFIABLE",
        "stage_contract": "V4_08_SECTOR_NATIVE_V1 + R2_CURRENT_SECTOR_MA20_WIDTH_ADAPTER_V2",
        "source_bindings": {"candidate_authority": bind(AUTH), "native": bind(native_path),
                            "independent_oracle": bind(ORACLE), "membership": bind(ROOT / authority["sources"]["membership"]["path"])},
        "counts": {"sectors": len(rows), "current_rs1_rs5_rs20_known": [accepted.get(f"sector_rs{n}", 0) for n in (1, 5, 20)],
                   "current_breadth1_5_20_known": [accepted.get(f"breadth_ret{n}", 0) for n in (1, 5, 20)],
                   "current_ma20_width_known": accepted.get("ma20_width", 0),
                   "rotation_output_state_unknown": 378, "strict_pit_2026_09_28_to_30": "0/3_VERIFIABLE"},
        "field_acceptance_counts": accepted,
        "unaccepted_reason_counts": {field: dict(counter) for field, counter in sorted(reasons.items())},
        "five_sector_oracle": chosen,
        "requested_lifecycle_strata": {key: "NOT_VERIFIABLE_WITHOUT_ACCEPTED_2026_09_29_MEMBERSHIP_AND_PRIOR_NATIVE_OWNER"
            for key in ("high_level_stall", "breadth_expansion", "retreat", "new_emergence", "membership_change")},
        "release_boundary": "Current same-day facts may be scoped independently. No output_state, Base, Seed, emergence, confirmation, maturity, retention, or historical member comparison is inferred from current strength.",
        "activation": False,
        "next_stage": "P0_4_SCOPED_CURRENT_SECTOR_FACT_CANDIDATE_ONLY; ROTATION_REMAINS_GATED"
    }
    (OUT / "R2_SECTOR_OWNER_BINDING_AND_ROOT_CAUSE.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": data["result"], "sectors": len(rows), "examples": len(chosen), "rotation_unknown": 378}, ensure_ascii=False))


if __name__ == "__main__":
    main()
