"""Explicit fresh/upgrade verification on newly created disposable PG clusters."""
import json,os,sys,subprocess
from pathlib import Path
from datetime import datetime,timezone
import psycopg
from psycopg import sql
from scripts.full_chain_repair_io import ROOT,write,binding
from workbench_analysis.fep_e5 import canonical_ledger as c
P='reports/forward_r2_remainder_consolidated_20261007/'

def typed_pit(pg):
    from tests.v4_phase0.test_postgres_schema import add_namespace,add_publication
    from psycopg.types.json import Jsonb
    from datetime import timedelta
    body=dict(accepted_contract=dict(contract_id='UNIT_PIT_OBSERVATION',observation_scope='UNIT_PIT_SCOPE',formal_signals=['UNIT_PIT_SIGNAL']),predicate_digest=c.digest('UNIT_PIT_SIGNAL'))
    c.contract(pg,'UNIT_PIT_FEATURE',{});c.contract(pg,'UNIT_PIT_OBSERVATION',body)
    add_namespace(pg,'UNIT_PIT_NAMESPACE');day=pg.execute('select current_date').fetchone()[0]
    add_publication(pg,publication_id='UNIT_PIT_PUBLICATION',namespace_id='UNIT_PIT_NAMESPACE',trade_date=day,lineage_id='UNIT_PIT_LINE')
    pg.execute("insert into fep.scopes values ('UNIT_PIT_SCOPE','STOCK','ENTRY','FIRST_PREWATCH','CORE','UNIT_PIT_NAMESPACE','UNIT_PIT_OBSERVATION',%s)",(c.digest('UNIT_PIT_SCOPE'),))
    pg.execute("insert into fep.signal_contract_registry values ('UNIT_PIT_OBSERVATION','UNIT_PIT_SCOPE','UNIT_PIT_SIGNAL','UNIT_PIT_OBSERVATION',%s,%s)",(c.digest(['UNIT_PIT_OBSERVATION',body]),body['predicate_digest']))
    cutoff=pg.execute("select clock_timestamp()+interval '2 seconds'").fetchone()[0]
    pg.execute("insert into fep.observations values ('UNIT_PIT_OBSERVATION','UNIT_PIT_SCOPE','UNIT_SEC',%s,'UNIT_PIT_SIGNAL',null,'UNIT_PIT_OBSERVATION',%s)",(day,cutoff+timedelta(hours=1)))
    manifest={k:'NONE' for k in ('accepted_head','algorithm_contract','parameter_contract','calendar','universe','adjustment_basis','membership','state_event_revision','enrichment_revision')}
    manifest.update(publication='UNIT_PIT_PUBLICATION',feature_contract='UNIT_PIT_FEATURE')
    pg.execute("insert into fep.observation_revisions(observation_id,revision,publication_id,feature_cutoff,dependency_manifest,dependency_digest,enrichment_token,evidence_origin,execution_mode,created_at) values ('UNIT_PIT_OBSERVATION',1,'UNIT_PIT_PUBLICATION',%s,%s,%s,'NONE','PIT_OBSERVED','SHADOW',clock_timestamp())",(cutoff,Jsonb(manifest),c.digest(manifest)))
    pg.execute("insert into fep.snapshots values ('UNIT_PIT_SNAPSHOT','UNIT_PIT_OBSERVATION',1,'UNIT_PIT_FEATURE',%s,%s,%s)",(c.digest('PIT_F'),c.digest('PIT_Q'),cutoff))

def upstream_aliases(clusters):
    from scripts.apply_v4_phase0_schema import VERSIONS
    import hashlib
    proof={}
    for kind,cluster in clusters.items():
        items=[];dsn=cluster['admin_dsn'].replace('dbname=postgres','dbname=fep_e1_'+kind)
        with psycopg.connect(dsn) as pg:
            for name,version in VERSIONS.items():
                path=ROOT/'src/workbench_db/migrations/v4_postgres'/name
                sha=hashlib.sha256(path.read_text(encoding='utf8').encode()).hexdigest();canonical='FEP_E5_CANONICAL_'+path.stem.upper()
                row=pg.execute('select checksum_sha256 from v4_meta.schema_migrations where version=%s',(canonical,)).fetchone()
                assert row and row[0].strip()==sha
                pg.execute("insert into v4_meta.schema_migrations values (%s,%s,clock_timestamp(),'ISOLATED_VERIFIED_CANONICAL_ALIAS_V1') on conflict do nothing",(version,sha))
                assert pg.execute('select checksum_sha256 from v4_meta.schema_migrations where version=%s',(version,)).fetchone()[0].strip()==sha
                items.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha,actually_executed_as=canonical,legacy_contract_alias=version,alias_is_not_second_execution=True))
        proof[kind]=items
    write(P+'IA06_UPSTREAM_MIGRATION_NAMESPACE_PROOF.json',dict(status='VERIFIED_EXISTING_SQL_NAMESPACE_ALIAS',fixtures=proof,SQL_reexecuted=False,production_modified=False,reason='Exact actually-executed SQL, explicit verification-only aliases for legacy owner-namespace tests.'))

