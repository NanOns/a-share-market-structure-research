import pytest

from workbench_db.v4_operational_owner_pg_closeout import read_schema


def test_head_bound_inline_descriptor_is_workspace_independent(tmp_path):
    descriptor=dict(contract_id='V4_PG_OPERATIONAL_OWNER_FACTS_R1',
        engine='postgresql',schema='v4_forward_0123456789abcdef',kind='core')
    binding=dict(path='data/v4/operational_owner_pg_closeout_r1/core/fact.pg.json',
        sha256='a'*64,bytes=100,pg_descriptor=descriptor)
    assert read_schema(tmp_path,binding,descriptor)==descriptor['schema']
    assert read_schema(tmp_path/'relocated',binding,descriptor)==descriptor['schema']


def test_schema_must_be_safe_and_descriptor_must_be_head_bound(tmp_path):
    descriptor=dict(contract_id='V4_PG_OPERATIONAL_OWNER_FACTS_R1',
        engine='postgresql',schema='v4_forward_0123456789abcdef',kind='core')
    binding=dict(path='data/v4/operational_owner_pg_closeout_r1/core/fact.pg.json',
        sha256='a'*64,bytes=100,pg_descriptor=descriptor)
    with pytest.raises(ValueError,match='INLINE_DESCRIPTOR_REQUIRED'):
        read_schema(tmp_path,dict(binding,pg_descriptor=None),descriptor)
    unsafe=dict(descriptor,schema='public; DROP SCHEMA public')
    with pytest.raises(ValueError,match='INVALID_V4_PG_SCHEMA'):
        read_schema(tmp_path,dict(binding,pg_descriptor=unsafe),unsafe)
