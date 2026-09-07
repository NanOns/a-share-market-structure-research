from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
def test_gate():
 p=ROOT/"reports/shadow/v2/20260904/sector_leader";required={"SECTOR_LEADER_V2_SHADOW.parquet","SECTOR_LEADER_V2_SUMMARY.json","SECTOR_LEADER_V1_V2_DIFF.csv","SECTOR_LEADER_PRIMARY_SECTOR_CHANGE.csv","SECTOR_LEADER_STYLE_SELF_REINFORCEMENT.csv","SECTOR_LEADER_AUDIT_SAMPLE.csv"};assert required<={x.name for x in p.iterdir()};s=json.loads((p/"SECTOR_LEADER_V2_SUMMARY.json").read_text("utf8"));assert sum(s["class_counts"].values())==s["v1_sector_leader_count"]==505