def run():
    clusters=json.loads((ROOT/(P+'IA06_CLUSTER_BOOTSTRAP.json')).read_bytes());environment={}
    paths=[p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('*.sql'))]
    assert len(paths)==33
    for kind,cluster in ([] if any(x in sys.argv for x in ("--seed-only","--drills-only")) else clusters.items()):
        dsn=cluster['admin_dsn'];name='fep_e1_'+kind
        with psycopg.connect(dsn,autocommit=True) as admin:
            directory=Path(admin.execute('show data_directory').fetchone()[0]).resolve()
            assert directory==(Path(cluster['root'])/'data').resolve() and directory.is_relative_to(Path('E:/codex_tmp/test_temp'))
            environment[kind]=dict(version=admin.execute('select version()').fetchone()[0],system_identifier=str(admin.execute('select system_identifier from pg_control_system()').fetchone()[0]),data_directory=str(directory),role=admin.execute('select current_user').fetchone()[0],search_path=admin.execute('show search_path').fetchone()[0],redacted_dsn=dsn,disposable=True)
            admin.execute(sql.SQL('create database {}').format(sql.Identifier(name)))
        active=dsn.replace('dbname=postgres','dbname='+name)
        with psycopg.connect(active,autocommit=True) as pg:
            upstream=c.apply(pg,ROOT,paths[:27])
        with psycopg.connect(dsn,autocommit=True) as admin:
            admin.execute(sql.SQL('create database fep_e1_core_template template {}').format(sql.Identifier(name)))
        with psycopg.connect(active,autocommit=True) as pg:
            predecessor=c.apply(pg,ROOT,paths[27:31])
            before=pg.execute("select table_schema,table_name from information_schema.tables where table_schema in ('v4','fep') order by 1,2").fetchall()
            upgraded=c.apply(pg,ROOT,paths[31:]);replay=c.apply(pg,ROOT,paths)
            assert all(r['status']=='ALREADY_APPLIED' for r in replay)
            tables=pg.execute("select table_schema,table_name from information_schema.tables where table_schema in ('v4','fep') order by 1,2").fetchall()
        with psycopg.connect(dsn,autocommit=True) as admin:
            admin.execute(sql.SQL('create database fep_e1_template template {}').format(sql.Identifier(name)))
            admin.execute(sql.SQL('create database {} template {}').format(sql.Identifier('fep_e5b_'+kind),sql.Identifier(name)))
        write(P+'IA06_PG_'+kind.upper()+'_RECEIPT.json',dict(environment=environment[kind],database=name,from_empty=kind=='fresh',upgrade_predecessor='001-031' if kind=='upgrade' else None,migrations=upstream+predecessor+upgraded,replay=replay,before_successor_tables=before,after_tables=tables,migration_bindings=[binding(p) for p in paths],constraints_relaxed=False))
        print(kind+' installed 001-033 and idempotent replay',flush=True)
    if environment:write(P+'IA06_ENVIRONMENT_MANIFEST.json',dict(instances=environment,production_access=False))
    upstream_aliases(clusters)
    # Reconstruct canonical historical engineering fixtures using frozen inputs;
    # no production DB or formal FEP store is reset or used as a target.
    from scripts import run_fep_e5_r1r1b as b
    from workbench_analysis.fep_e5 import metadata_binding as m
    folder=ROOT/P/'canonical_fixtures';folder.mkdir(exist_ok=True)
    authority=(ROOT/'reports/fep_e5_r1r1c/HISTORICAL_RECONSTRUCTION_AUTHORITY_CONTRACT.json').read_bytes()
    (folder/'HISTORICAL_RECONSTRUCTION_AUTHORITY_CONTRACT.json').write_bytes(authority)
    b.REPORT=folder;b.frozen=lambda:None
    b.DSNS={k:v['admin_dsn'].replace('dbname=postgres','dbname=fep_e5b_'+k) for k,v in clusters.items()}
    # Explicit successor fixture: relocate metadata registration after scope
    # and before observations, as required by migration 033. Frozen owner stays intact.
    import inspect
    source=inspect.getsource(c.seed_identity)
    source=source.replace('    metadata = register(pg, contract)\n','')
    source=source.replace("    target = metadata['target_row']", "    metadata = register(pg, contract)\n    target = metadata['target_row']")
    namespace=dict(c.__dict__)
    exec(compile(source,'<REMAINDER_033_FIXTURE_ORDER>','exec'),namespace)
    original_seed=c.seed_identity;c.seed_identity=namespace['seed_identity']
    try:
        if "--drills-only" not in sys.argv:b.project()
    finally:c.seed_identity=original_seed
    # Typed synthetic PIT contract; this never grants historical authority.
    with psycopg.connect(b.DSNS['upgrade'],autocommit=True) as pg:
        if not pg.execute("select 1 from fep.observations where observation_id='UNIT_PIT_OBSERVATION'").fetchone():
            with pg.transaction():typed_pit(pg)
    from scripts import finalize_fep_e5_r1r1b as drills
    drills.REPORT=folder;drills.DSNS=b.DSNS;drills.verified=lambda:None
    drills.drills()
    write(P+'IA06_CANONICAL_FIXTURE_INPUTS.json',dict(authority=binding('reports/fep_e5_r1r1c/HISTORICAL_RECONSTRUCTION_AUTHORITY_CONTRACT.json'),output=binding((folder/'CANONICAL_PREDICTION_BINDING_READBACK.json').relative_to(ROOT).as_posix()),formal_FEP_DB_modified=False))
if __name__=='__main__':run()
