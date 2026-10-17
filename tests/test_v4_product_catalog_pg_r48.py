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


def test_current_bff_pack_routes_fail_closed_without_head_bound_pg_catalog(tmp_path, monkeypatch):
    candidate, _, _ = _fixture(tmp_path, monkeypatch)
    candidate.pop(catalog.PG_KEY)
    monkeypatch.setattr(catalog, 'checked', lambda *_: pytest.fail('BFF opened local product authority'))
    bff = object.__new__(CoreProductBFFR1)
    bff.api = SimpleNamespace(root=tmp_path, candidate=candidate, cache={})
    bff.isolated_history = None

    with pytest.raises(ValueError, match='PRODUCT_PG_CATALOG_REQUIRED_NO_FILE_FALLBACK'):
        bff.pack('2026-10-17')
    with pytest.raises(ValueError, match='PRODUCT_PG_CATALOG_REQUIRED_NO_FILE_FALLBACK'):
        bff.chart_history_pack('2026-10-17')


def test_bff_focus_reads_head_bound_catalog_and_postgresql_fact_without_config_fallback(tmp_path,monkeypatch):
    from workbench_service import core_product_bff_r1 as bff_module
    from workbench_db import v4_focus_projection_pg_closeout as focus_pg

    day='2026-10-17';head_token='a'*64
    projection_binding=dict(path='pg/focus.pg.json',sha256='b'*64,bytes=20,
        pg_descriptor=dict(contract_id='V4_PG_OPERATIONAL_OWNER_FACTS_R1',engine='postgresql',
                           kind='focus_projection',fact_key='focus-fact'))
    manifest=dict(T0=day,contract_id='CORE_PRODUCT_FOCUS_READ_MANIFEST_R3_NATIVE_PG',
                  head=dict(path='head-scope.json',sha256=head_token,bytes=20),
                  projection=projection_binding,projection_source=dict(path='ingress.gz',sha256='c'*64,bytes=30))
    candidate={catalog.PG_KEY:{'contract_id':catalog.PG_CONTRACT}}
    monkeypatch.setattr(catalog,'load',lambda *_:dict(dates={day:manifest},scopes={day:{'scope':'accepted'}}))
    reads=[]
    monkeypatch.setattr(focus_pg,'read',lambda root,binding,**kwargs:reads.append((binding,kwargs)) or {'events':[],'episodes':[]})
    monkeypatch.setattr(bff_module,'checked',lambda *_:pytest.fail('BFF attempted a filesystem authority fallback'))
    bff=object.__new__(CoreProductBFFR1)
    bff.api=SimpleNamespace(root=tmp_path,candidate=dict(candidate,accepted_trade_date=day),cache={},context_digest='api-context')

    actual_manifest,projection=bff.focus_projection(day)

    assert actual_manifest==manifest
    assert projection=={'events':[],'episodes':[]}
    assert reads==[(projection_binding,{'t0':day,'head_token':head_token})]


def test_pg_product_catalog_upgrades_legacy_focus_projection_into_owner_fact(tmp_path,monkeypatch):
    from workbench_db import v4_operational_owner_pg_closeout as closeout
    from workbench_db import v4_focus_projection_pg_closeout as focus_pg

    day='2026-10-17'
    source_path=tmp_path/'focus-source.json.gz';source_path.write_bytes(b'projection-source')
    source=ref(tmp_path,source_path)
    scope=dict(T0=day,accepted=True)
    scope_path=tmp_path/'focus-scope.json';scope_path.write_bytes(canonical(scope))
    scope_binding=ref(tmp_path,scope_path)
    manifest=dict(T0=day,contract_id='CORE_PRODUCT_FOCUS_READ_MANIFEST_R2',
        head=scope_binding,projection=source,source_bindings={},implementation=ref(tmp_path,scope_path))
    manifest['fact_token']=scope_binding['sha256']
    manifest['history_index']=dict(T0=day,head_token=scope_binding['sha256'])
    manifest_path=tmp_path/'focus-manifest.json';manifest_path.write_bytes(canonical(manifest))
    owners={day:{'focus':source}}
    authority=dict(contract_id=catalog.CONTRACT,dates={day:ref(tmp_path,manifest_path)},
        source_owners=owners,owner_source_digest=digest(canonical(owners)),PIT_ELIGIBLE=False,
        AS_RECORDED=False,historical_PIT_permission=False)
    source_authority_path=tmp_path/'source-authority.json';source_authority_path.write_bytes(b'{}')
    candidate=dict(accepted_trade_date=day,published_sessions=[day],owners=owners,
        native_product_read_authority=ref(tmp_path,source_authority_path))
    stored={}

    def append(root_arg,fact_token,t0,domain,binding,rows):
        stored[(domain,fact_token)]=rows
        return dict(path=f'{domain}/{fact_token}.pg.json',fact_key=fact_token)
    monkeypatch.setattr(closeout,'prepare',append)
    monkeypatch.setattr(closeout,'read',lambda root_arg,descriptor,fact_token,t0,domain,binding,**kwargs:
        stored[(domain,fact_token)])
    projection_fact=dict(contract_id=focus_pg.CONTRACT,T0=day,head_token=scope_binding['sha256'],
        source_binding=source,fact_token='d'*64,projection_sha256='e'*64,
        path='focus_projection/fact.pg.json',sha256='f'*64,bytes=50,
        pg_descriptor={'engine':'postgresql','kind':'focus_projection'})
    monkeypatch.setattr(focus_pg,'build',lambda *args,**kwargs:(projection_fact,
        dict(whole_payload_difference=0,storage_engine='postgresql')))
    receipt=catalog.prepare_pg(tmp_path,candidate,authority)
    assert receipt['dates']==1
    loaded=catalog.load(tmp_path,candidate)
    migrated=loaded['dates'][day]
    assert migrated['contract_id']=='CORE_PRODUCT_FOCUS_READ_MANIFEST_R3_NATIVE_PG'
    assert migrated['projection']==projection_fact
    assert migrated['projection_source']==source
    assert migrated['projection_pg_receipt']['whole_payload_difference']==0
