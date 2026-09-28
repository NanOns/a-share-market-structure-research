"""Independent real-data recomputation; does not import V4-03 production code."""

import hashlib
import json
import math
from pathlib import Path
from statistics import mean

import duckdb


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "reports/v4_03/staging/V4_03_CORE_FACTOR_REAL_SAMPLE_SH600006_R1.json"
RECEIPT = ROOT / "reports/v4_03/V4_03_REAL_SAMPLE_INDEPENDENT_POSTCHECK_R1.json"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def close(a, b):
    return a is not None and b is not None and math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-12)


def main():
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "reports/v4_02/V4_02_FINAL_STAGING_MANIFEST_R6.json").read_text(encoding="utf-8"))
    daily = ROOT / manifest["components"]["DAILY_R7"]["path"]
    if digest(daily) != sample["accepted_daily_sha256"]:
        raise RuntimeError("input artifact drift")
    rows = duckdb.connect().execute(
        "select trade_date,qfq_close from read_parquet(?) where source_security_key=? and trade_date<=? and adjusted_quality=? order by trade_date desc limit 25",
        [daily.as_posix(), sample["security_key"], 20260924, "READY"]).fetchall()
    closes = [float(x[1]) for x in rows]
    ma20 = mean(closes[:20])
    ret5 = closes[0] / closes[5] - 1
    session_returns = [math.log(closes[i] / closes[i + 1]) for i in range(20)]
    center = sum(session_returns) / 20
    vol20 = math.sqrt(sum((x - center) ** 2 for x in session_returns) / 20)
    expected = {"ma20": ma20, "ret5": ret5, "vol20": vol20}
    checks = {name: close(value, sample["fields"][name]["value"]) for name, value in expected.items()}
    receipt = {"contract_id": "V4_03_REAL_SAMPLE_INDEPENDENT_POSTCHECK_R1",
               "status": "DIAGNOSTIC_SAMPLE_PASS" if all(checks.values()) else "DIAGNOSTIC_SAMPLE_FAIL",
               "sample_sha256": digest(SAMPLE), "accepted_daily_sha256": digest(daily),
               "independent_formulas": "plain mean, fixed-endpoint ratio, population standard deviation of 20 adjacent log returns",
               "checks": checks, "expected": expected,
               "actual": {name: sample["fields"][name]["value"] for name in expected},
               "limitations": "Three fields and one security only; not V4-03 full-market independent acceptance"}
    temp = RECEIPT.with_suffix(".json.tmp")
    temp.write_bytes((json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    temp.replace(RECEIPT)
    print(receipt["status"], checks)
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
