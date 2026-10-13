"""Additive staged R1.1 metadata admission; no canonical policy or Head writes."""
import argparse,json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_runtime_acceptance_r1_1 import KEY,CONTRACT,source_conservation,verify as verify_metadata


def save(root,folder,name,value):
    path=folder/name
    if path.exists():
        if json.loads(path.read_bytes())!=value:raise ValueError('IMMUTABLE_ADMISSION_ARTIFACT_CONFLICT:'+name)
    else:atomic_json(root,path,value)
    return ref(root,path)


def policy_archive(root,policy):
    raw=json.dumps(policy,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    path=root/'data/v4/exact_daily_policies_v2'/hashlib.sha256(raw).hexdigest()/'POLICY.json'
    if path.exists() and path.read_bytes()!=raw:raise ValueError('IMMUTABLE_POLICY_CONFLICT')
    if not path.exists():
        from workbench_analysis.tdx_official_daily_source import _atomic_write
        _atomic_write(path,raw,tdx_root=Path('D:/new_tdx'))
    return ref(root,path)


def main():
    p=argparse.ArgumentParser();p.add_argument('--step',choices=['prepare','finalize'],required=True);p.add_argument('--root',required=True);p.add_argument('--generation-candidate',required=True);p.add_argument('--generation-g123',required=True);p.add_argument('--pending-policy',required=True);p.add_argument('--revision-check',required=True);p.add_argument('--out',required=True);p.add_argument('--shadow-root');a=p.parse_args()
    root=Path(a.root).resolve();folder=Path(a.out).resolve()
    if root.drive.upper()!='G:' or not folder.is_relative_to(root/'data/v4'):raise ValueError('ADDITIVE_G_DATA_OUTPUT_REQUIRED')
    def read_bound(path):
        path=Path(path).resolve();binding=ref(root,path)
        return json.loads(checked(root,binding).read_bytes()),binding
    original,original_binding=read_bound(a.generation_candidate)
    generation_report,generation_report_binding=read_bound(a.generation_g123)
    pending,pending_binding=read_bound(a.pending_policy)
    revision,revision_binding=read_bound(a.revision_check)
    old=json.loads(checked(root,original['release_policy']).read_bytes())
    changes=source_conservation(root,old,pending,candidate=original)
    if original['accepted_algorithm_bindings']!=old['accepted_algorithm_bindings']:raise ValueError('GENERATION_BINDINGS_MISMATCH')
    if generation_report.get('scope')!='FULL_ALL_DOMAIN' or generation_report.get('candidate_binding')!=original_binding or generation_report.get('accepted_algorithm_bindings')!=old['accepted_algorithm_bindings']:raise ValueError('GENERATION_FULL_GATE_BINDINGS_REQUIRED')
    if generation_report.get('target_trade_date')!=original['accepted_trade_date'] or any(generation_report.get('counts',{}).get(k)!=v for k,v in {'stocks':5225,'sectors':400}.items()):raise ValueError('GENERATION_FULL_COUNTS_REQUIRED')
    for g in ('G1','G2','G3'):
        if generation_report.get(g,{}).get('status')!='PASS':raise ValueError('GENERATION_GATE_FAILED:'+g)
    if revision.get('acceptance')!='PASS' or revision.get('mode')!='APPEND_DAY' or revision.get('revisions'):raise ValueError('REVISION_GATE_FAILED')
    receipt=dict(contract_id=CONTRACT,acceptance='PASS_METADATA_ONLY',generation_candidate=original_binding,generation_g123=generation_report_binding,changed_io_modules=changes,runtime_bindings=pending['accepted_algorithm_bindings'])
    receipt_binding=save(root,folder,'METADATA_CONSERVATION.json',receipt)
    candidate=dict(original,release_policy=pending_binding,accepted_algorithm_bindings=pending['accepted_algorithm_bindings'],**{KEY:receipt_binding})
    verify_metadata(root,candidate,pending)
    candidate_binding=save(root,folder,'PENDING_RUNTIME_CANDIDATE.json',candidate)
    g123=dict(contract_id='V4_R1_1_DUAL_REFERENCE_SEMANTIC_AND_IDENTITY_PARITY',scope='FULL_ALL_DOMAIN',target_trade_date=candidate['accepted_trade_date'],counts=generation_report['counts'],candidate_binding=candidate_binding,accepted_algorithm_bindings=pending['accepted_algorithm_bindings'],generation_receipt=generation_report_binding,metadata_conservation=receipt_binding,**{g:dict(status='PASS',basis='GENERATION_FULL_GATE_PLUS_EXACT_METADATA_SOURCE_CONSERVATION') for g in ('G1','G2','G3')})
    g123_binding=save(root,folder,'PENDING_RUNTIME_G123.json',g123)
    if a.step=='prepare':print(json.dumps(dict(status='RUNTIME_METADATA_PREPARED_NOT_ADMITTED',candidate=candidate_binding,g123=g123_binding)));return
    shadow=Path(a.shadow_root or '').resolve()
    if not shadow.is_relative_to(Path('G:/codex_tmp').resolve()):raise ValueError('SHADOW_G4_REQUIRED')
    result=json.loads((shadow/'success_RESULT.json').read_bytes());transaction=json.loads((shadow/'runtime/dynamic_daily/publication_transaction.json').read_bytes())
    failure=json.loads((shadow/'failure_RESULT.json').read_bytes())
    if failure.get('status')!='ENGINEERING_SHADOW_FAILURE_ROLLBACK_PASS' or failure.get('formal_pointers_unchanged') is not True:
        raise ValueError('REAL_SHADOW_FAILURE_ROLLBACK_REQUIRED')
    from workbench_analysis.operational_successor_v1 import digest
    if result.get('status')!='ENGINEERING_SHADOW_PUBLISHED' or result.get('formal_pointers_unchanged') is not True or transaction.get('state')!='COMMITTED' or transaction.get('head_sha256')!=digest(candidate):raise ValueError('REAL_SHADOW_G4_REQUIRED')
    checks=transaction.get('readback',{}).get('checks',[])
    required={'/api/v4/context','/api/v4/stocks','/api/v4/sectors','/api/v4/focus','/api/v4/home','/api/v4/market','/api/v4/stocks/SZ.301660/chart'}
    if {r.get('path') for r in checks}!=required or any(r.get('status')!='PASS' for r in checks):raise ValueError('G4_SEVEN_REAL_HTTP_REQUIRED')
    raw_g4=save(root,folder,'ACTUAL_SHADOW_G4.json',dict(result=result,transaction=transaction,failure_rollback=failure))
    gates={}
    for gate in ('G1','G2','G3','G4'):
        gates[gate]=save(root,folder,gate+'_RUNTIME_GATE.json',dict(contract_id='V4_R1_1_RUNTIME_GATE_CONSERVATION',gate=gate,acceptance='PASS',unexplained_differences=0,accepted_algorithm_bindings=pending['accepted_algorithm_bindings'],generation_receipt=generation_report_binding,metadata_conservation=receipt_binding,actual_shadow_g4=raw_g4 if gate=='G4' else None))
    evidence=save(root,folder,'RUNTIME_ACCEPTANCE.json',dict(contract_id='V4_RUNTIME_REPAIR_ACCEPTANCE_R1_1',acceptance='PASS',accepted_algorithm_bindings=pending['accepted_algorithm_bindings'],component_source_bindings=pending['component_source_bindings'],gates=gates,revision_check=revision_binding))
    final=dict(pending,publication_ready=True,status='PASS_R1_1_RUNTIME_GATES',admission_evidence=evidence)
    final_binding=policy_archive(root,final)
    final_candidate=dict(candidate,release_policy=final_binding)
    verify_metadata(root,final_candidate,final)
    final_candidate_binding=save(root,folder,'FINAL_RUNTIME_CANDIDATE.json',final_candidate)
    from workbench_analysis.operational_successor_release_v1 import verify_policy
    verify_policy(root,final_candidate,verify_loaded=False)
    print(json.dumps(dict(status='STAGED_RUNTIME_ADMITTED_NOT_ACTIVATED',policy=final_binding,candidate=final_candidate_binding,canonical_policy_changed=False,formal_head_changed=False)))

if __name__=='__main__':main()
