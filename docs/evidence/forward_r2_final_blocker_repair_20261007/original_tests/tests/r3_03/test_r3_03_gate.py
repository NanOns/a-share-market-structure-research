from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
def test_outputs_and_partition():
 p=ROOT/"reports/shadow/v2/20260904/breakout_prep";required={"BREAKOUT_PREP_V2_SHADOW.parquet","BREAKOUT_PREP_V2_SUMMARY.json","BREAKOUT_PREP_V1_V2_DIFF.csv","BREAKOUT_PREP_AUDIT_SAMPLE.csv"}
 assert required<={x.name for x in p.iterdir()};s=json.loads((p/"BREAKOUT_PREP_V2_SUMMARY.json").read_text("utf8"));assert sum(s["class_counts"].values())==s["v1_breakout_prep_count"]==304
