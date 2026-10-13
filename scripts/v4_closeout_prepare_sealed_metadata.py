"""Conserve sealed generation while binding current post-generation consumers."""
import json
from pathlib import Path
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_daily_exact_policy_v2 import immutable_policy_binding,PATH
from workbench_analysis.operational_sealed_preparation_v1 import CONTRACT,KEY,source_conservation,verify
from workbench_analysis.operational_successor_v1 import validate

ROOT=Path('G:/codex work/v4-production-20261012');OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--label',default='R1');parser.add_argument('--native-research',action='store_true');parser.add_argument('--native-profile-corrections',action='store_true');args=parser.parse_args()
    if not args.label.isalnum():raise ValueError('VERSIONED_PREPARATION_REQUIRED')
    report=OUT/('SEALED_METADATA_CONSERVATION_R6_'+args.label+'.json')
    if report.exists():raise ValueError('PRESERVE_PRIOR_SEALED_METADATA_PREPARATION')
    source=json.loads((OUT/'SEALED_NATIVE_OWNER_R6.json').read_bytes())['source_candidate']
    sealed=json.loads(checked(ROOT,source).read_bytes())
    previous_report='COMPONENT_SOURCE_CONSERVATION_R6_R1.json' if args.native_profile_corrections else 'NATIVE_RESEARCH_REFERENCE_PREPARATION_R6_R1.json' if args.native_research else 'NATIVE_SEARCH_IDENTITY_PREPARATION_R6.json'
    previous=json.loads((OUT/previous_report).read_bytes())['candidate']
    candidate=json.loads(checked(ROOT,previous).read_bytes())
    generation_policy=dict(sealed['release_policy'],path='data/v4/exact_daily_policies_v2/'+sealed['release_policy']['sha256']+'/POLICY.json')
    original=json.loads(checked(ROOT,generation_policy).read_bytes())
    binding=immutable_policy_binding(ROOT);current=json.loads(checked(ROOT,binding).read_bytes())
    receipt=dict(contract_id=CONTRACT,acceptance='PASS_METADATA_CONSERVATION_ONLY',sealed_candidate=source,
        generation_policy=generation_policy,consumer_algorithm_bindings=current['accepted_algorithm_bindings'],
        source_conservation=source_conservation(ROOT,original['accepted_algorithm_bindings'],current['accepted_algorithm_bindings']),
        numerical_producers_reexecuted=False,publication=False)
    from workbench_db.v4_forward_pg_r1 import digest,canonical
    folder=ROOT/'data/v4/sealed_numeric_preparations_v1'/digest(canonical(receipt));path=folder/'CONSERVATION.json';atomic_json(ROOT,path,receipt)
    candidate[KEY]=ref(ROOT,path);candidate['accepted_algorithm_bindings']=current['accepted_algorithm_bindings'];candidate['release_policy']=binding
    verify(ROOT,candidate,current);validate(ROOT,candidate)
    prepared=folder/'CANDIDATE.json';atomic_json(ROOT,prepared,candidate)
    result=dict(contract_id=CONTRACT,acceptance=receipt['acceptance'],candidate=ref(ROOT,prepared),receipt=ref(ROOT,path),
        numeric_generation_policy=generation_policy,consumer_policy=binding,numerical_producers_reexecuted=False,
        publication=False,admission='PENDING_FOUR_REAL_GATES')
    if args.native_profile_corrections:result['bounded_profile_correction_admission']='PASS_SEPARATE_COMPONENT_SOURCE_CONSERVATION_NOT_METADATA_ONLY_MATH'
    atomic_json(OUT,report,result);print(json.dumps(dict(acceptance=result['acceptance'],publication=False)),flush=True)

if __name__=='__main__':main()
