"""Explicit R3 source guard propagation and a disposable live UI fixture."""
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import threading
import shutil
import pytest
from tests.runtime_isolation import REPOSITORY


def pytest_configure(config):
    from tests.final_disposable_paths import configured_source_roots
    patch = pytest.MonkeyPatch()
    config._final_guard_patch = patch
    logs = Path('G:/codex_tmp/test_temp') / (Path(str(config.option.basetemp or 'final_blocker')).name + '_source_guard')
    patch.setenv('FINAL_SOURCE_GUARD_ROOTS', json.dumps([str(p) for p in configured_source_roots()]))
    patch.setenv('FINAL_CHILD_AUDIT_ROOT', str(logs))
    guarddir = REPOSITORY / 'tests/final_child_guard'
    patch.setenv('PYTHONPATH', str(guarddir) + os.pathsep + os.environ.get('PYTHONPATH', ''))
    runpy.run_path(str(guarddir / 'sitecustomize.py'), run_name='_final_parent_source_guard')
    original = subprocess.Popen

    def guarded_child(command, *args, **kw):
        if isinstance(command, (list, tuple)) and command and Path(str(command[0])).stem.lower() in ('python', 'python3', 'pythonw'):
            env = dict(kw.get('env') or os.environ)
            env['FINAL_SOURCE_GUARD_ROOTS'] = os.environ['FINAL_SOURCE_GUARD_ROOTS']
            env['FINAL_CHILD_AUDIT_ROOT'] = str(logs)
            env['PYTHONPATH'] = str(guarddir) + os.pathsep + env.get('PYTHONPATH', '')
            kw['env'] = env
        return original(command, *args, **kw)
    patch.setattr(subprocess, 'Popen', guarded_child)


def pytest_unconfigure(config):
    patch = getattr(config, '_final_guard_patch', None)
    if patch:
        patch.undo()


@pytest.fixture(scope='session')
def isolated_v3_live_url(tmp_path_factory):
    from tests.upgrade_m12.conftest import isolated_m12_runtime
    from tests.runtime_isolation import guard
    from workbench_service import app
    from http.server import ThreadingHTTPServer
    root, database, env = isolated_m12_runtime.__wrapped__(tmp_path_factory)
    guard(root, database)
    from common.disposable_paths import resolve_destination_inside_root
    from workbench_service.research_bundle_v3_3 import activate_bundle, validate_bundle, build_bundle
    pointer = json.loads((REPOSITORY / 'data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json').read_bytes())
    source = Path(pointer['bundle_path']).resolve()
    if not source.is_relative_to((REPOSITORY / 'data/research_bundles_v3_3').resolve()):
        raise ValueError('UI_FIXTURE_BUNDLE_SOURCE_ESCAPE')
    manifest = validate_bundle(source)
    if manifest['output_digest'] != pointer['output_digest']:
        raise ValueError('UI_FIXTURE_BUNDLE_IDENTITY_MISMATCH')
    destination = resolve_destination_inside_root(root, 'data/research_bundles_v3_3/' + pointer['output_digest'])
    shutil.copytree(source, destination)
    import duckdb
    from workbench_service.research_registry_v3_3 import register_active_bundle
    with duckdb.connect(str(database)) as connection:
        publication, date = connection.execute('select publication_id,cast(trade_date as varchar) from publication_heads limit 1').fetchone()
        identity = dict(manifest['identity'], publication_id=publication, trade_date=date)
        built = build_bundle(root / 'data/ui_transport_fixture_bundles', identity,
                             json.loads((destination / 'results.json').read_bytes()),
                             {'fixture_scope': 'DISPOSABLE_UI_TRANSPORT_ONLY', 'source_output_digest': manifest['output_digest'],
                              'identity_rebinding_is_not_algorithm_or_release_acceptance': True},
                             bundle_contract=manifest['contract_id'])
        activate_bundle(Path(built['path']), root / 'data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json')
        register_active_bundle(connection, root / 'data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json')
        complete = connection.execute("select count(*) from research_runs_v3_3 where publication_id=? and status='COMPLETE' and result_count>=50", [publication]).fetchone()[0]
        if not complete:
            raise ValueError('UI_FIXTURE_COMPLETE_RESEARCH_PUBLICATION_REQUIRED')
    patch = pytest.MonkeyPatch()
    for cls in (app.HistoryJobService, app.OneClickPublisher):
        original = cls.recover_interrupted
        def synchronous_recovery(self, *args, _original=original, **kw):
            kw['background'] = False
            return _original(self, *args, **kw)
        patch.setattr(cls, 'recover_interrupted', synchronous_recovery)
    try:
        server = ThreadingHTTPServer(('127.0.0.1', 0), app.make_handler(root, database))
    except BaseException:
        patch.undo()
        raise
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = 'http://127.0.0.1:' + str(server.server_port)
    try:
        from workbench_service.today_research_bundle import TodayResearchBundleReader
        direct = TodayResearchBundleReader(root, database_path=database).list(publication_id=publication, trade_date=date, page_size=25)
        if direct.get('status') != 'READY':
            raise ValueError('UI_FIXTURE_DIRECT_READ_NOT_READY:' + json.dumps(direct))
        import urllib.request
        import urllib.parse
        query = urllib.parse.urlencode({'publication_id': publication, 'trade_date': date, 'page_size': 25})
        try:
            with urllib.request.urlopen(url + '/api/v3/research/today?' + query, timeout=10) as response:
                listing = json.load(response)
        except urllib.error.HTTPError as error:
            raise ValueError('UI_FIXTURE_HTTP_ERROR:' + error.read().decode('utf8')) from error
        if listing.get('status') != 'READY' or listing.get('returned_count') != 25:
            raise ValueError('UI_FIXTURE_HTTP_RESEARCH_NOT_READY:' + json.dumps(listing, ensure_ascii=False))
        yield url
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)
        patch.undo()
        if thread.is_alive():
            raise ValueError('DISPOSABLE_UI_SERVICE_DID_NOT_STOP')
