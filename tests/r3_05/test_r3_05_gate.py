from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
def test_gate():
 p=ROOT/"reports/shadow/v2/20260904/early_mover";required={"EARLY_MOVER_V2_SHADOW.parquet","EARLY_MOVER_V2_SUMMARY.json","EARLY_MOVER_V1_V2_DIFF.csv","EARLY_MOVER_SECTOR_CONTEXT_AUDIT.csv","EARLY_MOVER_AUDIT_SAMPLE.csv"};assert required<={x.name for x in p.iterdir()};s=json.loads((p/"EARLY_MOVER_V2_SUMMARY.json").read_text("utf8"));assert sum(s["class_counts"].values())==s["v1_early_mover_count"]==86
