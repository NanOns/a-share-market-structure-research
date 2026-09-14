"""Read-only source availability and bounded static-history repeatability probe."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
PARQUET = ROOT / "data/normalized/adjusted_daily.parquet"
SPEC = ROOT / "docs/V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md"
OUT = ROOT / "reports/p12_02/remaining_history_validation.json"
DATES = ("2026-03-31", "2026-06-30", "2026-09-14")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    revisions = sorted(path.parent.parent.name for path in
                       (ROOT / "reports/revisions").glob("*/revision-*/INPUT_SNAPSHOT_MANIFEST.json"))
    out_dir = OUT.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    shards = []
    with duckdb.connect(database=":memory:") as con:
        for day in DATES:
            measurements = []
            for _ in range(2):
                fd, name = tempfile.mkstemp(prefix="p12_02_static_", suffix=".parquet", dir=out_dir)
                os.close(fd)
                target = Path(name)
                try:
                    # Stable sort and schema; RAW static facts only, no historical PIT claim.
                    source_sql = str(PARQUET).replace("'", "''")
                    target_sql = str(target).replace("'", "''")
                    con.execute(f"""
                        COPY (
                          SELECT security_id,date,raw_open,raw_high,raw_low,raw_close,
                                 raw_amount,raw_volume,has_actual_bar,is_synthetic_fill
                          FROM read_parquet('{source_sql}') WHERE date='{day}' ORDER BY security_id
                        ) TO '{target_sql}' (FORMAT PARQUET, COMPRESSION ZSTD)
                    """)
                    count = con.execute("SELECT count(*) FROM read_parquet(?)", [str(target)]).fetchone()[0]
                    measurements.append({"sha256": digest(target), "bytes": target.stat().st_size,
                                         "rows": count})
                finally:
                    target.unlink(missing_ok=True)
            shards.append({"date": day, "measurements": measurements,
                           "repeat_identical": measurements[0] == measurements[1]})
    history_cutoffs = [day for day in DATES if day.replace("-", "") not in revisions]
    result = {
        "stage_contract": "P12-02_REMAINING_HISTORY_VALIDATION_V1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "consulted_spec_sha256": digest(SPEC),
        "input_identity": {"adjusted_daily_sha256": digest(PARQUET),
                           "source_revision_dates": revisions},
        "historic_pit_source_evidence": {
            "target_dates_without_source_revision": history_cutoffs,
            "source_gbbq_known_at_verified": False,
            "historic_universe_asof_verified": False,
            "status": "RECONSTRUCTED_CURRENT_SOURCE_ONLY"},
        "static_raw_shards": shards,
        "temporary_shards_removed": True,
        "acceptance_result": "DEGRADED_PASS" if all(s["repeat_identical"] for s in shards) else "BLOCKED",
        "acceptance_scope": "Three-date RAW static shard repeatability and size; no historic PIT claim",
        "next_stage": "P12-02_FACTOR_V3_3_CONTINUE",
    }
    fd, name = tempfile.mkstemp(prefix="remaining_history_", suffix=".tmp", dir=out_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, OUT)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    if result["acceptance_result"] == "BLOCKED":
        raise RuntimeError("Static shard repeatability failed")
    print(OUT)


if __name__ == "__main__":
    main()
