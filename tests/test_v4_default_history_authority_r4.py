"""R4-E02 normal authority path in a disposable root; no constructor injection."""
import hashlib
import json
from types import SimpleNamespace

import pytest

from workbench_db.v4_history_pg_r1 import build, read
from workbench_service.core_product_bff_r1 import CoreProductBFFR1


def save(root, name, value):
    raw = json.dumps(value, sort_keys=True).encode()
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return dict(path=name, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def vector(root, index):
    head = save(root, 'data/v4/head.json', {'T0': '2026-10-09'})
    facts = save(root, 'data/market.json', {'market': 'engineering'})
    manifest = save(root, 'data/manifest.json', dict(T0='2026-10-09', head=head,
                    history_index=index, market_facts=facts))
    save(root, 'config/core_product_read_authority_r1.json', {'manifest': manifest})
    bff = object.__new__(CoreProductBFFR1)
    bff.api = SimpleNamespace(root=root, cache={})
    bff.isolated_history = None
    return bff


def test_default_old_sqlite_binding_is_rejected(tmp_path):
    bff = vector(tmp_path, {'path': 'history.sqlite', 'sha256': 'a' * 64})
    with pytest.raises(ValueError, match='^PG_HISTORY_BINDING_REQUIRED_NO_FALLBACK$'):
        bff.history_pack('2026-10-09')
    assert not (tmp_path / 'history.sqlite').exists()


def test_default_pg_binding_reads_exact_history(tmp_path):
    bars = [{'trade_date': '2026-10-09', 'raw_ohlc': [1, 2, 1, 2],
             'qfq_ohlc': [2, 4, 2, 4], 'volume': 100, 'amount': 150}]
    index = build(tmp_path, [{'security_id': 'ENGINEERING', 'bars': bars}],
                  head_token='a' * 64, t0='2026-10-09', source_digest='b' * 64)
    bff = vector(tmp_path, index)
    manifest, facts = bff.history_pack('2026-10-09')
    assert bff.isolated_history is None
    assert facts == {'market': 'engineering'}
    assert read(tmp_path, manifest['history_index'], '2026-10-09', 'ENGINEERING') == bars
    with pytest.raises(ValueError, match='CONTEXT'):
        read(tmp_path, manifest['history_index'], '2026-10-08', 'ENGINEERING')


def test_default_manifest_tamper_fails_before_pg(tmp_path):
    bff = vector(tmp_path, {'engine': 'postgresql'})
    (tmp_path / 'data/manifest.json').write_text('{}')
    with pytest.raises(ValueError, match='DIGEST_MISMATCH'):
        bff.history_pack('2026-10-09')
