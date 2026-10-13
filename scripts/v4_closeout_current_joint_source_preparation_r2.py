"""Freeze current IO sources without changing active policies or Heads."""
import hashlib,json,os
from pathlib import Path
from scripts.v4_closeout_prepare_exact_daily_candidate import policy
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_sealed_preparation_v1 import KEY,source_conservation,verify
from workbench_analysis.operational_successor_v1 import validate

ROOT=Path('G:/codex work/v4-production-20261012')
DOC=Path(__file__).resolve().parents[1]/'docs/audits/v4_full_closeout_20261012/continuation_20261013/CURRENT_PUBLICATION_JOINT_AUDIT_R1'

def main():
    output=DOC/'UPDATED_CANDIDATE_SOURCE_PREPARATION_R2.json'
    if output.exists():raise ValueError('PRESERVE_EXISTING_SOURCE_PREPARATION')
    old=json.loads((DOC/'UPDATED_CANDIDATE_SOURCE_PREPARATION.json').read_bytes())
    candidate=json.loads(checked(ROOT,old['candidate']).read_bytes())
    current=policy(ROOT)
    raw=(json.dumps(current,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode('utf8')
    target=ROOT/'data/v4/exact_daily_policies_v2'/hashlib.sha256(raw).hexdigest()/'POLICY.json'
    if target.exists() and target.read_bytes()!=raw:raise ValueError('IMMUTABLE_POLICY_CONFLICT')
    if not target.exists():
        target.parent.mkdir(parents=True,exist_ok=True)
        temporary=target.with_suffix('.tmp');temporary.write_bytes(raw);os.replace(temporary,target)
    binding=ref(ROOT,target)
    receipt=json.loads(checked(ROOT,candidate[KEY]).read_bytes())
    original=json.loads(checked(ROOT,receipt['generation_policy']).read_bytes())
    receipt['consumer_algorithm_bindings']=current['accepted_algorithm_bindings']
    receipt['source_conservation']=source_conservation(ROOT,original['accepted_algorithm_bindings'],current['accepted_algorithm_bindings'])
    receipt_raw=json.dumps(receipt,sort_keys=True,separators=(',',':')).encode()
    folder=ROOT/'data/v4/sealed_numeric_preparations_v1'/hashlib.sha256(receipt_raw+binding['sha256'].encode()).hexdigest()
    receipt_path=folder/'CONSERVATION.json';atomic_json(ROOT,receipt_path,receipt)
    candidate[KEY]=ref(ROOT,receipt_path);candidate['release_policy']=binding
    candidate['accepted_algorithm_bindings']=current['accepted_algorithm_bindings']
    verify(ROOT,candidate,current);validate(ROOT,candidate)
    target_candidate=folder/'CANDIDATE.json';atomic_json(ROOT,target_candidate,candidate)
    result=dict(contract_id='V4_CURRENT_JOINT_FINAL_IO_SOURCE_PREPARATION_R2',acceptance='PASS_CONSERVED_NUMERICS_NEW_PUBLICATION_IO_ONLY',candidate=ref(ROOT,target_candidate),policy=binding,old_candidate=old['candidate'],owners_unchanged=True,numerical_producers_reexecuted=False,publication=False,algorithm_count=len(current['accepted_algorithm_bindings']),component_count=len(current['component_source_bindings']),source_conservation=receipt['source_conservation'])
    atomic_json(DOC,output,result)
    print(json.dumps({'acceptance':result['acceptance'],'candidate':result['candidate'],'algorithm_count':result['algorithm_count'],'component_count':result['component_count']}))

if __name__=='__main__':main()
