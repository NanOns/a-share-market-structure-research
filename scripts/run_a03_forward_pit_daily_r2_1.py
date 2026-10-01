"""Current A03 daily entry: payload-derived schema/date checks before publication."""
import argparse
import json
from pathlib import Path
from workbench_analysis.forward_pit_ledger_r2_1 import append_observation,rebuild_latest
from workbench_analysis.forward_pit_ledger_r2 import canonical

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project-root",type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument("--capture-envelope",type=Path)
    p.add_argument("--ledger",default="data/v4/a03_forward_pit_r2")
    p.add_argument("--recover",action="store_true")
    a=p.parse_args()
    if a.recover:result=rebuild_latest(a.project_root,a.ledger)
    else:
        if not a.capture_envelope:p.error("--capture-envelope required unless --recover")
        result=append_observation(a.project_root,a.ledger,json.loads(a.capture_envelope.read_text(encoding="utf8")))
    print(canonical(result).decode("utf8"))

if __name__=="__main__":main()
