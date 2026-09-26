from __future__ import annotations

"""Independent DuckDB postcheck for V4-02 adjusted daily and period artifacts."""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "data/v4/artifact_store/v4_02"
REPORT = ROOT / "reports/v4_02/V4_02_FORMAL_PERIODS_INDEPENDENT_POSTCHECK_20260926.json"
DAILY_NAME = "V4_02_ADJUSTED_CANONICAL_DAILY_R6_2_20260926.parquet"
PERIOD_NAMES = ["V4_02_FORMAL_WEEKLY_RAW_QFQ_R6_2_20260926.parquet", "V4_02_FORMAL_MONTHLY_RAW_QFQ_R6_2_20260926.parquet"]
EXPECTED_DAILY = 4027002
ASOF = 20260924


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def main() -> int:
    daily = ARTIFACT / DAILY_NAME
    if not daily.is_file():
        raise SystemExit("ADJUSTED_DAILY_ARTIFACT_NOT_FOUND")
    period_paths = [ARTIFACT / name for name in PERIOD_NAMES]
    for path in period_paths:
        if not path.is_file():
            raise SystemExit("PERIOD_ARTIFACT_NOT_FOUND:" + path.name)
    db = duckdb.connect(database=":memory:")
    daily_ref = str(daily).replace("'", "''")
    checks = {}
    summary = db.execute(f"""
      SELECT count(*) AS n,
             count(DISTINCT (canonical_security_id, trade_date)) AS unique_keys,
             count_if(canonical_security_id IS NULL) AS null_security_id,
             count_if(trade_date < 20230704 OR trade_date > {ASOF}) AS out_of_scope_dates,
             count_if(adjusted_quality = 'READY' AND (qfq_open IS NULL OR qfq_high IS NULL OR qfq_low IS NULL OR qfq_close IS NULL)) AS ready_missing_qfq,
             count_if(adjusted_quality <> 'READY' AND (qfq_open IS NOT NULL OR qfq_high IS NOT NULL OR qfq_low IS NOT NULL OR qfq_close IS NOT NULL)) AS unready_raw_fallback,
             count_if(qfq_high < qfq_low) AS invalid_qfq_ohlc
      FROM read_parquet('{daily_ref}')
    """).fetchone()
    quality_counts = db.execute(f"SELECT adjusted_quality,count(*) FROM read_parquet('{daily_ref}') GROUP BY 1 ORDER BY 1").fetchall()
    board_counts = db.execute(f"SELECT board_scope,count(*) FROM read_parquet('{daily_ref}') GROUP BY 1 ORDER BY 1").fetchall()
    checks["daily_rows_match_required_actual_scope"] = summary[0] == EXPECTED_DAILY
    checks["daily_keys_unique"] = summary[0] == summary[1]
    checks["daily_security_ids_nonnull"] = summary[2] == 0
    checks["daily_dates_within_required_scope_and_cutoff"] = summary[3] == 0
    checks["ready_rows_have_qfq_ohlc"] = summary[4] == 0
    checks["unready_rows_do_not_fallback_to_raw"] = summary[5] == 0
    checks["qfq_ohlc_valid"] = summary[6] == 0
    checks["required_boards_present"] = {row[0] for row in board_counts} == {"SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"}

    period_summaries = {}
    for path in period_paths:
        ref = str(path).replace("'", "''")
        pcount = db.execute(f"SELECT count(*) FROM read_parquet('{ref}')").fetchone()[0]
        pchecks = db.execute(f"""
          SELECT count_if(period_view='CLOSED_ONLY' AND (period_last_session IS NULL OR period_last_session > {ASOF})) AS invalid_closed_only,
                 count_if(period_view='CLOSED_ONLY' AND (data_gap_count > 0 OR unknown_count > 0)) AS closed_with_unresolved_status,
                 count_if(calendar_count <> actual_count + suspended_count + data_gap_count + unknown_count) AS status_reconciliation_errors,
                 count_if(price_basis='QFQ' AND period_status='BLOCKED_BY_ADJUSTMENT' AND
                          (open IS NOT NULL OR high IS NOT NULL OR low IS NOT NULL OR close IS NOT NULL)) AS qfq_raw_fallback,
                 count_if(period_view='AS_OF_PARTIAL' AND period_last_session IS NOT NULL AND period_last_session <= {ASOF}) AS invalid_asof_partial
          FROM read_parquet('{ref}')
        """).fetchone()
        basis_counts = db.execute(f"SELECT price_basis,count(*) FROM read_parquet('{ref}') GROUP BY 1 ORDER BY 1").fetchall()
        kind = "WEEKLY" if "WEEKLY" in path.name else "MONTHLY"
        period_summaries[kind] = {"row_count": pcount, "price_basis_counts": {r[0]: r[1] for r in basis_counts},
                                  "invalid_closed_only": pchecks[0], "closed_with_unresolved_status": pchecks[1],
                                  "status_reconciliation_errors": pchecks[2], "qfq_raw_fallback": pchecks[3],
                                  "invalid_asof_partial": pchecks[4]}
        checks[kind.lower() + "_closed_only_periods_are_complete"] = pchecks[0] == 0 and pchecks[1] == 0
        checks[kind.lower() + "_status_counts_reconcile"] = pchecks[2] == 0
        checks[kind.lower() + "_blocked_qfq_never_uses_raw"] = pchecks[3] == 0
        checks[kind.lower() + "_asof_partial_semantics"] = pchecks[4] == 0
        checks[kind.lower() + "_raw_and_qfq_both_present"] = {r[0] for r in basis_counts} == {"RAW", "QFQ"}

        # Independent source aggregation check: period OHLC and sums must match daily source rows.
        periods_cte = f"""
          WITH p AS (SELECT *, row_number() OVER () AS check_period_id FROM read_parquet('{ref}')),
          joined AS (
            SELECT p.check_period_id, p.price_basis, p.period_status, p.open AS actual_open, p.high AS actual_high,
                   p.low AS actual_low, p.close AS actual_close, p.volume AS actual_volume, p.amount AS actual_amount,
                   d.trade_date, d.raw_open, d.raw_high, d.raw_low, d.raw_close,
                   d.qfq_open, d.qfq_high, d.qfq_low, d.qfq_close, d.volume AS daily_volume, d.amount AS daily_amount
            FROM p LEFT JOIN read_parquet('{daily_ref}') d
              ON p.canonical_security_id=d.canonical_security_id AND d.trade_date BETWEEN p.period_start_date AND p.period_end_date
          ),
          agg AS (
            SELECT check_period_id, price_basis, period_status, actual_open, actual_high, actual_low, actual_close,
                   actual_volume, actual_amount,
                   first(CASE WHEN price_basis='RAW' THEN raw_open ELSE qfq_open END ORDER BY trade_date) AS expected_open,
                   max(CASE WHEN price_basis='RAW' THEN raw_high ELSE qfq_high END) AS expected_high,
                   min(CASE WHEN price_basis='RAW' THEN raw_low ELSE qfq_low END) AS expected_low,
                   first(CASE WHEN price_basis='RAW' THEN raw_close ELSE qfq_close END ORDER BY trade_date DESC) AS expected_close,
                   sum(daily_volume) AS expected_volume, sum(daily_amount) AS expected_amount,
                   count(trade_date) AS daily_rows
            FROM joined GROUP BY ALL
          )
          SELECT count_if(period_status NOT IN ('NO_ACTUAL_BARS','BLOCKED_BY_ADJUSTMENT') AND daily_rows > 0 AND
                          (actual_open IS DISTINCT FROM expected_open OR actual_high IS DISTINCT FROM expected_high OR
                           actual_low IS DISTINCT FROM expected_low OR actual_close IS DISTINCT FROM expected_close OR
                           actual_volume IS DISTINCT FROM expected_volume OR abs(actual_amount-expected_amount) > 0.000001)) AS aggregate_mismatches
          FROM agg
        """
        aggregate_mismatches = db.execute(periods_cte).fetchone()[0]
        period_summaries[kind]["independent_daily_aggregate_mismatches"] = aggregate_mismatches
        checks[kind.lower() + "_period_values_match_independent_daily_aggregation"] = aggregate_mismatches == 0

    output_hashes = {path.name: {"sha256": sha(path), "bytes": path.stat().st_size,
                                  "row_count": pq.ParquetFile(path).metadata.num_rows}
                     for path in [daily, *period_paths]}
    all_pass = all(checks.values())
    receipt = {"contract_id": "V4_02_FORMAL_PERIODS_INDEPENDENT_POSTCHECK_V1",
               "status": "PASS" if all_pass else "BLOCKED", "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
               "checks": checks, "daily_summary": {"row_count": summary[0], "unique_keys": summary[1],
                                                    "quality_counts": {r[0]: r[1] for r in quality_counts},
                                                    "board_counts": {r[0]: r[1] for r in board_counts}},
               "period_summaries": period_summaries, "outputs": output_hashes,
               "independence": "DuckDB SQL over emitted daily artifacts; independent Parquet footer/sha256 readback.",
               "execution_identity": {"script_sha256": sha(Path(__file__).resolve()),
                                      "daily_schema": pq.ParquetFile(daily).schema_arrow.names},
               "acceptance_boundary": "Does not independently accept GBBQ semantics or close the temporal leakage suite."}
    atomic_json(REPORT, receipt)
    print(json.dumps({"status": receipt["status"], "checks": checks,
                      "daily_quality": receipt["daily_summary"]["quality_counts"],
                      "periods": period_summaries}, ensure_ascii=False))
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
