"""Append namespace-separated amendment evidence; preserve initial R1 bytes."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
from v4.rps_pit_history_a02_v1 import read_bound,binding,immutable_json
from scripts.build_a02_rps_history_candidate_r1 import downstream_replay

def main():
    old=ROOT/'reports/audits/A02_RPS_HISTORY_BOOTSTRAP_EVIDENCE_R1.json'
    evidence=json.loads(old.read_text(encoding='utf8'))
    publications={day:read_bound(ROOT,ref) for day,ref in evidence['publications'].items()}
    timestamp=json.loads((ROOT/'reports/next_round_r1/BATCH_STAGE_ENTRY_R1.json').read_text(encoding='utf8'))['observed_at']
    evidence['downstream_replay']=downstream_replay(publications,evidence['deltas'],timestamp,ROOT/'data/v4/a02_rps_history_r1',revision='R2')
    evidence['supersedes']=binding(ROOT,old)
    evidence['namespace_hardening']='Initial R1 replay retained. Final R2 derived Core/Factor/Seed candidates use distinct candidate publication namespaces, never reuse accepted publication namespace; only original source provenance references the accepted publication.'
    evidence['reader_runtime_binding']=binding(ROOT,ROOT/'src/v4/rps_history_reader_a02_v1.py')
    evidence['final_revision']='R2'
    immutable_json(ROOT/'reports/audits/A02_RPS_HISTORY_BOOTSTRAP_EVIDENCE_R2.json',evidence)
    print(json.dumps(dict(status=evidence['status'],final_revision='R2',seed_counts=evidence['downstream_replay']['new_seed_counts'],stock_business_changed=evidence['downstream_replay']['stock_business_changed'])))
if __name__=='__main__': main()
