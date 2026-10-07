from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
def test_outputs_partition_base():
 p=ROOT/"reports/shadow/v2/20260904/strong_pullback"
 required={"STRONG_PULLBACK_V2_SHADOW.parquet","STRONG_PULLBACK_V2_SUMMARY.json","STRONG_PULLBACK_V1_V2_DIFF.csv","STRONG_PULLBACK_DEPTH_MISMATCH.csv","STRONG_PULLBACK_AUDIT_SAMPLE.csv"}
 assert required<={x.name for x in p.iterdir()}
 s=json.loads((p/"STRONG_PULLBACK_V2_SUMMARY.json").read_text("utf8"))
 assert sum(s["class_counts"].values())==s["v1_strong_pullback_count"]==345
