"""DB12 native immutable export and exact descriptor negative vectors."""
import json
import threading
from http.server import ThreadingHTTPServer
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from pathlib import Path

import psycopg
import pytest

from workbench_db.v4_shadow_pg_r1 import build_readback, read
from workbench_db.v4_native import connection
from tests.test_v4_17_shadow_ui import native_vector, real_token
from workbench_service.shadow_context import PREFIX, ShadowContextReader


def test_export_is_immutable_and_reader_transaction_is_readonly(tmp_path):
    descriptor = build_readback(tmp_path, [], environment='REAL', evidence_origin='PIT_OBSERVED')
    assert build_readback(tmp_path, [], environment='REAL', evidence_origin='PIT_OBSERVED') == descriptor
    with read(descriptor) as tx:
        assert tx.execute('SHOW transaction_isolation').fetchone()[0] == 'repeatable read'
        assert tx.execute('SHOW transaction_read_only').fetchone()[0] == 'on'
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            tx.execute('DELETE FROM v4.shadow_readback_facts_r1')
    with pytest.raises(psycopg.Error, match='IMMUTABLE_SHADOW_READBACK'):
        with connection(descriptor['schema']) as pg:
            pg.execute('TRUNCATE v4.shadow_readback_facts_r1')


@pytest.mark.parametrize('change', ['digest', 'engine', 'contract', 'extra'])
def test_descriptor_rejects_wrong_identity(tmp_path, change):
    descriptor = build_readback(tmp_path, [], environment='REAL', evidence_origin='PIT_OBSERVED')
    if change == 'digest':
        descriptor['logical_digest'] = '0' * 64
    elif change == 'engine':
        descriptor['engine'] = 'sqlite3'
    elif change == 'contract':
        descriptor['contract_id'] = 'V4_PG_RESEARCH_SNAPSHOT_R1'
    else:
        descriptor['dsn'] = 'UNAUTHORIZED'
    with pytest.raises(ValueError):
        with read(descriptor):
            pytest.fail('invalid descriptor must never yield a reader')


def test_manifest_pins_descriptor_bytes(tmp_path):
    root, manifest, config, save = native_vector(tmp_path)
    descriptor = json.loads((root / manifest['database_path']).read_bytes())
    descriptor['logical_digest'] = '0' * 64
    save(manifest['database_path'], descriptor)  # deliberately retain old manifest binding
    status, data = ShadowContextReader(root).handle(PREFIX + 'context', {})
    assert status == 409 and data['code'] == 'SOURCE_DIGEST_MISMATCH'


def test_descriptor_unpinned_path_is_rejected(tmp_path):
    root, manifest, config, save = native_vector(tmp_path)
    manifest['database_binding']['path'] = 'other.pg.json'
    config['accepted_readback'] = save('manifest.json', manifest)
    config['external_acceptance'] = save('receipt.json', dict(decision='PASS_REAL_SHADOW_UI_READBACK',
        readback_sha256=config['accepted_readback']['sha256'], context_token=real_token(manifest, config)))
    save('config/v4_17_shadow_ui_source_v1.json', config)
    status, data = ShadowContextReader(root).handle(PREFIX + 'context', {})
    assert status == 409 and data['code'] == 'EXACT_PG_SHADOW_BINDING_REQUIRED'


def test_v4_http_pg_consumption_and_write_rejection(tmp_path):
    from workbench_service.shadow_server import make_shadow_handler
    root, manifest, config, save = native_vector(tmp_path)
    server = ThreadingHTTPServer(('127.0.0.1', 0), make_shadow_handler(root))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        with urlopen(base + PREFIX + 'context') as response:
            context = json.loads(response.read())
        assert context['status'] == 'READY' and context['real_sample_count'] == 0
        context_binding = context['context_token']
        for component in ('summary', 'radar', 'entity', 'cohort', 'settlement', 'health'):
            with urlopen(base + PREFIX + component + '?context_token=' + context_binding) as response:
                data = json.loads(response.read())
            assert data['context_token'] == context_binding and data['status'] == 'READY'
        for method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            with pytest.raises(HTTPError) as caught:
                urlopen(Request(base + PREFIX + 'context', data=b'{}', method=method))
            assert caught.value.code == 405
        with pytest.raises(HTTPError) as caught:
            urlopen(base + PREFIX + 'context?context_token=a&context_token=b')
        assert caught.value.code == 409
    finally:
        server.shutdown(); server.server_close(); thread.join(2)


def test_invalid_contract_blocks_v4_startup(tmp_path):
    from workbench_service.shadow_server import make_shadow_handler
    from workbench_service.research_context import ResearchContextError
    root = tmp_path / 'broken'
    (root / 'config').mkdir(parents=True)
    contract = json.loads((Path(__file__).resolve().parents[1] / 'config/v4_17_shadow_ui_contract_v1.json').read_bytes())
    contract['identity_fields'] = []
    (root / 'config/v4_17_shadow_ui_contract_v1.json').write_text(json.dumps(contract))
    # The current shared service isolates this broken domain. A returned
    # handler must reject actual Shadow requests rather than serving data.
    server=ThreadingHTTPServer(('127.0.0.1',0),make_shadow_handler(root))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with pytest.raises(HTTPError) as caught:
            urlopen(f'http://127.0.0.1:{server.server_port}'+PREFIX+'context')
        assert caught.value.code==409
        payload=json.loads(caught.value.read())
        assert payload['status']=='BLOCKED' and payload['code']=='SHADOW_CONTRACT_INVALID'
        assert payload['items']==[]
    finally:server.shutdown();server.server_close();thread.join(2)
