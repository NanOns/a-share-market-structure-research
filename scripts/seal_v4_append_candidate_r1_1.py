"""Resume exact completed APPEND artifacts, prepare PG, never publish Head."""
import json,os,sys,time,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]

def main():
    root=Path('G:/codex work/v4-production-20261012')
    from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
    credentials=load_credentials(root/'config/native_pg_roles.dpapi')
    os.environ['V4_NATIVE_PG_DSN']=credentials[ROLES[1]];os.environ['V4_NATIVE_PG_READER_DSN']=credentials[ROLES[0]]
    from workbench_analysis.r43_owner_replay import checked,load,ref
    from workbench_analysis.operational_new_listing_r1 import ready_build
    from workbench_analysis.operational_daily_ready_owner_v2 import seal
    from workbench_analysis.operational_daily_storage_v1 import atomic_json
    from workbench_db.v4_native import workspace_schema
    import psycopg
    head=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';before=head.read_bytes()
    run=load(root/'runtime/r1_1/FULL_APPEND_RUN.json')
    if run['acceptance']!='DERIVED_NOT_SEALED':raise ValueError('COMPLETE_DERIVATION_REQUIRED')
    folder=Path(run['output']);generation=load(folder/'GENERATION_SCOPE.json')
    policy=generation['adjustment_contract']['policy']
    gate_path=next(p for p in (root/'data/v4/dynamic_daily_sources/source_readiness/2026-10-13').glob('*.json')
        if load(p).get('source_ready') and load(p).get('source_freeze',{}).get('sha256')==generation['source_freeze']
        and load(p).get('dependency_bindings',{}).get('new_listing_identity'))
    gate=load(gate_path);started=time.monotonic()
    key=int.from_bytes(hashlib.sha256(workspace_schema(root,'jobs').encode()).digest()[:8],'big',signed=True)^1
    with psycopg.connect(credentials[ROLES[1]],autocommit=True) as lock:
        if not lock.execute('SELECT pg_try_advisory_lock(%s)',(key,)).fetchone()[0]:raise ValueError('DAILY_WRITER_ALREADY_ACTIVE')
        try:
            if '--resume-sealed' in sys.argv:
                candidate=load(folder/'SUCCESSOR_CANDIDATE.json')
                if candidate['exact_daily_generation_scope']!=ref(root,folder/'GENERATION_SCOPE.json'):
                    raise ValueError('SEALED_GENERATION_BINDING_CHANGED')
                context=dict(folder=folder,compute_dates=['2026-10-13'])
            else:
                produced,context=ready_build(root,gate['source_freeze'],source_readiness=ref(root,gate_path),
                    candidate_only_exact=True,exact_policy_binding=policy)
                if context['folder'].resolve()!=folder.resolve():raise ValueError('EXACT_RESUME_GENERATION_CHANGED')
                candidate,binding=seal(root,context)
            from scripts import audit_dynamic_daily_period_numbers_v1 as period_module
            from workbench_analysis.operational_owner_adapter_v1 import private_scope
            raw=Path(period_module.__file__).read_bytes()
            archive=folder/'executed_verifiers'/hashlib.sha256(raw).hexdigest()/'audit_dynamic_daily_period_numbers_v1.py'
            if not archive.exists():
                archive.parent.mkdir(parents=True,exist_ok=True);archive.write_bytes(raw)
            qa=private_scope(period_module,dict(__file__=str(archive)))['audit'](root,folder)
            if qa['acceptance']!='PASS':raise ValueError('FULL_PERIOD_NUMERIC_ORACLE_FAILED')
            candidate['period_numeric_oracle']=ref(root,folder/'PERIOD_NUMERIC_ORACLE.json')
            from workbench_analysis.operational_product_pack_v3 import prepare
            core_owner=next(r for r in load(folder/'owner_v3/CORE_REPLAY.json')['owners'] if r['trade_date']=='2026-10-13')
            pack=prepare(root,candidate,core_owner)
            atomic_json(root,folder/'R1_1_PRODUCT_PACK.json',pack)
            path=folder/'R1_1_PG_CANDIDATE.json';atomic_json(root,path,candidate)
            from workbench_db.v4_read_index_r1 import prepare_bff
            index=prepare_bff(root,candidate)
            from workbench_analysis.operational_successor_v1 import validate
            validate(root,candidate)
            receipt=dict(contract_id='V4_R1_1_APPEND_CANDIDATE_PG_QA',acceptance='PASS_CANDIDATE_ONLY',
                candidate=ref(root,path),period_qa=ref(root,folder/'PERIOD_NUMERIC_ORACLE.json'),
                source_policy=policy,read_index=index,seconds=time.monotonic()-started,
                compute_sessions=context['compute_dates'],published=False,head_unchanged=head.read_bytes()==before)
            atomic_json(root,root/'runtime/r1_1/PG_CANDIDATE_QA.json',receipt)
            print(json.dumps({k:v for k,v in receipt.items() if k!='read_index'}),flush=True)
        finally:lock.execute('SELECT pg_advisory_unlock(%s)',(key,))
    if head.read_bytes()!=before:raise ValueError('FORMAL_HEAD_CHANGED')

if __name__=='__main__':main()
