"""Candidate-only real source build, whole PG readback, then authority binding."""
import argparse, gzip, hashlib, importlib.util, json, os, sys
from pathlib import Path

SOURCE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(SOURCE/'src'),str(SOURCE)]

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--evidence',required=True);p.add_argument('--trade-date');p.add_argument('--formal-roles');a=p.parse_args()
    root=Path(a.root).resolve();out=Path(a.evidence).resolve()
    if root.drive.upper()!='G:' or out.drive.upper()!='G:' or root==Path('G:/codex work/大A交易').resolve():raise ValueError('ISOLATED_G_CANDIDATE_REQUIRED')
    out.mkdir(parents=True,exist_ok=True)
    if a.formal_roles:
        if root!=Path('G:/codex work/v4-production-20261012').resolve() or Path(a.formal_roles).resolve()!=root/'config/native_pg_roles.dpapi':raise ValueError('FORMAL_STAGING_ROLE_REQUIRED')
        from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
        os.environ['V4_NATIVE_PG_DSN']=load_credentials(a.formal_roles)[ROLES[1]]
    from workbench_db.v4_native import connection, configured_dsn
    import psycopg
    with psycopg.connect(configured_dsn()) as pg:
        identity=pg.execute("select current_database(),(pg_control_system()).system_identifier,NULL::text" if a.formal_roles else "select current_database(),(pg_control_system()).system_identifier,current_setting('data_directory')").fetchone()
    if a.formal_roles:
        if identity[0]!='market_research' or str(identity[1])!='7688198230782699460':raise ValueError('FORMAL_DATABASE_REQUIRED')
        with psycopg.connect(configured_dsn()) as pg:
            if pg.execute('SELECT current_user').fetchone()[0]!=ROLES[1]:raise ValueError('FORMAL_PRODUCER_REQUIRED')
    elif str(identity[1])!='7695278778933357404' or identity[2].replace('\\','/').lower()!='g:/codex_tmp/full_system_r4_fbd23a6b/pg_data':raise ValueError('ISOLATED_DATABASE_REQUIRED')
    protected=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';before=protected.read_bytes()
    authority=root/'config/core_product_read_authority_r1.json'
    if authority.exists():(out/'BEFORE_AUTHORITY.json').write_bytes(authority.read_bytes())
    spec=importlib.util.spec_from_file_location('actual_builder',SOURCE/'scripts/build_core_product_read_pack_r1.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.ROOT=root;sys.argv=['build_core_product_read_pack_r1.py']+(['--trade-date',a.trade_date] if a.trade_date else []);module.main()
    token=hashlib.sha256(before).hexdigest();manifest_path=root/'data/v4/core_product_read_pg_r1'/token/'MANIFEST.json'
    if a.trade_date:manifest_path=manifest_path.parent/a.trade_date/'MANIFEST.json'
    manifest=json.loads(manifest_path.read_bytes());binding=manifest['history_index']
    from workbench_analysis.r43_owner_replay import checked,ref
    from workbench_db.v4_history_pg_r1 import canonical,read
    expected={}
    with gzip.open(checked(root,manifest['source_bindings']['history']),'rt',encoding='utf8') as stream:
        for line in stream:
            r=json.loads(line);expected[r['security_id']]=(hashlib.sha256(canonical(r['bars'])).hexdigest(),len(r['bars']))
    count=bars=0;diffs=[];samples=[]
    with connection(binding['schema'],read_only=True) as pg:
        with pg.cursor(name='core_product_whole_source_oracle') as cur:
            cur.execute('select security,payload from history where version=%s order by security',(binding['version'],))
            for sid,series in cur:
                count+=1;bars+=len(series)
                if expected.get(sid)!=(hashlib.sha256(canonical(series)).hexdigest(),len(series)):diffs.append(sid)
                if any(b['trade_date']>manifest['T0'] for b in series):diffs.append('FUTURE:'+sid)
                if len(samples)<3:samples.append((sid,series))
    if diffs or count!=len(expected) or bars!=binding['bar_count']:raise ValueError('WHOLE_SOURCE_ORACLE_FAILED')
    for sid,series in samples:
        if read(root,binding,manifest['T0'],sid)!=series:raise ValueError('REAL_READER_FAILED')
    if protected.read_bytes()!=before:raise ValueError('PROTECTED_HEAD_CHANGED')
    from workbench_db.v4_market_fact_pg_r1 import prepare,read as read_market
    original_facts=json.loads(checked(root,manifest['market_facts']).read_bytes())
    pg_market=prepare(root,original_facts,token+':'+manifest['T0'])
    if read_market(root,pg_market,manifest['T0'])!=original_facts:raise ValueError('WHOLE_MARKET_PG_ORACLE_FAILED')
    manifest['market_facts']=pg_market;manifest['contract_id']='CORE_PRODUCT_DATED_READ_PACK_PG_MARKET_R2'
    manifest['authority_scope']='ISOLATED_ENGINEERING_ONLY';module.atomic_json(root,manifest_path,manifest)
    dates={}
    if authority.exists():
        old=json.loads(authority.read_bytes())
        if old['contract_id']=='CORE_PRODUCT_READ_AUTHORITY_R2':dates.update(old['dates'])
        else:
            old_manifest=json.loads(checked(root,old['manifest']).read_bytes());dates[old_manifest['T0']]=old['manifest']
    dates[manifest['T0']]=ref(root,manifest_path)
    module.atomic_json(root,authority,dict(contract_id='CORE_PRODUCT_READ_AUTHORITY_R2',dates=dates))
    result=dict(contract_id='CORE_PRODUCT_PG_SOURCE_MIGRATION_CLOSEOUT_R1',status='CANDIDATE_WHOLE_SOURCE_READBACK_PASS',database_identity=dict(database=identity[0],system_identifier=str(identity[1]),data_directory=identity[2]),T0=manifest['T0'],head_token=token,symbols=count,bars=bars,differences=diffs,manifest=ref(root,manifest_path),production_changed=False,external_acceptance='NOT_GRANTED',builder_sha256=hashlib.sha256((SOURCE/'scripts/build_core_product_read_pack_r1.py').read_bytes()).hexdigest())
    (out/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result),flush=True)

if __name__=='__main__':main()
