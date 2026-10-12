"""Transfer complete exact period payloads to separately sealed formal PG."""
import argparse,hashlib,json,os,sys
from pathlib import Path
SOURCE=Path(__file__).resolve().parents[1];sys.path[:0]=[str(SOURCE),str(SOURCE/'src')]
ORIGIN=Path('G:/codex_tmp/v4_ui_default_r1');ROOT=Path('G:/codex work/v4-production-20261012')
def main():
    p=argparse.ArgumentParser();p.add_argument('day');a=p.parse_args();day=a.day
    from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
    from workbench_service.current_v4_context import canonical
    from workbench_service.v4_daily_refresh import atomic_bytes
    from workbench_analysis.r43_owner_replay import checked
    from workbench_service.core_product_bff_r1 import dated_product_manifest
    from workbench_db.v4_period_pg_r1 import read,prepare
    from workbench_db.v4_forward_pg_r1 import ForwardFactStore
    from workbench_db.v4_native import workspace_schema
    import psycopg
    formal=load_credentials(ROOT/'config/native_pg_roles.dpapi')[ROLES[1]]
    with psycopg.connect(formal) as pg:
        if pg.execute('SELECT current_user,current_database(),system_identifier::text FROM pg_control_system()').fetchone()!=(ROLES[1],'market_research','7688198230782699460'):raise ValueError('FORMAL_CLUSTER_ROLE_REQUIRED')
    out=Path('G:/codex_tmp/v4_full_closeout_20261012/formal_period_r1')/day;out.mkdir(parents=True,exist_ok=False)
    head=ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';before=head.read_bytes();token=hashlib.sha256(before).hexdigest()
    if (ORIGIN/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()!=before:raise ValueError('SOURCE_HEAD_DIFFERENCE')
    old=dated_product_manifest(ORIGIN,json.loads((ORIGIN/'config/core_product_read_authority_r1.json').read_bytes()),day)
    path=ROOT/'config/core_product_read_authority_r1.json';prior=path.read_bytes();authority=json.loads(prior);manifest=dated_product_manifest(ROOT,authority,day)
    bindings={};evidence=[]
    for domain,binding in old['period_owners'].items():
        os.environ['V4_NATIVE_PG_DSN']='host=127.0.0.1 port=55791 user=r4_isolated_admin dbname=postgres'
        store=ForwardFactStore.__new__(ForwardFactStore);store.root=ORIGIN;store.folder=ORIGIN/'data/v4/core_period_pg_r1';store.schema=workspace_schema(store.folder,'forward');store.dsn=os.environ['V4_NATIVE_PG_DSN'];store.database_identity=json.loads(checked(ORIGIN,binding).read_bytes())['database_identity']
        envelope=store.read(binding);rows=read(ORIGIN,binding,day,domain,token)
        payload={k:v for k,v in envelope.items() if k not in ('storage_contract','row_count','chunks','security_index')};payload['rows']=rows
        for source in payload['source_bindings'].values():checked(ROOT,source)
        os.environ['V4_NATIVE_PG_DSN']=formal
        new=prepare(ROOT,payload,token+'_'+day+'_'+domain+'_formal_r1')
        if canonical(read(ROOT,new,day,domain,token))!=canonical(rows):raise ValueError('FORMAL_PERIOD_COMPLETE_PAYLOAD_DIFFERENCE')
        bindings[domain]=new;evidence.append(dict(domain=domain,rows=len(rows),whole_payload_difference=0))
    manifest=dict(manifest,period_owners=bindings);target=ROOT/'data/v4/core_period_pg_r1/manifests'/day/'FORMAL_R1.json';atomic_bytes(target,canonical(manifest))
    if head.read_bytes()!=before or path.read_bytes()!=prior:raise ValueError('FORMAL_PERIOD_CAS_SOURCE_CHANGED')
    authority['dates'][day]=dict(path=target.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size);atomic_bytes(path,canonical(authority))
    (out/'RESULT.json').write_bytes(canonical(dict(status='FORMAL_PERIOD_COMPLETE_TRANSFER_READBACK_PASS',day=day,domains=evidence,head_unchanged=True,production_activated=False,numeric_oracle='SEPARATE_REQUIRED')));print('FORMAL_PERIOD_COMPLETE_TRANSFER_READBACK_PASS')
if __name__=='__main__':main()
