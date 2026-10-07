import os
import uuid
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict,make_conninfo
import pytest
from .conftest import ROOT
from workbench_analysis.fep_e1.db import apply
from workbench_analysis.fep_e1.contracts import atomic_json


def test_actual_fep_migration_rollback(pg):
    name=pg.execute('select current_database()').fetchone()[0]
    if name!='fep_e1_upgrade':
        pytest.skip('Upgrade instance owns the pre-FEP accepted-schema template; drill runs there')
    params=conninfo_to_dict(os.environ['FEP_E1_TEST_DSN']);params['dbname']='postgres'
    drill='fep_e1_rollback_'+uuid.uuid4().hex[:8]
    with psycopg.connect(make_conninfo(**params),autocommit=True) as admin:
        admin.execute(sql.SQL('create database {} template fep_e1_core_template').format(sql.Identifier(drill)))
    params['dbname']=drill
    with psycopg.connect(make_conninfo(**params)) as p:
        before=p.execute("select tablename from pg_tables where schemaname='v4' order by tablename").fetchall();p.commit()
        with pytest.raises(psycopg.Error) as exc:
            with p.transaction():
                txid=p.execute('select txid_current()').fetchone()[0]
                from workbench_analysis.fep_e5.canonical_ledger import apply as current_apply
                paths=[x.relative_to(ROOT).as_posix() for x in sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('*.sql')) if int(x.name[:3])>=28]
                current_apply(p,ROOT,paths)
                assert p.execute("select count(*) from pg_tables where schemaname='fep'").fetchone()[0]==35
                p.execute('create table fep.failed_install (id nonexistent_type)')
        assert p.execute("select count(*) from pg_tables where schemaname='fep'").fetchone()[0]==0
        assert p.execute("select count(*) from v4_meta.schema_migrations where version ~ '^FEP_E5_CANONICAL_0(28|29|30|31|32|33)'").fetchone()[0]==0
        after=p.execute("select tablename from pg_tables where schemaname='v4' order by tablename").fetchall()
        assert before==after
        atomic_json(ROOT/os.environ.get('FEP_TEST_RECEIPT_ROOT','reports/fep_e1')/'TRANSACTION_ROLLBACK_GATE.json',dict(status='PASS',database=drill,
            transaction_id=txid,exception=str(exc.value),sqlstate=exc.value.sqlstate,
            before_core_tables=before,after_core_tables=after,fep_tables_during_install=35,fep_tables_after_rollback=0,
            fep_migration_rows_after_rollback=0,fixture_state_retained=True))
