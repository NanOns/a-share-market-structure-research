"""Stage the real 2026-09-30 sector candidate through the existing research reader."""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from scripts.fp01_evidence import write, ref
from workbench_service.current_v4_context import digest
from workbench_service.joint_release import AUTHORITY, validate
from workbench_service.production_v4 import ProductionV4ResearchReader, build_snapshot

EVIDENCE = ROOT / "docs/evidence/three_day_repair_r2_20261008"
DAILY = ROOT / "data/v4/r2_daily_candidates/three_day_repair_r2_20261008"
AUTHORITY_PATH = DAILY / "v4_sector_operational_authority_v1.json"


def main():
    before = (ROOT / AUTHORITY).read_bytes()
    candidate = json.loads(before)
    prior = ProductionV4ResearchReader(ROOT)
    sector = json.loads(AUTHORITY_PATH.read_bytes())
    owners = dict(candidate["daily_owner_authorities"])
    owners["sector"] = sector
    day = candidate["trade_date"]
    focus = dict(trade_date=day, input_data_head=sector["input_data_head"],
                 publication=prior.manifest["sources"]["focus_operational"],
                 journal=prior.manifest["sources"]["focus_journal"])
    snapshot = build_snapshot(ROOT, publish=False, focus_override=focus, authority_overrides=owners)
    staged = ProductionV4ResearchReader(ROOT, snapshot_authority=snapshot["pointer"])
    counts = {}
    for domain in ("stocks", "sectors"):
        total = 0
        offset = 0
        while True:
            page = staged.query(domain, {"limit": 200, "offset": offset})
            total += len(page["items"])
            offset += len(page["items"])
            if offset >= page["total"]:
                break
        counts[domain] = total
    manifest = json.loads((ROOT / snapshot["pointer"]["manifest"]["path"]).read_bytes())
    sectors = []
    with sqlite3.connect((ROOT / manifest["database"]["path"]).as_uri() + "?mode=ro", uri=True) as db:
        for sid, payload in db.execute("SELECT id,payload FROM objects WHERE domain='sectors' ORDER BY id"):
            row = json.loads(payload)
            sectors.append((sid, row["fields"].get("ma20_width", {}).get("value"),
                            row["fields"].get("sector_rs20", {}).get("value"),
                            row["fields"].get("output_state", {}).get("value")))
        stock_states = db.execute("SELECT COUNT(*) FROM objects WHERE domain='stocks' AND json_extract(payload,'$.fields.basic_breakout_state.quality')='UNKNOWN'").fetchone()[0]
    # FP06 carries 5,224 Core factor rows; the accepted identity directory has
    # 5,213 product stock rows.  Keep the two denominators distinct.
    assert counts == {"stocks": 5213, "sectors": 378}
    assert len(sectors) == 378
    assert all(x[3] == "UNKNOWN" for x in sectors), "rotation must remain unknown without accepted prior membership/seed"
    assert (ROOT / AUTHORITY).read_bytes() == before, "live joint authority changed during staging"
    validate(ROOT, candidate)
    entry = {
        "stage": "P0_2_CURRENT_OWNER_CONSUMER_SNAPSHOT",
        "contract": "V4_04_DERIVED_PRIMITIVES_V1 + V4_08_SECTOR_NATIVE_V1 + R2_CURRENT_SECTOR_MA20_WIDTH_ADAPTER_V2 + FP02_RESEARCH_SNAPSHOT_V1",
        "target": day,
        "scope": "SECTORS_CURRENT_STRENGTH_AND_PROFILE_CONSUMER_ONLY",
        "result": "STAGED_READER_PASS_ROTATION_UNKNOWN",
        "snapshot": snapshot,
        "sector_authority": ref(AUTHORITY_PATH),
        "counts": {**counts, "sector_rows_with_current_width": sum(x[1] is not None for x in sectors),
                   "sector_rows_with_current_rs20": sum(x[2] is not None for x in sectors),
                   "rotation_output_unknown": sum(x[3] == "UNKNOWN" for x in sectors),
                   "stock_breakout_unknown": stock_states},
        "live_joint_authority_before_sha256": digest(before),
        "live_joint_authority_unchanged": True,
        "strict_pit_historical_membership": "NOT_VERIFIABLE",
        "profile_to_structure_owner": "NOT_PROVED_BY_THIS_SNAPSHOT; stock structure predicates remain owner-scoped UNKNOWN",
        "activation": False,
        "acceptance": "ENGINEERING_CONSUMER_PASS_ONLY",
        "next_stage": "E6_SCOPED_PUBLICATION_CAS_AND_TWO_RESOLUTION_IAB_OR_KEEP_GATED_IF_OWNER_SCOPE_FAILS",
    }
    write(EVIDENCE / "R2_P0_2_OWNER_CONSUMER_SNAPSHOT.json", entry)
    print(json.dumps({"result": entry["result"], "counts": entry["counts"], "snapshot": snapshot["pointer"]["manifest"]["sha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
