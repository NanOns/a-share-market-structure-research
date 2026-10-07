"""A schema-only disposable V4 database on the verified owned test cluster."""
import json
import uuid
from pathlib import Path
import psycopg
from psycopg import sql
from scripts.full_chain_repair_io import ROOT, binding, write
from scripts.forward_final_bootstrap import P


def prepare():
    clusters=json.loads((ROOT/'reports/forward_r2_remainder_consolidated_20261007/IA06_CLUSTER_BOOTSTRAP.json').read_bytes())
    cluster=clusters['fresh']
    expected=(Path(cluster['root'])/'data').resolve()
    if not expected.is_relative_to(Path('E:/codex_tmp/test_temp').resolve()):
        raise ValueError('OWNED_DISPOSABLE_CLUSTER_REQUIRED')
    name='fep_v4_final_r3_'+uuid.uuid4().hex[:12]
    template='fep_e1_template'
    template_dsn=cluster['admin_dsn'].replace('dbname=postgres','dbname='+template)
    import hashlib
    migration_files=sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('*.sql'))
    expected_checksums={hashlib.sha256(p.read_text(encoding='utf8').encode()).hexdigest() for p in migration_files}
    with psycopg.connect(template_dsn) as pg:
        checksums={str(r[0]).strip() for r in pg.execute('select checksum_sha256 from v4_meta.schema_migrations').fetchall()}
        if checksums!=expected_checksums: raise ValueError('EXACT_33_MIGRATION_TEMPLATE_REQUIRED')
        if pg.execute('select count(*) from v4.sector_membership_facts').fetchone()[0]:
            raise ValueError('EMPTY_V4_MEMBERSHIP_FIXTURE_TEMPLATE_REQUIRED')
    with psycopg.connect(cluster['admin_dsn'],autocommit=True) as pg:
        actual=Path(pg.execute('show data_directory').fetchone()[0]).resolve()
        if actual!=expected: raise ValueError('DISPOSABLE_CLUSTER_IDENTITY_MISMATCH')
        pg.execute(sql.SQL('CREATE DATABASE {} TEMPLATE {}').format(sql.Identifier(name),sql.Identifier(template)))
    dsn=cluster['admin_dsn'].replace('dbname=postgres','dbname='+name)
    migrations=[binding(p.relative_to(ROOT).as_posix()) for p in migration_files]
    write(P+'V4_SQL_DISPOSABLE_FIXTURE.json',dict(status='PASS',dsn=dsn,
        cluster_root=cluster['root'],verified_data_directory=str(actual),database=name,
        fixture_role='VERIFIED_DISPOSABLE_TEMPLATE_V4_10_V4_11_AND_PHASE0_TESTS',
        migrations=migrations,template_database=template,template_migration_checksums=sorted(checksums),
        global_roles_not_recreated=True,
        original_cluster_manifest=binding('reports/forward_r2_remainder_consolidated_20261007/IA06_CLUSTER_BOOTSTRAP.json'),
        production=False,runtime_permission=False))
    return dsn


if __name__=='__main__': print(prepare())
