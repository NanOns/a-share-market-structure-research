from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from shadow_v2.steady_trend import (
    LIMIT_UP_IS_NOT_AN_EXCLUSION,
    RULESET_ID,
    classify,
    continuity_class,
    pulse_class,
)

ROOT = Path(__file__).resolve().parent
CUTOFF = "20260904"
BASE_RUN = "4255c2f108ac4cdabca3e212079d8bf8"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_bytes(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix="." + path.name, suffix=".tmp")
    try:
        os.write(fd, body)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, path)


def atomic_json(path, value):
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n").encode("utf-8"))


def atomic_csv(path, frame):
    atomic_bytes(path, frame.to_csv(index=False).encode("utf-8-sig"))


def quantiles(frame):
    result = {}
    for column in ("up_day_ratio20", "return_concentration_20"):
        series = pd.to_numeric(frame[column], errors="coerce")
        result[column] = {
            "valid_count": int(series.notna().sum()),
            **{name: (None if pd.isna(v) else float(v)) for name, v in zip(
                ("p10", "p25", "median", "p75", "p90"), series.quantile([.10, .25, .50, .75, .90]))},
        }
    return result


def run(requested="latest"):
    if requested != "latest":
        raise ValueError("SHADOW_LATEST_ONLY")
    pointer_path = ROOT / "reports/current/CURRENT_RELEASE.json"
    pointer_before = pointer_path.read_bytes()
    pointer = json.loads(pointer_before)
    identity_before = pointer["latest_release"]["computation_identity"]
    release = ROOT / f"reports/releases/{CUTOFF}/{BASE_RUN}"
    v1_paths = [release / "stocks.csv", release / "candidates.csv", release / "manifest.json", pointer_path]
    v1_hashes_before = {str(p.relative_to(ROOT)): sha256(p) for p in v1_paths}

    diagnostic_path = ROOT / f"reports/shadow/v2/{CUTOFF}/V2_DIAGNOSTIC_FACTORS.parquet"
    diagnostic = pq.read_table(diagnostic_path).to_pandas()
    stock = pd.read_csv(release / "stocks.csv", encoding="utf-8-sig")
    required = ["security_id", "date", "steady_trend", "sector_leader", "breakout_prep", "strong_pullback", "early_mover",
                "TREND_R2_20", "TREND_R2_60", "MDD20", "MDD60", "RET20", "RET60", "RS20", "POS60", "DIST_HIGH20"]
    base = stock[required].copy()
    base["v1_steady_trend"] = base.pop("steady_trend").astype(str).str.lower().eq("true")
    for source, target in (("sector_leader", "v1_sector_leader"), ("breakout_prep", "v1_breakout_prep"),
                           ("strong_pullback", "v1_strong_pullback"), ("early_mover", "v1_early_mover")):
        base[target] = base.pop(source).astype(str).str.lower().eq("true")
    base = base.rename(columns={c: c.lower() for c in ["TREND_R2_20", "TREND_R2_60", "MDD20", "MDD60", "RET20", "RET60", "RS20", "POS60", "DIST_HIGH20"]})
    diag = diagnostic[["security_id", "UP_DAY_RATIO20", "UP_DAY_RATIO20__valid_count", "UP_DAY_RATIO20__valid_ratio", "RETURN_CONCENTRATION_20"]].rename(columns={
        "UP_DAY_RATIO20": "up_day_ratio20", "UP_DAY_RATIO20__valid_count": "up_day_valid_count",
        "UP_DAY_RATIO20__valid_ratio": "up_day_valid_ratio", "RETURN_CONCENTRATION_20": "return_concentration_20"})
    out = base.merge(diag, on="security_id", how="left", validate="one_to_one")
    out["continuity_class"] = [continuity_class(v, n, r) for v, n, r in zip(out.up_day_ratio20, out.up_day_valid_count, out.up_day_valid_ratio)]
    out["pulse_class"] = [pulse_class(v) for v in out.return_concentration_20]
    classified = [classify(v, c, p) for v, c, p in zip(out.v1_steady_trend, out.continuity_class, out.pulse_class)]
    out["v2_steady_class"] = [x[0] for x in classified]
    out["v2_steady_hit"] = [x[1] for x in classified]
    out["shadow_ruleset_id"] = RULESET_ID
    out["shadow"] = True
    out["production_eligible"] = False
    columns = ["security_id", "date", "v1_steady_trend", "up_day_ratio20", "up_day_valid_count", "up_day_valid_ratio",
               "continuity_class", "return_concentration_20", "pulse_class", "v2_steady_class", "v2_steady_hit",
               "trend_r2_20", "trend_r2_60", "mdd20", "mdd60", "ret20", "ret60", "rs20", "pos60", "dist_high20",
               "v1_sector_leader", "v1_breakout_prep", "v1_strong_pullback", "v1_early_mover",
               "shadow_ruleset_id", "shadow", "production_eligible"]
    out = out[columns].sort_values("security_id").reset_index(drop=True)
    target = ROOT / f"reports/shadow/v2/{CUTOFF}/steady_trend"
    target.mkdir(parents=True, exist_ok=True)
    parquet_path = target / "STEADY_TREND_V2_SHADOW.parquet"
    temporary = target / ".STEADY_TREND_V2_SHADOW.parquet.tmp"
    pq.write_table(pa.Table.from_pandas(out, preserve_index=False), temporary, compression="zstd")
    os.replace(temporary, parquet_path)
    hits = out[out.v1_steady_trend].copy()
    class_order = ["STEADY_CORE", "STEADY_ACCEPTABLE", "PULSE_DOMINATED", "CONTINUITY_WEAK", "DATA_INSUFFICIENT"]
    counts = {name: int(hits.v2_steady_class.eq(name).sum()) for name in class_order}
    summary = {
        "phase": "R3-01", "cutoff": CUTOFF, "ruleset_id": RULESET_ID, "v1_steady_count": int(len(hits)),
        "class_counts": counts, "v2_retained_count": int(hits.v2_steady_hit.sum()),
        "limit_up_is_not_an_exclusion": LIMIT_UP_IS_NOT_AN_EXCLUSION,
        "limit_up_day_count_20": "NOT_AVAILABLE",
        "distributions": {
            "NORMAL_UNIVERSE": quantiles(out), "V1_STEADY_TREND": quantiles(hits),
            "STEADY_CORE": quantiles(hits[hits.v2_steady_class.eq("STEADY_CORE")]),
            "PULSE_DOMINATED": quantiles(hits[hits.v2_steady_class.eq("PULSE_DOMINATED")]),
        },
    }
    atomic_json(target / "STEADY_TREND_V2_SUMMARY.json", summary)
    diff = hits[["security_id", "date", "v1_steady_trend", "v2_steady_class", "v2_steady_hit", "continuity_class", "pulse_class"]]
    atomic_csv(target / "STEADY_TREND_V1_V2_DIFF.csv", diff)
    sample = pd.concat([hits[hits.v2_steady_class.eq(name)].head(20) for name in class_order], ignore_index=True)
    atomic_csv(target / "STEADY_TREND_AUDIT_SAMPLE.csv", sample)
    assert pointer_path.read_bytes() == pointer_before
    assert identity_before == json.loads(pointer_path.read_text("utf-8"))["latest_release"]["computation_identity"]
    assert v1_hashes_before == {str(p.relative_to(ROOT)): sha256(p) for p in v1_paths}
    return {"rows": len(out), "counts": counts, "summary": summary, "target": str(target),
            "identity_before": identity_before, "v1_hashes": v1_hashes_before}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="latest")
    print(json.dumps(run(parser.parse_args().date), ensure_ascii=False, indent=2, default=str))
