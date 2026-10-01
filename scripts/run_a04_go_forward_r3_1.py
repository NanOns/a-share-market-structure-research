"""Current A04 accepted-source daily admission; original R3 evidence is immutable."""
import argparse
import json
from pathlib import Path
from workbench_analysis.forward_pit_ledger_r2 import atomic,canonical,reference
from workbench_analysis.amount_a_source_binding_r3_1 import append_accepted_observation,compute_ledger_candidate

def main():
    p=argparse.ArgumentParser();p.add_argument("--project-root",type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument("--data-head",type=Path,default=Path("data/v4/V4_DATA_ACCEPTED_HEAD.json"))
    p.add_argument("--membership-head",type=Path,default=Path("data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json"))
    a=p.parse_args();root=a.project_root.resolve()
    ref=append_accepted_observation(root,data_head_binding=reference(root,root/a.data_head),membership_head_binding=reference(root,root/a.membership_head))
    bindings=[reference(root,path) for path in sorted((root/"data/v4/a04_go_forward_r3/observations").glob("*.json"))]
    target=json.loads((root/a.data_head).read_text(encoding="utf8"))["accepted_trade_date"]
    candidate=compute_ledger_candidate(root,bindings,target=target)
    path=root/"reports/audits/a04_r3/candidates"/(candidate["publication_id"].split(":")[1]+".json")
    atomic(path,canonical(candidate),immutable=True)
    print(canonical({"status":"A04_R3_GO_FORWARD_FORMAL_AUTHORITY_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT","admission_contract":"A04_ACCEPTED_SOURCE_ADMISSION_R3_1","observation":ref,"candidate":reference(root,path),"formal_consumer_enabled":False}).decode("utf8"))

if __name__=="__main__":main()
