import json
import pytest
from workbench_analysis.r43_owner_replay import ref
from workbench_db.v4_native import workspace_schema
from workbench_db.v4_operational_owner_pg_closeout import read_schema,FOLDER


def fixture(tmp_path):
    source=tmp_path.parent/'accepted-source'
    binding=dict(path='old.pg.json',sha256='a'*64,bytes=1)
    authority=tmp_path/'authority.json'
    owners={'2026-10-13':{'core':{'path':'core.gz','sha256':'b'*64}}}
    authority.write_text(json.dumps(dict(contract_id='V4_HEAD_EMBEDDED_NATIVE_PG_OWNER_AUTHORITY_V2',source_owners=owners,
        owners={'2026-10-13':{'core':dict(descriptor=binding,fact_token='c'*64)}})))
    head=tmp_path/'head.json'
    head.write_text(json.dumps(dict(contract_id='V4_OPERATIONAL_INCREMENTAL_SUCCESSOR_V1',owners=owners,native_pg_owner_authority=ref(tmp_path,authority))))
    config=tmp_path/'config/r8_owner_read_origin_r1.json';config.parent.mkdir()
    origin=dict(contract_id='R8_ISOLATED_OWNER_READ_ORIGIN_R1',scope='READ_ONLY_ACCEPTED_PREDECESSOR',
        candidate_root=str(tmp_path),source_workspace_root=str(source),source_head=ref(tmp_path,head))
    config.write_text(json.dumps(origin))
    return binding,dict(schema=workspace_schema(source/FOLDER,'forward')),config,origin,head


def test_only_hash_bound_accepted_predecessor_descriptor_can_use_source_schema(tmp_path):
    binding,descriptor,*_=fixture(tmp_path)
    assert read_schema(tmp_path,binding,descriptor)==descriptor['schema']
    own=dict(schema=workspace_schema(tmp_path/FOLDER,'forward'))
    assert read_schema(tmp_path,{},own)==own['schema']


@pytest.mark.parametrize('kind',['descriptor','schema','root','head'])
def test_unbound_descriptor_or_changed_origin_fails_closed(tmp_path,kind):
    binding,descriptor,config,origin,head=fixture(tmp_path)
    if kind=='descriptor':binding=dict(binding,sha256='d'*64)
    elif kind=='schema':descriptor=dict(schema='v4_forward_unrelated')
    elif kind=='root':origin['candidate_root']=str(tmp_path/'another');config.write_text(json.dumps(origin))
    else:head.write_text('{}')
    with pytest.raises(ValueError):read_schema(tmp_path,binding,descriptor)
