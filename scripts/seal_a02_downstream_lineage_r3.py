"""Seal a separate candidate Seed artifact and exact downstream input binding."""
from pathlib import Path
import gzip
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from v4.rps_pit_history_a02_v1 import binding,immutable_json,digest
from v4.stock_prewatch import write_immutable_gzip_jsonl,load_package,build
from v4.base_seed import _logical_digest

def rows(ref):
    with gzip.open(ROOT/ref['path'],'rt',encoding='utf8') as stream: return [json.loads(line) for line in stream]

def main():
    parent=ROOT/'reports/audits/A02_RPS_HISTORY_BOOTSTRAP_EVIDENCE_R2.json'
    evidence=json.loads(parent.read_text(encoding='utf8'));replay=evidence['downstream_replay'];refs=replay['artifacts']
    cores=rows(refs[0]);factors=rows(refs[1]);seeds=[r['new'] for r in rows(refs[2])]
    assert _logical_digest(seeds,replay['new_seed_context']['source_bindings'])==replay['new_stock_context']['source_bindings']['seed_logical_digest']
    directory=ROOT/'data/v4/a02_rps_history_r1';seedpath=directory/'V4_07_SEED_AMENDMENT_CANDIDATE_R2.jsonl.gz'
    write_immutable_gzip_jsonl(seedpath,seeds)
    context=replay['new_stock_context'];context['source_bindings']['seed_artifact']=dict(**binding(ROOT,seedpath),logical_digest=context['source_bindings']['seed_logical_digest'],row_count=len(seeds))
    context['context_id']='A02_AMENDMENT_CORE_SEED:'+digest(context['source_bindings'])
    newstock=build(cores,factors,seeds,context,load_package(ROOT));oldstock=[r['old'] for r in rows(refs[3])]
    stockpath=directory/'V4_09_FULL_AMENDMENT_REPLAY_R3.jsonl.gz';write_immutable_gzip_jsonl(stockpath,[dict(security_id=a['security_id'],old=a,new=b) for a,b in zip(oldstock,newstock)])
    # Business outputs remain identical to R2; only corrected publication/input
    # lineage and its derived digests change. Old candidate revisions remain.
    previous=[r['new'] for r in rows(refs[3])]
    fields=['base_seed_state','mandatory_core_quality_ready','raw_qualification','emergence_axis','structure_quality_axis','risk_axis','priority_bucket','priority_sort_key','waiting_for','quality']
    assert all(all(a[f]==b[f] for f in fields) for a,b in zip(previous,newstock))
    replay['artifacts'][3]=binding(ROOT,stockpath);replay['seed_amendment_artifact']=binding(ROOT,seedpath)
    evidence['supersedes']=binding(ROOT,parent);evidence['final_revision']='R3'
    evidence['final_lineage_hardening']='Exact new candidate Seed bytes are sealed and bound as downstream seed_artifact. V4-09 context binds candidate Core, Factor and Seed artifacts, all distinct from accepted inputs; R2 business outputs unchanged.'
    immutable_json(ROOT/'reports/audits/A02_RPS_HISTORY_BOOTSTRAP_EVIDENCE_R3.json',evidence)
    print(json.dumps(dict(status=evidence['status'],final_revision='R3',seed_rows=len(seeds),stock_rows=len(newstock),business_diff_vs_r2=0)))
if __name__=='__main__': main()
