"""Audit accepted Replay Gate A prerequisites; stop on upstream PIT blocker."""

from __future__ import annotations

import gzip
import json
import os
from pathlib import Path
import tempfile

import duckdb

from src.v4.replay_inputs import resolve


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/v4_05/V4_05_REPLAY_GATE_A_AUDIT_R1.json"
BLOCK = "V4_05_BLOCKED_UPSTREAM_DEFECT_HISTORICAL_ADJUSTED_PRICE_PIT_LINEAGE"


def write_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        temp = Path(stream.name)
    os.replace(temp, path)


def main() -> None:
    inputs, authority = resolve(ROOT)
    matrix = json.loads((ROOT / "reports/v4_05/V4_05_REPLAY_DATE_MATRIX_R1.json").read_text(encoding="utf-8"))
    if matrix["authority"] != authority or matrix["input_hashes"] != {k: v.sha256 for k, v in sorted(inputs.items())}:
        raise ValueError("frozen matrix authority diverged")
    db = duckdb.connect()
    daily = str(inputs["daily"].path).replace("'", "''")
    lineage = db.execute(
        f"SELECT knowledge_lineage, count(*), min(trade_date), max(trade_date) "
        f"FROM read_parquet('{daily}') GROUP BY 1 ORDER BY 1"
    ).fetchall()
    total = sum(row[1] for row in lineage)
    if total == 0:
        raise ValueError("accepted daily artifact empty")
    # Check a frozen recent universe cell and the later listing boundary using
    # the accepted historical universe, without constructing replay output.
    recent = matrix["cases"]["recent"]["trade_date"]
    short = matrix["cases"]["short_history"]
    recent_board_ids = {row["security_id"] for row in matrix["cases"]["board_coverage"]}
    found_recent = set()
    short_early = 0
    short_recent = 0
    with gzip.open(inputs["universe"].path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            d = row["trade_date"].replace("-", "")
            sid = row["security_id"]
            if d == recent and sid in recent_board_ids:
                found_recent.add(sid)
            if short and sid == short["security_id"]:
                short_early += d < short["first_trade_date"]
                short_recent += d == recent
    g02_pass = found_recent == recent_board_ids and short_early == 0 and short_recent == 1
    if not g02_pass:
        raise ValueError("accepted historical universe frozen sample mismatch")
    expected_lineage = "DIAGNOSTIC_NON_PIT_CURRENT_METADATA_SNAPSHOT"
    g03_block = len(lineage) == 1 and lineage[0][0] == expected_lineage
    if not g03_block:
        raise ValueError("G03 lineage differs; investigate without automatic pass")
    result = {
        "contract_id": "V4_05_REPLAY_GATE_A_AUDIT_R1",
        "status": BLOCK,
        "accepted_input_authority": authority,
        "frozen_matrix": "reports/v4_05/V4_05_REPLAY_DATE_MATRIX_R1.json",
        "gates": {
            "G01_TDX_SOURCE_IDENTITY": {"status": "PASS", "archive_sha256": inputs["tdx_archive"].sha256, "accepted_inputs_verified": sorted(inputs)},
            "G02_HISTORICAL_UNIVERSE": {"status": "PASS_SAMPLED_BOUNDARY", "recent_board_entities_found": sorted(found_recent), "later_listing_early_rows": short_early, "later_listing_recent_rows": short_recent},
            "G03_ADJUSTMENT_REPRODUCIBILITY": {"status": "BLOCKED", "reason": "AS_RECORDED historical adjustment availability cannot be proved from current-metadata snapshot", "lineage_counts": [{"knowledge_lineage": x[0], "rows": x[1], "first_trade_date": x[2], "last_trade_date": x[3]} for x in lineage], "accepted_v4_02_receipt": "reports/v4_02/V4_02_DATA_PERIOD_MAINLINE_FINAL_ACCEPTANCE_R2.json", "accepted_v4_02_pit_receipt": "reports/v4_02/V4_02_CANONICAL_DAILY_PIT_20260924_085207Z_stage_receipt.json"},
            **{f"G{i:02d}_{name}": {"status": "NOT_RUN_BLOCKED_BY_G03"} for i, name in [(4, "DAILY_DETERMINISM"), (5, "FORMAL_PERIOD_ASOF"), (6, "FACTOR_MAX_SOURCE_DATE"), (7, "CORE_PROFILE_REPLAY"), (8, "REVISION_IDEMPOTENCY")]},
        },
        "capabilities": {
            "HISTORICAL_ADJUSTED_PRICE": {"status": "BLOCKED", "capability_scope": "AS_RECORDED historical adjusted coordinates", "affected_dates": [lineage[0][2], lineage[0][3]], "affected_entities": "all accepted daily entities", "affected_fields": ["qfq_mul", "qfq_add", "qfq_open", "qfq_high", "qfq_low", "qfq_close"], "reasons": ["No historical first-availability metadata for accepted adjustment coordinates"], "evidence": ["G03_ADJUSTMENT_REPRODUCIBILITY"]},
            **{name: {"status": "BLOCKED", "capability_scope": name, "affected_dates": "historical replay matrix", "affected_entities": "frozen matrix", "affected_fields": "replay output", "reasons": ["Execution halted at G03 upstream blocker"], "evidence": ["G03_ADJUSTMENT_REPRODUCIBILITY"]} for name in ["STOCK_CORE", "MARKET_REFERENCE", "MARKET_REGIME", "WEEKLY_PERIOD", "MONTHLY_PERIOD"]},
        },
        "data_factor_replay_pass": False,
        "next_stage": "BLOCKED_PENDING_SEPARATELY_ACCEPTED_HISTORICAL_ADJUSTMENT_PIT_REPAIR",
        "v4_08_sector_pit": "SEPARATELY_BLOCKED",
    }
    write_atomic(OUT, result)
    print(f"{BLOCK}: {total} accepted daily rows, all {expected_lineage}")


if __name__ == "__main__":
    main()
