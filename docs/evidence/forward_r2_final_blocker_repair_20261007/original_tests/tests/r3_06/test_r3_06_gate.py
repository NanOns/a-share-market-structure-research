from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
def test_gate():
 p=ROOT/"reports/shadow/v2/20260904/priority";required={"V2_UNIFIED_RESEARCH_BOARD.parquet","V2_QUEUE_MEMBERSHIP.parquet","V2_PRIORITY_SUMMARY.json","V2_STRUCTURE_OVERLAP_MATRIX.csv","V1_V2_PRIORITY_DIFF.csv","V2_LEADER_DOMINANCE_AUDIT.json","V2_PRIORITY_AUDIT_SAMPLE.csv","V2_PRIORITY_SHADOW_IDENTITY.json"};assert required<={x.name for x in p.iterdir()};s=json.loads((p/"V2_PRIORITY_SUMMARY.json").read_text());assert sum(s["band_counts"].values())==1015
