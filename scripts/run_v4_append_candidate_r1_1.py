"""Isolated genuine full APPEND candidate; no seal, CAS or Head mutation."""
import argparse,hashlib,json,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--exact-policy-path');args=parser.parse_args()
    root=Path(args.root).resolve()
    if not root.is_relative_to(Path('G:/codex_tmp').resolve()) and not (root==Path('G:/codex work/v4-production-20261012').resolve() and args.exact_policy_path):raise ValueError('ISOLATED_OR_EXPLICIT_STAGED_CANDIDATE_REQUIRED')
    from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
    from workbench_analysis.r43_owner_replay import load,ref,checked
    from workbench_analysis.operational_new_listing_r1 import ready_build
    from workbench_db import v4_series_pg_r1 as series
    from workbench_db.v4_snapshot_pg_r2 import grant_verifier
    from psycopg import connect
    from workbench_db.v4_native import workspace_schema
    credentials=load_credentials('G:/codex work/v4-production-20261012/config/native_pg_roles.dpapi')
    os.environ.update(V4_NATIVE_PG_DSN=credentials[ROLES[1]],V4_NATIVE_PG_READER_DSN=credentials[ROLES[0]])
    # Source capture is explicitly disabled: a missing frozen dependency fails.
    from workbench_analysis.operational_baostock_client_v1 import BaoStockClient
    def forbidden_query(*a,**kw):raise ValueError('FIXED_INPUT_RUN_NETWORK_FORBIDDEN')
    BaoStockClient.query_rows=forbidden_query
    original=series.build
    def build(root,path,rows,**kwargs):
        descriptor=original(root,path,rows,**kwargs)
        with connect(credentials[ROLES[1]],connect_timeout=5) as pg:
            grant_verifier(pg,descriptor['schema'],ROLES[0],tables=('objects','aliases','members','metadata','bars','snapshot_identity'))
        return descriptor
    series.build=build
    gates=[]
    for path in (root/'data/v4/dynamic_daily_sources/source_readiness/2026-10-13').glob('*.json'):
        doc=load(path)
        if doc.get('source_ready') and doc.get('dependency_bindings',{}).get('new_listing_identity'):gates.append((path,doc))
    if not gates:raise ValueError('FROZEN_ADMITTED_GATE_REQUIRED')
    path,gate=max(gates,key=lambda item:item[0].stat().st_mtime_ns)
    checked(root,gate['source_freeze']);head_path=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';before=head_path.read_bytes()
    started=time.monotonic();stages=[]
    # Same session advisory key as the real DailyJobs worker, without creating
    # or ticking a scheduler and without mutating any production job row.
    lock_connection=connect(credentials[ROLES[1]],autocommit=True,connect_timeout=5)
    schema=workspace_schema(root,'jobs');lock_key=int.from_bytes(hashlib.sha256(schema.encode()).digest()[:8],'big',signed=True)^1
    if not lock_connection.execute('SELECT pg_try_advisory_lock(%s)',(lock_key,)).fetchone()[0]:
        lock_connection.close();raise ValueError('DAILY_WRITER_ALREADY_ACTIVE')
    def progress(day,stage,detail):
        if detail.get('stage_state') in ('RUNNING','COMPLETED') and 'processed' not in detail:
            stages.append(dict(stage=stage,elapsed_seconds=round(time.monotonic()-started,3),**detail));print(json.dumps(stages[-1]),flush=True)
    try:
        extra={}
        if args.exact_policy_path:extra['exact_policy_binding']=ref(root,root/args.exact_policy_path)
        produced,context=ready_build(root,gate['source_freeze'],source_readiness=ref(root,path),candidate_only_exact=True,progress=progress,**extra)
        result=dict(contract_id='V4_R1_1_FULL_APPEND_ENGINEERING_RUN',acceptance='DERIVED_NOT_SEALED',
            output=str(context['folder']),compute_sessions=context['compute_dates'],mode=context['increment_plan']['mode'],
            elapsed_seconds=round(time.monotonic()-started,3),stages=stages,production_publication=False)
    except Exception as exc:
        result=dict(contract_id='V4_R1_1_FULL_APPEND_ENGINEERING_RUN',acceptance='BLOCKED',error_type=type(exc).__name__,error=str(exc),
            elapsed_seconds=round(time.monotonic()-started,3),stages=stages,production_publication=False)
    finally:
        lock_connection.execute('SELECT pg_advisory_unlock(%s)',(lock_key,));lock_connection.close()
    if head_path.read_bytes()!=before:raise ValueError('ISOLATED_HEAD_CHANGED_WITHOUT_SEAL')
    result['head_unchanged']=True
    path=root/'runtime/r1_1/FULL_APPEND_RUN.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
