"""Independent required-scope MA20 recomputation for diagnostic artifact."""

import gzip
import hashlib
import json
import math
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "reports/v4_03/V4_03_CORE_REQUIRED_SCOPE_DIAGNOSTIC_RECEIPT_R1.json"
OUTPUT = ROOT / "reports/v4_03/staging/V4_03_CORE_REQUIRED_SCOPE_DIAGNOSTIC_R1.jsonl.gz"
POSTCHECK = ROOT / "reports/v4_03/V4_03_CORE_REQUIRED_SCOPE_NUMERIC_POSTCHECK_R1.json"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def main():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    if sha(OUTPUT) != receipt["output_sha256"]:
        raise RuntimeError("diagnostic output drift")
    manifest = json.loads((ROOT / "reports/v4_02/V4_02_FINAL_STAGING_MANIFEST_R6.json").read_text(encoding="utf-8"))
    daily = ROOT / manifest["components"]["DAILY_R7"]["path"]
    if sha(daily) != receipt["daily_sha256"]:
        raise RuntimeError("accepted daily drift")
    sql = """with ranked as (
               select canonical_security_id, trade_date, adjusted_quality,
                      cast(qfq_close as double) as close,
                      row_number() over(partition by canonical_security_id order by trade_date desc) as rn
               from read_parquet(?) where trade_date<=20260924
             )
             select canonical_security_id, avg(close) as independent_ma20,
                    count(*) as n, count(distinct adjusted_quality) as quality_count,
                    min(adjusted_quality) as only_quality
             from ranked where rn<=20 group by canonical_security_id"""
    checks = {r[0]: r[1:] for r in duckdb.connect().execute(sql, [daily.as_posix()]).fetchall()}
    compared, mismatches, observed_by_board = 0, [], {}
    rows = 0
    with gzip.open(OUTPUT, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            rows += 1
            field = row["fields"]["ma20"]
            if field["quality_state"] != "OBSERVED":
                continue
            sid = row["security_id"]
            independent = checks.get(sid)
            compared += 1
            board = row["board_scope"]
            observed_by_board[board] = observed_by_board.get(board, 0) + 1
            if (independent is None or independent[1] != 20 or independent[2] != 1 or independent[3] != "READY"
                    or not math.isclose(field["value"], independent[0], rel_tol=1e-12, abs_tol=1e-12)):
                mismatches.append({"security_id": sid, "actual": field["value"], "independent": independent})
    result = {"contract_id": "V4_03_CORE_REQUIRED_SCOPE_NUMERIC_POSTCHECK_R1",
              "status": "DIAGNOSTIC_MA20_PASS" if not mismatches and rows == receipt["rows_out"] else "DIAGNOSTIC_MA20_FAIL",
              "output_sha256": receipt["output_sha256"], "accepted_daily_sha256": receipt["daily_sha256"],
              "rows_checked": rows, "ma20_observed_compared": compared,
              "ma20_observed_by_board": observed_by_board, "mismatch_count": len(mismatches),
              "mismatch_examples": mismatches[:20],
              "limitations": "Independent numeric MA20 only; not all fields, quality states, PIT membership or V4-03 publication"}
    temp = POSTCHECK.with_suffix(".json.tmp")
    temp.write_bytes((json.dumps(result, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    temp.replace(POSTCHECK)
    print(json.dumps({"status": result["status"], "compared": compared, "mismatches": len(mismatches)}))
    if result["status"] != "DIAGNOSTIC_MA20_PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
