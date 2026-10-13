"""Prepare additive PG/read models for a bounded target-Market correction."""
import json,os,sys,time,hashlib
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]

def main():
    root=Path('G:/codex work/v4-production-20261012')
    from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
    credentials=load_credentials(root/'config/native_pg_roles.dpapi')
    os.environ.update(V4_NATIVE_PG_DSN=credentials[ROLES[1]],V4_NATIVE_PG_READER_DSN=credentials[ROLES[0]])
    from workbench_analysis.r43_owner_replay import load,ref,checked
    from workbench_analysis.operational_daily_storage_v1 import atomic_json
    from workbench_db.v4_native import workspace_schema
    import psycopg
    folder=root/load(root/'runtime/r1_1/PG_CANDIDATE_QA.json')['candidate']['path']
    original_binding=ref(root,folder);original=load(checked(root,original_binding));candidate=deepcopy(original)
    generation=checked(root,original['exact_daily_generation_scope']).parent
    result_path=next(generation.glob('market_context_patch_r1_1/*/RESULT.json'))
    result=load(result_path)
    if result['acceptance']!='PASS' or result['compute_sessions']!=['2026-10-13']:raise ValueError('BOUNDED_MARKET_QA_REQUIRED')
    checked(root,result['market_binding']);out=result_path.parent/'candidate_read_preparation';day='2026-10-13'
    head=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';before=head.read_bytes();started=time.monotonic()
    candidate['owners'][day]['market']=result['market_binding']
    receipt=load(checked(root,original['day_receipt']));receipt['owners']=candidate['owners'][day]
    receipt['bounded_market_correction']=ref(root,result_path)
    atomic_json(root,out/'DAY_RECEIPT.json',receipt);candidate['day_receipt']=ref(root,out/'DAY_RECEIPT.json')
    registry=load(checked(root,original['registry']));registry['owner_bindings']=candidate['owners']
    registry['bounded_market_correction']=ref(root,result_path)
    atomic_json(root,out/'BUILDER_REGISTRY.json',registry);candidate['registry']=ref(root,out/'BUILDER_REGISTRY.json')
    key=int.from_bytes(hashlib.sha256(workspace_schema(root,'jobs').encode()).digest()[:8],'big',signed=True)^1
    with psycopg.connect(credentials[ROLES[1]],autocommit=True) as lock:
        if not lock.execute('SELECT pg_try_advisory_lock(%s)',(key,)).fetchone()[0]:raise ValueError('DAILY_WRITER_ALREADY_ACTIVE')
        try:
            from workbench_db.v4_operational_owner_authority_v2 import prepare_successor
            pg=prepare_successor(root,candidate)
            from workbench_db.v4_membership_reference_pg_v1 import prepare,prepare_identity,prepare_search_identity
            membership=prepare(root,candidate);membership.update(identity=prepare_identity(root,candidate),search_identity=prepare_search_identity(root,candidate))
            from workbench_analysis.operational_product_pack_v3 import prepare as prepare_pack
            core=next(r for r in load(generation/'owner_v3/CORE_REPLAY.json')['owners'] if r['trade_date']==day)
            pack=prepare_pack(root,candidate,core)
            from workbench_db.v4_read_index_r1 import prepare_bff
            index=prepare_bff(root,candidate)
            from workbench_analysis.operational_successor_v1 import validate
            validate(root,candidate)
            atomic_json(root,out/'CORRECTED_PG_CANDIDATE.json',candidate)
            atomic_json(root,out/'PG_PREPARATION.json',dict(acceptance='PASS',original_candidate=original_binding,
                corrected_candidate=ref(root,out/'CORRECTED_PG_CANDIDATE.json'),market_correction=ref(root,result_path),
                pg=pg,membership=membership,pack=pack,index=index,seconds=time.monotonic()-started,
                head_unchanged=head.read_bytes()==before,published=False))
            print(json.dumps(dict(candidate=ref(root,out/'CORRECTED_PG_CANDIDATE.json'),seconds=time.monotonic()-started)))
        finally:lock.execute('SELECT pg_advisory_unlock(%s)',(key,))
    if head.read_bytes()!=before:raise ValueError('FORMAL_HEAD_CHANGED')

if __name__=='__main__':main()
