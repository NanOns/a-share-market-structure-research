"""Bind the exact admitted candidate to a staged CATCH_UP resume manifest."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    root=a.root.resolve();out=a.out.resolve()
    if root.drive.upper()!='G:' or not out.is_relative_to(root/'data/v4'):raise ValueError('ADDITIVE_G_MANIFEST_REQUIRED')
    from workbench_analysis.r43_owner_replay import checked,ref,load
    from workbench_analysis.operational_daily_storage_v1 import atomic_json
    candidate=load(a.candidate);cb=ref(root,a.candidate)
    policy=load(checked(root,candidate['release_policy']));acceptance=load(checked(root,policy['admission_evidence']))
    generation=load(checked(root,candidate['exact_daily_generation_scope']));receipt=load(checked(root,candidate['day_receipt']))
    gates={key:acceptance['gates'][key] for key in ('G1','G2','G3')};gates['G4_PREPUBLICATION']=acceptance['gates']['G4']
    attestation=dict(contract_id='SEALED_RESUME_GATE_ATTESTATION_R1',acceptance='PASS',target_session=candidate['accepted_trade_date'],candidate=cb,generation=candidate['exact_daily_generation_scope'],source_freeze=receipt['source_freeze'],predecessor=candidate['predecessor'],gates=gates)
    atomic_json(root,out/'GATE_ATTESTATION.json',attestation)
    verifier=list(checked(root,candidate['exact_daily_generation_scope']).parent.glob('executed_verifiers/*/audit_dynamic_daily_period_numbers_v1.py'))
    if len(verifier)!=1:raise ValueError('EXACT_PERIOD_VERIFIER_REQUIRED')
    manifest=dict(contract_id='SEALED_CANDIDATE_RESUME_R1',target_session=candidate['accepted_trade_date'],allowed_modes=['CATCH_UP'],candidate=cb,predecessor=candidate['predecessor'],generation=candidate['exact_daily_generation_scope'],source_freeze=receipt['source_freeze'],source_readiness=receipt['source_readiness'],generation_policy=generation['adjustment_contract']['policy'],runtime_policy=candidate['release_policy'],period_verifier=ref(root,verifier[0]),gate_attestation=ref(root,out/'GATE_ATTESTATION.json'),gates=gates)
    from workbench_analysis.operational_sealed_resume_r1 import verify
    verify(root,manifest)
    atomic_json(root,out/'MANIFEST.json',manifest)
    pointer=dict(target_session=candidate['accepted_trade_date'],allowed_modes=['CATCH_UP'],manifest=ref(root,out/'MANIFEST.json'))
    atomic_json(root,out/'POINTER_STAGED.json',pointer)
    print(json.dumps(dict(acceptance='PASS_STAGED_NOT_INSTALLED',manifest=pointer['manifest'])))

if __name__=='__main__':main()
