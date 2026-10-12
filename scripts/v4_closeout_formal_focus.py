"""Build fresh formal PG Focus authority from the complete frozen projection."""
import hashlib,json,os,sys
from pathlib import Path
SOURCE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(SOURCE),str(SOURCE/'src')]
ROOT=Path('G:/codex work/v4-production-20261012')
OUT=Path('G:/codex_tmp/v4_full_closeout_20261012/formal_focus_r1')
def main():
    from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
    from workbench_db.v4_focus_projection_pg_closeout import build,read
    from workbench_service.current_v4_context import canonical
    from workbench_service.v4_daily_refresh import atomic_bytes
    import psycopg
    os.environ['V4_NATIVE_PG_DSN']=load_credentials(ROOT/'config/native_pg_roles.dpapi')[ROLES[1]]
    with psycopg.connect(os.environ['V4_NATIVE_PG_DSN']) as pg:
        if pg.execute('SELECT current_user,current_database(),system_identifier::text FROM pg_control_system()').fetchone()!=(ROLES[1],'market_research','7688198230782699460'):raise ValueError('FORMAL_CLUSTER_ROLE_REQUIRED')
    OUT.mkdir(parents=True,exist_ok=False)
    def ref(path):
        raw=path.read_bytes();return dict(path=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    head=ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';before=head.read_bytes();token=hashlib.sha256(before).hexdigest()
    authority=ROOT/'config/core_product_focus_read_authority_r2.json';prior=authority.read_bytes()
    old=json.loads((ROOT/json.loads(prior)['manifest']['path']).read_bytes())
    if old['head']['sha256']!=token:raise ValueError('FORMAL_FOCUS_HEAD_MISMATCH')
    source=ref(ROOT/'data/v4/closeout_focus_source/FOCUS.json.gz')
    binding,oracle=build(ROOT,source,t0='2026-10-09',head_token=token)
    projection=read(ROOT,binding,t0='2026-10-09',head_token=token)
    manifest=dict(old,projection=binding,formal_database_identity=dict(database='market_research',system_identifier='7688198230782699460'))
    path=ROOT/'data/v4/focus_pg_projection_closeout'/binding['sha256']/'FORMAL_READ_MANIFEST.json'
    atomic_bytes(path,canonical(manifest))
    if head.read_bytes()!=before or authority.read_bytes()!=prior:raise ValueError('FORMAL_SOURCE_CHANGED')
    atomic_bytes(authority,canonical(dict(contract_id='CORE_PRODUCT_FOCUS_READ_AUTHORITY_R3_NATIVE_PG',manifest=ref(path))))
    result=dict(status='FORMAL_PG_COMPLETE_FOCUS_READBACK_PASS',oracle=oracle,binding=binding,episodes=len(projection['episodes']),head_unchanged=True,production_activated=False)
    (OUT/'RESULT.json').write_bytes(canonical(result));print(json.dumps(dict(status=result['status'],episodes=result['episodes'])))
if __name__=='__main__':main()
