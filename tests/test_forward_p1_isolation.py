import sqlite3
import pytest
from tests.runtime_isolation import REPOSITORY, create, guard, environment, recover_history, serve

@pytest.mark.parametrize('case', range(8))
def test_disposable_guard(tmp_path, case):
    root = create(tmp_path / 'runtime')
    database = root / 'data/test.sqlite'
    if case == 0:
        with pytest.raises(ValueError): serve(REPOSITORY, REPOSITORY / 'data/database/market_research.duckdb', 19001)
    elif case == 1:
        with pytest.raises(ValueError): guard('D:/new_tdx', 'D:/new_tdx/test.db')
    elif case == 2:
        with pytest.raises(ValueError): guard(root, REPOSITORY / 'data/database/market_research.duckdb')
    elif case == 3:
        with pytest.raises(ValueError): guard(root, database, 'DEFAULT')
    elif case == 4:
        (root / '.disposable-runtime.json').unlink()
        with pytest.raises(FileNotFoundError): guard(root, database)
    elif case == 5:
        env = environment(root)
        assert not any('DSN' in k or 'PG' in k for k in env)
        assert env['CODEX_TEST_RECOVERY_MODE'] == 'NO_REAL_RECOVERY'
    elif case == 6:
        assert recovery_fixture(root)['after_status'] == 'INTERRUPTED'
    else:
        with pytest.raises(ValueError): guard(root, root / '..' / 'escape.db')

def recovery_fixture(root):
    import duckdb
    from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor
    from workbench_db.history_job_repository import DuckDBHistoryJobRepository
    database = root / 'recovery.duckdb'
    guard(root, database, 'DISPOSABLE_RECOVERY')
    with duckdb.connect(str(database)) as connection:
        connection.execute((REPOSITORY / 'src/workbench_db/schema.sql').read_text(encoding='utf8'))
        connection.execute('insert into schema_migrations values (?,current_timestamp)',[BASE_SCHEMA_VERSION])
        MigrationExecutor(connection).apply()
    with DuckDBHistoryJobRepository(root, database).transaction() as store:
        store.upsert_job(job_id='disposable-job',job_key='fixture',status='RUNNING',
                         payload={'job_kind':'HISTORY_ANALYSIS','request':{},'completed_slice_ids':[]})
        store.upsert_attempt(job_id='disposable-job',attempt=1,status='RUNNING',payload={})
    before = database.read_bytes()
    result = recover_history(root, database)
    with duckdb.connect(str(database),read_only=True) as connection:
        status = connection.execute("select status from jobs where job_id='disposable-job'").fetchone()[0]
    import hashlib
    return dict(root=str(root),database=str(database),before_status='RUNNING',after_status=status,
                before_sha256=hashlib.sha256(before).hexdigest(),after_sha256=hashlib.sha256(database.read_bytes()).hexdigest(),
                recovery_result=result,background_resume=False)

def test_global_guard_rejects_explicit_real_database_writer():
    import duckdb
    with pytest.raises(ValueError,match='PROTECTED_DATABASE_WRITER_FORBIDDEN'):
        duckdb.connect(str(REPOSITORY/'data/database/market_research.duckdb'),read_only=False)

def test_global_guard_default_live_connection_is_read_only():
    import duckdb
    with duckdb.connect(str(REPOSITORY/'data/database/market_research.duckdb')) as connection:
        assert connection.execute('select 1').fetchone()==(1,)
        with pytest.raises(duckdb.InvalidInputException,match='read-only'):
            connection.execute('create table forbidden_isolation_probe(i integer)')


def test_legacy_collection_repository_metadata_is_readonly():
    from workbench_db import WorkbenchRepository
    import duckdb
    with WorkbenchRepository(REPOSITORY) as repository:
        assert repository.migration_receipt['migrations_executed'] is False
        assert repository.connection.execute('select count(*) from publication_heads').fetchone()[0] >= 0
        with pytest.raises(duckdb.InvalidInputException, match='read-only'):
            repository.connection.execute('create table forbidden_repository_probe(i integer)')
