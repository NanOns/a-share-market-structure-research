"""R4-E02 normal authority path in a disposable root; no constructor injection."""
import hashlib
import json
from types import SimpleNamespace

import pytest

from workbench_db.v4_history_pg_r1 import build, read
from workbench_db.v4_native import workspace_schema
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
    save(root, 'config/core_product_read_authority_r1.json', {'contract_id': 'CORE_PRODUCT_READ_AUTHORITY_R1', 'manifest': manifest})
    bff = object.__new__(CoreProductBFFR1)
    bff.api = SimpleNamespace(root=root, cache={}, candidate={})
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
    head = save(tmp_path, 'data/v4/head.json', {'T0': '2026-10-09'})
    index = build(tmp_path, [{'security_id': 'ENGINEERING', 'bars': bars}],
                  head_token=head['sha256'], t0='2026-10-09', source_digest='b' * 64)
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


def test_chart_history_pack_does_not_require_unrelated_market_facts_owner(tmp_path):
    day='2026-10-09'
    index_root=tmp_path/'upstream-history-root'
    index_root.mkdir()
    head=save(tmp_path,'data/v4/head.json',{'T0':day})
    source=save(tmp_path,'data/history-source.json',{'scope':'accepted chart history'})
    history=dict(contract_id='V4_PG_DATED_HISTORY_INDEX_R1',engine='postgresql',
        schema=workspace_schema(index_root,'history'),version='v1',head_token=head['sha256'],
        T0=day,source_digest=source['sha256'],logical_digest='c'*64,symbol_count=1,bar_count=1)
    manifest=save(tmp_path,'data/manifest.json',dict(contract_id='CORE_PRODUCT_DATED_READ_PACK_PG_MARKET_R2',
        T0=day,head=head,history_index=history,source_bindings={'history':source},
        market_facts={'contract_id':'MISSING_MARKET_DESCRIPTOR'}))
    save(tmp_path,'config/core_product_read_authority_r1.json',
        {'contract_id':'CORE_PRODUCT_READ_AUTHORITY_R1','manifest':manifest})
    bff=object.__new__(CoreProductBFFR1)
    bff.api=SimpleNamespace(root=tmp_path,cache={},candidate={})
    bff.isolated_history=None
    bff.chart_history_index_root=index_root
    loaded,facts=bff.chart_history_pack(day)
    assert facts is None
    assert loaded['history_index']==history
