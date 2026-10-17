from types import SimpleNamespace

import pytest

from workbench_analysis.r43_owner_replay import ref
from workbench_db.v4_forward_pg_r1 import canonical, digest
from workbench_db.v4_native import workspace_schema
from workbench_service import native_product_catalog_v3 as catalog
from workbench_service.core_product_bff_r1 import CoreProductBFFR1, dated_product_manifest


def _fixture(root, monkeypatch):
    from workbench_db import v4_operational_owner_pg_closeout as closeout

    day = '2026-10-17'
    source_path = root / 'history.jsonl.gz'
    source_path.write_bytes(b'opaque-owner-history')
    source = ref(root, source_path)
    owners = {day: {'period_raw': source}}
    scope = dict(contract_id='V4_NATIVE_DATED_PRODUCT_SOURCE_SCOPE_V3', T0=day,
        source_bindings={'history': source}, source_owners=owners[day], AS_RECORDED=False, PIT_ELIGIBLE=False)
    scope_path = root / 'scope.json'
    scope_path.write_bytes(canonical(scope))
    scope_binding = ref(root, scope_path)
    manifest = dict(contract_id='CORE_PRODUCT_DATED_HISTORY_ONLY_PACK_R1', T0=day,
        head=scope_binding, fact_token=scope_binding['sha256'], capabilities=['CHART_HISTORY'],
        history_index=dict(engine='postgresql', T0=day, head_token=scope_binding['sha256'],
            source_digest=source['sha256'], schema=workspace_schema(root, 'history')),
        source_bindings={'history': source})
    manifest_path = root / 'manifest.json'
    manifest_path.write_bytes(canonical(manifest))
    authority = dict(contract_id=catalog.CONTRACT, dates={day: ref(root, manifest_path)},
        source_owners=owners, owner_source_digest=digest(canonical(owners)),
        PIT_ELIGIBLE=False, AS_RECORDED=False, historical_PIT_permission=False)
    catalog_path = root / 'catalog.json'
    catalog_path.write_bytes(canonical(authority))
    candidate = dict(accepted_trade_date=day, published_sessions=[day], owners=owners,
        exact_daily_adjustment_contract='exact-r1', native_product_read_authority=ref(root, catalog_path))
    stored = {}

    def append(root_arg, fact_token, t0, domain, binding, rows):
        stored[(domain, fact_token)] = rows
        return dict(path=f'{domain}/{fact_token}.pg.json', fact_key=fact_token)

    monkeypatch.setattr(closeout, 'prepare', append)
    monkeypatch.setattr(closeout, 'read', lambda root_arg, descriptor, fact_token, t0, domain, binding, **kwargs:
        stored[(domain, fact_token)])
    receipt = catalog.prepare_pg(root, candidate, authority)
    assert receipt['dates'] == 1
    return candidate, manifest, stored


def test_pg_product_catalog_reads_manifest_and_scope_without_local_fallback(tmp_path, monkeypatch):
    candidate, expected, _ = _fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(catalog, 'checked', lambda *_: pytest.fail('PG catalogue reopened local manifest'))
    loaded = catalog.load(tmp_path, candidate)
    assert loaded['dates']['2026-10-17'] == expected
    assert dated_product_manifest(tmp_path, loaded, '2026-10-17', candidate=candidate) == expected
    api = SimpleNamespace(root=tmp_path, candidate=candidate, cache={})
    setattr(api, 'token', 'head-token')
    bff = object.__new__(CoreProductBFFR1)
    bff.api = api
    bff.isolated_history = None
    bff.market_fact_index_root = None
    bff.chart_history_index_root = None
    manifest, facts = bff.pack('2026-10-17')
    assert manifest == expected and facts is None
    chart_manifest, chart_index = bff.chart_history_pack('2026-10-17')
    assert chart_manifest == expected and chart_index is None
    with pytest.raises(ValueError, match='PRODUCT_PG_CANDIDATE_REQUIRED_NO_FILE_FALLBACK'):
        dated_product_manifest(tmp_path, loaded, '2026-10-17')


def test_pg_product_catalog_rejects_owner_binding_substitution(tmp_path, monkeypatch):
    candidate, _, _ = _fixture(tmp_path, monkeypatch)
    candidate['owners']['2026-10-17']['period_raw']['sha256'] = 'b' * 64
    with pytest.raises(ValueError, match='CATALOG|SCOPE_MISMATCH'):
        catalog.load(tmp_path, candidate)
