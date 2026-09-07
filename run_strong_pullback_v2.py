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

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from shadow_v2.strong_pullback import RULESET_ID, classify, depth_status, segment_status, volume_status

CUTOFF = "20260904"
BASE_RUN = "4255c2f108ac4cdabca3e212079d8bf8"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix="." + path.name, suffix=".tmp")
    try:
        os.write(fd, body)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, path)


def write_json(path, value):
    atomic(path, (json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n").encode())


def write_csv(path, frame):
    atomic(path, frame.to_csv(index=False).encode("utf-8-sig"))


def distribution(frame):
    result = {}
    for column in ("days_since_peak_20", "current_drawdown_from_peak_20", "pullback_amount_ratio"):
        series = pd.to_numeric(frame[column], errors="coerce")
        quantiles = series.quantile([.10, .25, .50, .75, .90])
        result[column] = {
            "valid_count": int(series.notna().sum()),
            "null_count": int(series.isna().sum()),
            **{name: (None if pd.isna(value) else float(value)) for name, value in zip(
                ("p10", "p25", "median", "p75", "p90"), quantiles)},
        }
    return result


def run(requested="latest"):
    if requested != "latest":
        raise ValueError("SHADOW_LATEST_ONLY")
    pointer = ROOT / "reports/current/CURRENT_RELEASE.json"
    pointer_before = pointer.read_bytes()
    current = json.loads(pointer_before)
    identity = current["latest_release"]["computation_identity"]["sha256"]
    release = ROOT / f"reports/releases/{CUTOFF}/{BASE_RUN}"
    v1_paths = [release / name for name in ("stocks.csv", "candidates.csv", "manifest.json")] + [pointer]
    hashes = {str(path.relative_to(ROOT)): sha(path) for path in v1_paths}

    diagnostic = pq.read_table(ROOT / f"reports/shadow/v2/{CUTOFF}/V2_DIAGNOSTIC_FACTORS.parquet").to_pandas()
    stocks = pd.read_csv(release / "stocks.csv", encoding="utf-8-sig")
    source_columns = ["security_id", "date", "strong_pullback", "RET60", "TREND_SLOPE_60", "TREND_R2_60", "RS60", "POS60", "MDD20", "DIST_HIGH20", "RET5", "RET20"]
    base = stocks[source_columns].copy()
    base["v1_strong_pullback"] = base.pop("strong_pullback").astype(str).str.lower().eq("true")
    diagnostic_columns = ["security_id", "recent_peak_date_20", "recent_peak_close_20", "days_since_peak_20", "current_drawdown_from_peak_20", "advance_amount_mean", "pullback_amount_mean", "pullback_amount_ratio"]
    out = base.merge(diagnostic[diagnostic_columns], on="security_id", how="left", validate="one_to_one")
    out["segment_status"] = [segment_status(value) for value in out.days_since_peak_20]
    out["depth_status"] = [depth_status(value) for value in out.current_drawdown_from_peak_20]
    out["volume_status"] = [volume_status(a, p, r) for a, p, r in zip(out.advance_amount_mean, out.pullback_amount_mean, out.pullback_amount_ratio)]
    classified = [classify(v1, segment, depth, volume) for v1, segment, depth, volume in zip(out.v1_strong_pullback, out.segment_status, out.depth_status, out.volume_status)]
    out["v2_pullback_class"] = [value[0] for value in classified]
    out["v2_pullback_structure_hit"] = [value[1] for value in classified]
    out["v2_pullback_volume_confirmed"] = [value[2] for value in classified]
    steady = pq.read_table(ROOT / f"reports/shadow/v2/{CUTOFF}/steady_trend/STEADY_TREND_V2_SHADOW.parquet", columns=["security_id", "v2_steady_class"]).to_pandas().rename(columns={"v2_steady_class": "steady_trend_v2_class"})
    out = out.merge(steady, on="security_id", how="left", validate="one_to_one")
    out["shadow_ruleset_id"] = RULESET_ID
    out["shadow"] = True
    out["production_eligible"] = False
    out = out.sort_values("security_id").reset_index(drop=True)

    target = ROOT / f"reports/shadow/v2/{CUTOFF}/strong_pullback"
    target.mkdir(parents=True, exist_ok=True)
    temporary = target / ".STRONG_PULLBACK_V2_SHADOW.parquet.tmp"
    pq.write_table(pa.Table.from_pandas(out, preserve_index=False), temporary, compression="zstd")
    os.replace(temporary, target / "STRONG_PULLBACK_V2_SHADOW.parquet")
    hits = out[out.v1_strong_pullback].copy()
    classes = ("PULLBACK_CORE", "PULLBACK_STRUCTURE_ONLY", "EARLY_PULLBACK", "DEPTH_MISMATCH", "DATA_INSUFFICIENT")
    counts = {name: int(hits.v2_pullback_class.eq(name).sum()) for name in classes}
    summary = {
        "phase": "R3-02", "cutoff": CUTOFF, "ruleset_id": RULESET_ID,
        "v1_strong_pullback_count": int(len(hits)), "class_counts": counts,
        "structure_hit_count": int(hits.v2_pullback_structure_hit.sum()),
        "volume_confirmed_count": int(hits.v2_pullback_volume_confirmed.sum()),
        "distributions": {
            "NORMAL_UNIVERSE": distribution(out), "V1_STRONG_PULLBACK": distribution(hits),
            "PULLBACK_CORE": distribution(hits[hits.v2_pullback_class.eq("PULLBACK_CORE")]),
            "PULLBACK_STRUCTURE_ONLY": distribution(hits[hits.v2_pullback_class.eq("PULLBACK_STRUCTURE_ONLY")]),
        },
    }
    write_json(target / "STRONG_PULLBACK_V2_SUMMARY.json", summary)
    diff_columns = ["security_id", "date", "v1_strong_pullback", "segment_status", "depth_status", "volume_status", "v2_pullback_class", "v2_pullback_structure_hit", "v2_pullback_volume_confirmed"]
    write_csv(target / "STRONG_PULLBACK_V1_V2_DIFF.csv", hits[diff_columns])
    mismatch_columns = ["security_id", "MDD20", "DIST_HIGH20", "current_drawdown_from_peak_20", "recent_peak_date_20", "depth_status"]
    mismatch = hits[hits.v2_pullback_class.eq("DEPTH_MISMATCH")][mismatch_columns].rename(columns={"depth_status": "reason"})
    write_csv(target / "STRONG_PULLBACK_DEPTH_MISMATCH.csv", mismatch)
    sample = pd.concat([hits[hits.v2_pullback_class.eq(name)].head(20) for name in classes], ignore_index=True)
    write_csv(target / "STRONG_PULLBACK_AUDIT_SAMPLE.csv", sample)

    assert pointer.read_bytes() == pointer_before
    assert json.loads(pointer.read_text("utf8"))["latest_release"]["computation_identity"]["sha256"] == identity
    assert hashes == {str(path.relative_to(ROOT)): sha(path) for path in v1_paths}
    return {"rows": len(out), "counts": counts, "summary": summary, "target": str(target), "v1_identity": identity, "v1_hashes": hashes}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="latest")
    print(json.dumps(run(parser.parse_args().date), ensure_ascii=False, indent=2, default=str))
