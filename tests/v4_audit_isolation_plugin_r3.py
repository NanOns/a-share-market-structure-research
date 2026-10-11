"""V4-only audit: isolated PostgreSQL, no DuckDB/SQLite compatibility fixture."""
import os,json
from pathlib import Path
import pytest
from tests import remainder_isolation_plugin as base
from tests.remainder_isolation_plugin import (
 pinned_r15_contract_profile,bounded_storage_contract_tmp_path,
 exact_legacy_v1_identity_profile,pinned_v9_v10_publication_history_profile,
 exact_frozen_stage_test_profile,frozen_additive_ast_node,
 accepted_observation_projection_replay,
)
_ACTIVE_NODE=None

class V4NonPostgresBackendError(BaseException):
    """Never satisfy a business-negative assertion expecting ValueError/Exception."""

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item,nextitem):
    global _ACTIVE_NODE
    _ACTIVE_NODE=item.nodeid
    try:yield
    finally:_ACTIVE_NODE=None

def pytest_configure(config):
    base.pytest_configure(config)
    from tests import final_blocker_plugin
    final_blocker_plugin.pytest_configure(config)
    import duckdb,sqlite3
    patch=config._remainder_patch
    def reject_duck(*args,**kwargs):
        base.EVENTS.append(dict(event='duckdb.connect',node=_ACTIVE_NODE,decision='REJECT_NON_POSTGRES_IN_V4_SCOPE'))
        raise V4NonPostgresBackendError('V4_SCOPE_DUCKDB_FORBIDDEN')
    def reject_sqlite(*args,**kwargs):
        base.EVENTS.append(dict(event='sqlite3.connect',node=_ACTIVE_NODE,decision='REJECT_NON_POSTGRES_IN_V4_SCOPE'))
        raise V4NonPostgresBackendError('V4_SCOPE_SQLITE_FORBIDDEN')
    patch.setattr(duckdb,'connect',reject_duck)
    patch.setattr(sqlite3,'connect',reject_sqlite)

def pytest_collection_modifyitems(session,config,items):
    base.pytest_collection_modifyitems(session,config,items)
    # The manifest is frozen before pytest; no extra legacy module is admitted.
    scope=json.loads(Path(os.environ['V4_AUDIT_SCOPE_MANIFEST']).read_bytes())
    admitted={x['path'] for x in scope['included_test_modules']}
    unexpected=[str(x.nodeid) for x in items if x.path.relative_to(base.REPOSITORY).as_posix() not in admitted]
    if unexpected:raise ValueError('V4_TEST_SCOPE_ESCAPE:'+str(unexpected[:3]))
    p=Path(config.getoption('basetemp')+'_collected_nodes.json')
    p.write_bytes((json.dumps([x.nodeid for x in items],indent=2)+'\n').encode())

def pytest_sessionstart(session):
    base.pytest_sessionstart(session)
    import duckdb,sqlite3,psycopg
    for call,code in [(lambda:duckdb.connect(':memory:'),'V4_SCOPE_DUCKDB_FORBIDDEN'),(lambda:sqlite3.connect(':memory:'),'V4_SCOPE_SQLITE_FORBIDDEN'),(lambda:psycopg.connect('host=127.0.0.1 port=5432 dbname=postgres'),'DISPOSABLE_PG_CLUSTER_REQUIRED')]:
        try:call()
        except (V4NonPostgresBackendError,ValueError) as error:
            if str(error)!=code:raise
        else:raise ValueError('V4_AUDIT_DATABASE_GUARD_NOT_ACTIVE')
    base.EVENTS.append(dict(event='V4_database_guard_preflight',decision='PASS_DUCKDB_SQLITE_AND_UNREGISTERED_PG_REJECTED'))
def pytest_runtest_logreport(report):base.pytest_runtest_logreport(report)

@pytest.fixture(autouse=True)
def pinned_v4_r24r1_simulation_profile(request,monkeypatch):
    """Restore only the named V4 historical simulation, without legacy DB access."""
    if request.module.__name__.rsplit('.',1)[-1]!='test_r24r1_authority':return
    base.pinned_r25_and_v3_simulation_profiles.__wrapped__(request,monkeypatch)

def pytest_sessionfinish(session,exitstatus):base.pytest_sessionfinish(session,exitstatus)
def pytest_unconfigure(config):
    from tests import final_blocker_plugin
    final_blocker_plugin.pytest_unconfigure(config)
    base.pytest_unconfigure(config)
