"""Synthetic engineering admission fixtures; no real historical PIT claim."""
import hashlib
import json
import pytest
from tests.test_cohort_admission_r4 import setup
from workbench_db.v4_cohort_pg_r1 import prepare_owner, load_owner
from workbench_analysis.validation_cohort_read_contract_r3 import read_authorized_statistics

def write(root,name,value):
    p=root/name;p.write_text(json.dumps(value),encoding='utf8')
    return dict(path=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest())

def authorize_descriptor(root,args,descriptor):
    head=json.loads((root/args['accepted_head']['path']).read_bytes())
    grant=json.loads((root/head['cohort_read_grants'][args['trade_date']]['path']).read_bytes())
    grant['owner']=descriptor
    head['cohort_read_grants'][args['trade_date']]=write(root,'pg_grant_fixture.json',grant)
    head['owners'][args['trade_date']]['validation_cohort']=descriptor
    return dict(args,accepted_head=write(root,'pg_head_fixture.json',head),owner_binding=descriptor)

def test_pg_exact_owner_read_requires_same_accepted_grant(tmp_path):
    args=setup(tmp_path)
    before=(tmp_path/'head.json').read_bytes()
    descriptor=prepare_owner(**args)
    assert (tmp_path/'head.json').read_bytes()==before
    assert load_owner(tmp_path,descriptor)==json.loads((tmp_path/'owner.json').read_bytes())
    with pytest.raises(ValueError,match='ACCEPTED_OWNER_BINDING'):
        read_authorized_statistics(**dict(args,owner_binding=descriptor))
    result=read_authorized_statistics(**authorize_descriptor(tmp_path,args,descriptor))
    assert result['observed_count']==1 and result['matured_count'] is None

def test_pg_descriptor_corruption_and_missing_dsn_fail_closed(tmp_path,monkeypatch):
    args=setup(tmp_path);descriptor=prepare_owner(**args)
    monkeypatch.delenv('V4_NATIVE_PG_DSN')
    with pytest.raises(RuntimeError,match='NO_FALLBACK'):
        load_owner(tmp_path,descriptor)
    monkeypatch.setenv('V4_NATIVE_PG_DSN','host=127.0.0.1 port=55791 user=r4_isolated_admin dbname=postgres')
    path=tmp_path/descriptor['path'];path.write_bytes(b'{}')
    with pytest.raises(ValueError,match='DIGEST_MISMATCH'):
        load_owner(tmp_path,descriptor)

def test_reconstructed_or_late_source_never_materializes_cohort(tmp_path):
    args=setup(tmp_path,{'membership_basis':'TDX_LATEST_MEMBER_RETRO_V1'})
    with pytest.raises(ValueError,match='MEMBER_ASOF'):
        prepare_owner(**args)
    assert not (tmp_path/'data/v4/cohort_pg').exists()

def test_missing_real_owner_route_preserves_unknown_counts():
    from workbench_analysis.operational_successor_v1 import accepted_api
    from workbench_service.operational_successor_bff_v1 import OperationalSuccessorBFFV1
    api=accepted_api('G:/codex_tmp/r4_r3_pg_publication_v2')
    code,response=OperationalSuccessorBFFV1(api,None).get('/api/v4/forward/statistics',{'context_token':api.token})
    assert code==200 and response['engineering_route_implemented']
    assert response['reason']=='NO_AUTHORIZED_COHORT_OWNER'
    assert response['data']['enrollment_denominator'] is None
    assert response['focus_is_validation_cohort'] is False
