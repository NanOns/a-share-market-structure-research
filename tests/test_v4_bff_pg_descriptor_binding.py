from pathlib import Path

from workbench_service.core_product_server_r1 import _collect_local_binding_paths


def test_inline_pg_descriptor_is_not_collected_as_a_local_file():
    root=Path('G:/codex_tmp/v4_inline_descriptor_fixture')
    paths=set()
    binding={
        'path':'data/v4/operational_owner_pg_closeout_r1/raw/fact.pg.json',
        'sha256':'a'*64,
        'bytes':123,
        'pg_descriptor':{
            'contract_id':'V4_OPERATIONAL_OWNER_NATIVE_PG_CLOSEOUT_R1',
            'engine':'postgresql','schema':'v4_forward_test','kind':'raw',
            'fact_key':'fact','payload_sha256':'b'*64,
        },
    }

    _collect_local_binding_paths(root,{'owner':binding},paths)

    assert not paths


def test_file_binding_remains_a_local_input():
    root=Path('G:/codex_tmp/v4_file_binding_fixture')
    paths=set()
    _collect_local_binding_paths(root,{'path':'config/contract.json','sha256':'c'*64},paths)

    assert paths=={root/'config/contract.json'}
