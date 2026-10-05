"""FEP_E1_MIGRATION_V1: checksum ledger and explicit, transactional installation.

The legacy migration service is frozen. This successor applies only allocated
FEP migrations to an existing V4 schema; empty isolated fixtures can explicitly
request upstream bootstrap. There is no default DSN or production credential.
"""
import hashlib
from pathlib import Path


def apply(pg, root, *, bootstrap=False):
    paths = sorted((Path(root) / 'src/workbench_db/migrations/v4_postgres').glob('[0-9][0-9][0-9]_*.sql'))
    result = []
    for path in paths:
        number = int(path.name[:3])
        if number > 31:
            raise ValueError('FEP_E1_UNALLOCATED_MIGRATION:' + path.name)
        if number < 28 and not bootstrap:
            continue
        sql = path.read_text(encoding='utf8')
        checksum = hashlib.sha256(sql.encode()).hexdigest()
        if number >= 28:
            version = 'FEP_E1_' + path.stem.upper()
        else:
            from scripts.apply_v4_phase0_schema import VERSIONS
            version = VERSIONS.get(path.name, 'FEP_E1_FIXTURE_UPSTREAM_' + path.stem.upper())
        with pg.transaction():
            pg.execute("select pg_advisory_xact_lock(hashtextextended('v4.fep.migration',0))")
            if pg.execute("select to_regclass('v4_meta.schema_migrations')").fetchone()[0]:
                row = pg.execute('select checksum_sha256 from v4_meta.schema_migrations where version=%s', (version,)).fetchone()
                if row:
                    if row[0].strip() != checksum:
                        raise ValueError('FEP_MIGRATION_CHECKSUM_CONFLICT:' + version)
                    result.append(dict(version=version, sha256=checksum, status='ALREADY_APPLIED'))
                    continue
            pg.execute(sql)
            pg.execute('insert into v4_meta.schema_migrations(version,checksum_sha256,applied_at,contract_id) values (%s,%s,now(),%s)',
                       (version, checksum, 'FEP_E1_ENGINEERING_V1' if number >= 28 else 'ISOLATED_UPSTREAM_FIXTURE'))
            result.append(dict(version=version, sha256=checksum, status='APPLIED'))
    return result


def validate_inventory(pg):
    tables = {r[0] for r in pg.execute("select tablename from pg_tables where schemaname='fep'")}
    guards = {r[0] for r in pg.execute("select c.relname from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='fep' and t.tgname='immutable' and t.tgenabled='O'")}
    if len(tables) != 33 or len(guards) != 32 or tables - {'deployment_heads'} != guards:
        raise ValueError('FEP_UNGUARDED_TABLE_INVENTORY')
    return dict(tables=sorted(tables),guarded=sorted(guards),mutable=['deployment_heads'])
