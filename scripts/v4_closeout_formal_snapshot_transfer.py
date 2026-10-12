"""Fresh formal snapshot seal with complete immutable PG table digest equality."""
import argparse,hashlib,json,os,sys,uuid
from pathlib import Path
SOURCE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(SOURCE),str(SOURCE/'src')]
ORIGIN=Path('G:/codex_tmp/v4_ui_default_r1')
TARGET=Path('G:/codex work/v4-production-20261012')
def main():
    p=argparse.ArgumentParser();p.add_argument('--descriptor',required=True);p.add_argument('--label',required=True);a=p.parse_args()
    from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
    from workbench_db.v4_snapshot_pg_r2 import Builder,read,TABLES,EXTRA_TABLES,EXTRA_FIELDS,canonical
    from workbench_service.v4_daily_refresh import atomic_bytes
    from psycopg import sql
    import psycopg
    relative=Path(a.descriptor)
    if relative.is_absolute() or '..' in relative.parts:raise ValueError('RELATIVE_DESCRIPTOR_REQUIRED')
    raw=(ORIGIN/relative).read_bytes();old=json.loads(raw)
    kind=old['content_manifest']['storage_kind']
    out=Path('G:/codex_tmp/v4_full_closeout_20261012/formal_snapshot_transfer')/a.label
    out.mkdir(parents=True,exist_ok=False)
    formal=load_credentials(TARGET/'config/native_pg_roles.dpapi')[ROLES[1]]
    with psycopg.connect(formal) as pg:
        if pg.execute('SELECT current_user,current_database(),system_identifier::text FROM pg_control_system()').fetchone()!=(ROLES[1],'market_research','7688198230782699460'):raise ValueError('FORMAL_CLUSTER_ROLE_REQUIRED')
    os.environ['V4_NATIVE_PG_DSN']='host=127.0.0.1 port=55791 user=r4_isolated_admin dbname=postgres'
    with read(old) as origin:
        os.environ['V4_NATIVE_PG_DSN']=formal
        builder=Builder(TARGET,uuid.uuid4().hex,storage_kind=kind)
        try:
            for table,columns in dict(TABLES,**{k:tuple(c[0] for c in v) for k,v in EXTRA_TABLES[kind].items()}).items():
                definitions=[sql.SQL('{} {}').format(sql.Identifier(c),sql.SQL('date' if table=='bars' and c=='day' else 'text')) for c in columns]
                builder.pg.execute(sql.SQL('CREATE TABLE {} ({})').format(sql.Identifier(table),sql.SQL(',').join(definitions)))
                with origin.pg.cursor(name='formal_transfer_'+table) as cur:
                    cur.execute(sql.SQL('SELECT {} FROM {}').format(sql.SQL(',').join(map(sql.Identifier,columns)),sql.Identifier(table)))
                    with builder.pg.cursor().copy(sql.SQL('COPY {} ({}) FROM STDIN').format(sql.Identifier(table),sql.SQL(',').join(map(sql.Identifier,columns)))) as stream:
                        for row in cur:stream.write_row(row)
                print(json.dumps(dict(table=table,stage='COPIED_NOT_SEALED')),flush=True)
            new=builder.seal(old['content_manifest']['metadata'],source_binding=old['content_manifest']['source_binding'],consumer_binding={k:old[k] for k in EXTRA_FIELDS[kind]})
            if new['content_manifest']!=old['content_manifest']:raise ValueError('COMPLETE_PG_TABLE_OR_METADATA_DIGEST_DIFFERENCE')
            builder.commit()
        finally:builder.close()
    with read(new):pass
    path=TARGET/relative
    if path.exists():raise ValueError('PRESERVE_EXISTING_FORMAL_DESCRIPTOR')
    atomic_bytes(path,canonical(new)+b'\n')
    binding=dict(path=relative.as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
    result=dict(status='FORMAL_PG_FULL_TABLE_TRANSFER_DIGEST_PASS',source_descriptor_sha256=hashlib.sha256(raw).hexdigest(),target=binding,database_identity=new['database_identity'],whole_content_manifest_difference=0,production_activated=False,authority_publication='SEPARATE_REQUIRED')
    (out/'RESULT.json').write_bytes(canonical(result));print(json.dumps(dict(status=result['status'],target=binding)))
if __name__=='__main__':main()
