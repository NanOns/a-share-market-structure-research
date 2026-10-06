"""Protect live databases and recovery even outside the legacy M12 fixture."""
import functools
import json
import os
import traceback
from pathlib import Path
import pytest
from tests.runtime_isolation import REPOSITORY, DISPOSABLE_BASE, create, guard, protected_roots

def pytest_configure(config):
    import duckdb
    patch = pytest.MonkeyPatch()
    config._forward_p1_patch = patch
    config._forward_p1_connections = []
    connect = duckdb.connect

    @functools.wraps(connect)
    def protected_connect(database=':memory:', *args, **kwargs):
        if database not in (None, '', ':memory:'):
            path = Path(database).resolve()
            inputs = [REPOSITORY / 'data'] + [p for p in protected_roots() if p != REPOSITORY]
            if any(path == p or path.is_relative_to(p) for p in inputs):
                requested = args[0] if args else kwargs.get('read_only')
                config._forward_p1_connections.append(dict(database=str(path),requested_read_only=requested,
                    decision='REJECT_EXPLICIT_WRITER' if requested is False else 'READ_ONLY_INPUT',
                    callers=[dict(file=f.filename,line=f.lineno,function=f.name) for f in traceback.extract_stack(limit=10)[:-1]]))
                if requested is False:
                    raise ValueError('PYTEST_PROTECTED_DATABASE_WRITER_FORBIDDEN')
                if args:
                    args = (True,) + args[1:]
                else:
                    kwargs['read_only'] = True
        return connect(database,*args,**kwargs)
    patch.setattr(duckdb,'connect',protected_connect)

    # Legacy collection reads publication metadata through a migration-capable
    # repository. Supply a read-only handle; never run startup migrations on inputs.
    from workbench_db import WorkbenchRepository
    repository_open = WorkbenchRepository.open
    repository_close = WorkbenchRepository.close
    def readonly_input_open(self):
        path = self.database_path.resolve()
        if path.is_relative_to(REPOSITORY / 'data'):
            self.connection = protected_connect(str(path), read_only=True)
            self._forward_p1_readonly_input = True
            self.migration_receipt = {'mode': 'READ_ONLY_TEST_METADATA', 'migrations_executed': False}
            return self
        return repository_open(self)
    def readonly_input_close(self):
        if getattr(self, '_forward_p1_readonly_input', False):
            if self.connection is not None: self.connection.close()
            self.connection = None
            return
        return repository_close(self)
    patch.setattr(WorkbenchRepository, 'open', readonly_input_open)
    patch.setattr(WorkbenchRepository, 'close', readonly_input_close)

    from workbench_service import app
    def runtime_guard(root,database):
        root=Path(root).resolve()
        if root.is_relative_to(DISPOSABLE_BASE): create(root)
        return guard(root,database)

    for name in ('serve','make_handler','_recover_startup'):
        original=getattr(app,name)
        def wrap(function,kind):
            @functools.wraps(function)
            def checked(root,*args,**kwargs):
                database=(kwargs.get('database_path') or (Path(root)/'data/database/market_research.duckdb')) if kind=='serve' else (args[0] if args else kwargs.get('db'))
                runtime_guard(root,database)
                return function(root,*args,**kwargs)
            return checked
        patch.setattr(app,name,wrap(original,name))

    for cls in (app.HistoryJobService,app.OneClickPublisher):
        original=cls.recover_interrupted
        def wrap_recovery(function):
            @functools.wraps(function)
            def checked(self,*args,**kwargs):
                runtime_guard(self.root,self.database_path)
                if kwargs.get('background') is True:
                    raise ValueError('TEST_BACKGROUND_RECOVERY_REQUIRES_EXPLICIT_DISPOSABLE_REQUEST_GUARD')
                return function(self,*args,**kwargs)
            return checked
        patch.setattr(cls,'recover_interrupted',wrap_recovery(original))

def pytest_sessionfinish(session,exitstatus):
    base=session.config.getoption('basetemp')
    if base:
        target=Path(str(base)+'_protected_connects.json').resolve()
        if not target.is_relative_to(DISPOSABLE_BASE): raise ValueError('PYTEST_CONNECTION_LOG_OUTSIDE_DISPOSABLE_BASE')
        temporary=target.with_suffix('.tmp')
        temporary.write_text(json.dumps(session.config._forward_p1_connections,indent=2)+'\n',encoding='utf8')
        os.replace(temporary,target)
    session.config._forward_p1_patch.undo()
