from pathlib import Path
import json
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[2]
def test_gate_outputs_and_partition():
    p=ROOT/"reports/shadow/v2/20260904/steady_trend"
    required={"STEADY_TREND_V2_SHADOW.parquet","STEADY_TREND_V2_SUMMARY.json","STEADY_TREND_V1_V2_DIFF.csv","STEADY_TREND_AUDIT_SAMPLE.csv"}
    assert required <= {x.name for x in p.iterdir()}
    s=json.loads((p/"STEADY_TREND_V2_SUMMARY.json").read_text("utf8"))
    assert sum(s["class_counts"].values()) == s["v1_steady_count"] == 198
    x=pq.read_table(p/"STEADY_TREND_V2_SHADOW.parquet",columns=["v1_steady_trend","v2_steady_class","v2_steady_hit"]).to_pandas()
    assert not x.loc[~x.v1_steady_trend,"v2_steady_hit"].any()
