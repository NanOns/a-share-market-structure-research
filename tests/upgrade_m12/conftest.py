import os
import shutil
from pathlib import Path
import pytest
from tests.runtime_isolation import REPOSITORY, create, guard, environment

@pytest.fixture(scope='session')
def isolated_m12_runtime(tmp_path_factory):
    root = create(tmp_path_factory.mktemp('m12_runtime'))
    database = root / 'data/database/test.duckdb'
    guard(root, database)
    database.parent.mkdir(parents=True)
    source = REPOSITORY / 'data/database/market_research.duckdb'
    # Read-only lock prevents concurrent writer changes during the snapshot copy.
    import duckdb
    with duckdb.connect(str(source), read_only=True):
        temporary = database.with_suffix('.copy.tmp')
        shutil.copyfile(source, temporary)
        os.replace(temporary, database)
    # Keep one complete frozen publication in this disposable fixture. The live
    # DB contains later partial preview publications and retired empty tables.
    with duckdb.connect(str(database)) as connection:
        selected = connection.execute("""select p.publication_id from publications p
          join publication_analysis_snapshots b using(publication_id)
          join analysis_snapshot_entries e using(snapshot_id)
          join technical_result_daily t on t.slice_id=e.slice_id and t.trade_date=e.trade_date
          where b.domain='LOCAL_RECONSTRUCTED' and e.domain='technical'
            and t.security_id='SZ.300010'
          order by p.trade_date desc,p.revision desc limit 1""").fetchone()
        if selected is None:
            raise ValueError('M12_COMPLETE_DISPOSABLE_FIXTURE_REQUIRED')
        connection.execute("update publications set status='FIXTURE_NOT_SELECTED' where publication_id<>?", [selected[0]])
        connection.execute("delete from publication_heads where trade_date<>(select trade_date from publications where publication_id=?)", [selected[0]])
        connection.execute("update publication_heads set publication_id=?", [selected[0]])
        cutoff = connection.execute('select trade_date from publications where publication_id=?', [selected[0]]).fetchone()[0]
        # The frozen M12 tests name the legacy materialization tables. Populate
        # those tables only in this disposable snapshot from exact current rows.
        for legacy, current in (('stock_technical_daily','technical_result_daily'),
                                ('historical_structure_daily','historical_structure_result_daily')):
            old_columns = [r[1] for r in connection.execute('pragma table_info('+legacy+')').fetchall()]
            new_columns = {r[1] for r in connection.execute('pragma table_info('+current+')').fetchall()}
            columns = ','.join('"'+c+'"' for c in old_columns if c in new_columns)
            connection.execute('delete from '+legacy)
            connection.execute('insert into '+legacy+' ('+columns+') select '+columns+' from '+current)
    # Bounded read-only input projection supplies the chart fixture without
    # relying on the live project's normalized output path at request time.
    normalized = root / 'data/normalized/adjusted_daily.parquet'
    normalized.parent.mkdir(parents=True)
    temporary = normalized.with_suffix('.tmp')
    with duckdb.connect(':memory:') as connection:
        connection.execute("copy (select * from read_parquet($source) where security_id='SZ.300010' and date<=$cutoff) to $target (format parquet)",
                           dict(source=str(REPOSITORY / 'data/normalized/adjusted_daily.parquet'), cutoff=cutoff, target=str(temporary)))
    os.replace(temporary, normalized)
    shutil.copytree(REPOSITORY / 'src/workbench_service/static', root / 'src/workbench_service/static')
    (root / 'config').mkdir()
    shutil.copyfile(REPOSITORY / 'config/history_windows.yaml', root / 'config/history_windows.yaml')
    return root, database, environment(root)

@pytest.fixture(scope='session', autouse=True)
def isolate_frozen_m12_consumers(request, isolated_m12_runtime):
    """Adapt fixture dependencies without changing historical test bytes/assertions."""
    import subprocess
    from types import SimpleNamespace
    from workbench_service.app import Api
    root, database, child_env = isolated_m12_runtime
    patch = pytest.MonkeyPatch()

    def isolated_api(db):
        guard(root, db)
        return Api(db, root=root)

    def guarded_process(command, **kwargs):
        if len(command) != 6 or command[1] != '-c':
            raise ValueError('UNEXPECTED_M12_CHILD_COMMAND')
        attempted_root, attempted_db = guard(command[3], command[5])
        if Path(kwargs.get('cwd', '')).resolve() != attempted_root:
            raise ValueError('CHILD_WORKING_DIRECTORY_MISMATCH')
        command = list(command)
        command[2] = 'from tests.runtime_isolation import serve; import sys; serve(sys.argv[1],sys.argv[3],int(sys.argv[2]))'
        return subprocess.Popen(command, **dict(kwargs, env=child_env))

    modules = {item.module for item in request.session.items if '/upgrade_m12/' in str(item.path).replace('\\','/')}
    for module in modules:
        if module.__name__.endswith('test_browser_behavior'):
            import duckdb
            with duckdb.connect(str(database),read_only=True) as connection:
                publication = connection.execute('select publication_id from publication_heads limit 1').fetchone()[0]
            patch.setattr(module,'ROOT',root)
            patch.setattr(module,'DB',database)
            patch.setattr(module,'PUBLICATION',publication)
            patch.setattr(module,'subprocess',SimpleNamespace(Popen=guarded_process,DEVNULL=subprocess.DEVNULL,TimeoutExpired=subprocess.TimeoutExpired))
        elif module.__name__.endswith('test_insight_api'):
            patch.setattr(module,'DB',database)
            patch.setattr(module,'Api',isolated_api)
    try:
        yield
    finally:
        patch.undo()
