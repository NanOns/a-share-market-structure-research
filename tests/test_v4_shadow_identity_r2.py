"""Pure R3 Shadow identity and fixed-schema locator checks."""
from copy import deepcopy

import pytest

from workbench_db import v4_shadow_pg_r3 as r3
from workbench_service.shadow_context import ShadowContextReader, canonical, context_token
from workbench_service.research_context import ResearchContextError


def descriptor():
    value = dict(contract_id=r3.CONTRACT, engine='postgresql', schema='v4',
                 content_digest='a' * 64,
                 database_identity=dict(system_identifier='1', database='market_research', database_oid='646711'))
    value['logical_digest'] = r3.digest(value)
    return value


def test_shadow_descriptor_rejects_per_export_schema_before_connection(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError('legacy physical Schema must be rejected before connecting')
    monkeypatch.setattr(r3, 'connection', forbidden)
    value = descriptor()
    value['schema'] = 'v4_shadow_r2_0123456789abcdef'
    value['logical_digest'] = r3.digest({k: v for k, v in value.items() if k != 'logical_digest'})
    with pytest.raises(ValueError, match='PG_SHADOW_R3_FIXED_V4_BINDING_REQUIRED'):
        with r3.read(value):
            pytest.fail('noncanonical schema must never yield a reader')


def test_shadow_fact_payload_must_bind_exact_origin():
    payload = dict(namespace='SHADOW_V4', execution_mode='SHADOW',
                   evidence_origin='PIT_OBSERVED', value='x')
    assert r3._records([dict(kind='vector', id='one', payload=payload)], 'PIT_OBSERVED')
    payload['evidence_origin'] = 'ACTIVATION_SIMULATION'
    with pytest.raises(ValueError, match='SHADOW_FACT_IDENTITY_MISMATCH'):
        r3._records([dict(kind='vector', id='one', payload=payload)], 'PIT_OBSERVED')


def test_shadow_export_rejects_duplicate_and_wrong_origin():
    payload = dict(namespace='SHADOW_V4', execution_mode='SHADOW',
                   evidence_origin='PIT_OBSERVED')
    with pytest.raises(ValueError, match='SHADOW_DUPLICATE_FACT'):
        r3._records([dict(kind='vector', id='one', payload=payload)] * 2, 'PIT_OBSERVED')
    with pytest.raises(ValueError, match='SHADOW_FACT_IDENTITY_MISMATCH'):
        r3._records([dict(kind='vector', id='one', payload=payload)], 'ACTIVATION_SIMULATION')


def test_shadow_descriptor_rejects_wrong_database_identity():
    class Cursor:
        def fetchone(self):
            return ('1', 'market_research', '646711')
    class FakePG:
        def execute(self, *_args, **_kwargs):
            return Cursor()
    value = deepcopy(descriptor())
    value['database_identity']['system_identifier'] = '0'
    value['logical_digest'] = r3.digest({k: v for k, v in value.items() if k != 'logical_digest'})
    with pytest.raises(ValueError, match='SHADOW_DATABASE_IDENTITY_MISMATCH'):
        r3.verify(FakePG(), value)


def test_shadow_ui_rejects_legacy_physical_schema_descriptor_before_pg(tmp_path):
    root = tmp_path / 'shadow'; (root / 'config').mkdir(parents=True)
    context = dict(namespace='SHADOW_V4', trade_date='2026-09-30', publication_id='pub',
                   publication_revision=1, model_contract_id='model', parameter_set_id='params',
                   state_lineage_id='lineage', daily_input_digest='a' * 64,
                   source_manifest_digest='b' * 64, evidence_origin='PIT_OBSERVED')
    def save(name, value):
        raw = canonical(value); path = root / name; path.write_bytes(raw)
        import hashlib
        return dict(path=name, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
    descriptor = dict(contract_id='V4_PG_SHADOW_READBACK_R2', engine='postgresql',
                      schema='v4_shadow_r2_0123456789abcdef')
    database_binding = save('shadow.pg.json', descriptor)
    manifest = dict(context=context, database_path='shadow.pg.json',
                    database_binding=database_binding, facts={},
                    components={}, source_quality='UNKNOWN')
    readback = save('manifest.json', manifest)
    context_binding = context_token(dict(context, readback_manifest_digest=readback['sha256']))
    receipt = save('receipt.json', dict(decision='PASS_REAL_SHADOW_UI_READBACK',
         readback_sha256=readback['sha256'], context_token=context_binding))
    config = dict(contract_id='V4_17_EXACT_READBACK_SOURCE_V1', accepted_readback=readback,
                  external_acceptance=receipt)
    save('config/v4_17_shadow_ui_source_v1.json', config)
    reader = ShadowContextReader(root)
    with pytest.raises(ResearchContextError, match='PG_SHADOW_R3_FIXED_V4_BINDING_REQUIRED'):
        reader._real()
